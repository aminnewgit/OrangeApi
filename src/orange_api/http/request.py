from urllib import parse
import asyncio
import json

from .response import Response
from ..log import log_error
from ..utils.file import async_write_once,\
  async_open_write_not_close,async_write,async_close
from ..websocket import WebSocketClient


class Request(object):
  def __init__(self,method,path,query_str,url,
               headers,body_length,body,loop):
    self.method = method
    self.path = path
    self.query_str = query_str
    self.headers:dict = headers
    self.url = url
    self.query = None
    self.cookie = None

    # 传输
    self.transport:[asyncio.transports.Transport,None] = None
    self.loop = loop
    self.protocol = None

    # body 有关
    self.body = body
    self.body_length = body_length
    self.body_over_event:[asyncio.Event,None] = None
    self.body_lock:[asyncio.Lock,None] = None
    self.body_read_event:[asyncio.Event,None] = None
    self.body_over = True
    # json
    self.json = None
    # formData

    # response 发送标志及回调函数
    self.response_over = False
    self.on_response_over = False

  def send(self,data):
    self.transport.write(data)

  def parse_cookie(self):
    ck = self.headers.get('Cookie')
    cookie = {}
    if ck is not None:
      ck = ck.split('; ')
      for i in ck:
        c = i.split('=')
        cookie[c[0]] = c[1]
    self.cookie = cookie
    return cookie

  def parse_query(self):
    query = {}
    if self.query_str is None: return query
    args = self.query_str.split('&')
    for m in args:
      arg = m.split('=')
      if(len(arg)) != 2: return {}
      query[arg[0]] = arg[1]
    self.query = query
    return query

  def upgrade_websocket(self) -> (Response,WebSocketClient):
     ws_client = WebSocketClient()
     resp: Response = ws_client.can_upgrade(self)
     if resp.status_code == 101:
       ws_client.id = id(self.transport)
       # todo transport.set_protocol()
       self.protocol.web_socket_client = ws_client
       return resp,ws_client
     else:
       return resp,None,

  async def get_json(self):
    if self.json is None:
      try:
        if self.body_lock is False:
          await self.body_over_event.wait()
        j = json.loads(self.body.decode("utf-8"))
        self.json = j
        return j
      except Exception as e:

        log_error('json dumps error',self,e)
        return None
    else:
      return self.json

  async def _get_body_chunk(self):
    await self.body_read_event.wait()
    self.transport.pause_reading()
    chunk = self.body
    self.body = b''
    over = self.body_over_event.is_set()
    self.body_read_event.clear()
    self.transport.resume_reading()
    return chunk,over

  async def save_body(self,path,mode='wb'):
    if self.body_over is True:
      print('一次性写入文件')
      async_write_once(self.loop,path,self.body,mode)
    else:
      chunk,over = await self._get_body_chunk()
      print('写入:',len(chunk))
      f = await async_open_write_not_close(self.loop,path,chunk,mode)
      while over is False:
        chunk, over = await self._get_body_chunk()
        print('写入:', len(chunk))
        await async_write(self.loop,f,chunk)
      await async_close(self.loop,f)
      print('写入完成')


class RequestParser:
  def __init__(self,protocol):
    self.protocol = protocol

    self.is_new_request = True
    self.body_expect_length = 0
    self.body_recv_length = 0

  def _parse(self,d):
    # 分离头部和body
    r = d.split(b'\r\n\r\n', 1)
    assert len(r) == 2 ,'no body'
    body = r[1]
    # print(len(body))
    self.body_recv_length = len(body)
    # 解析请求行
    # http请求头格式
    # 请求方法 空格 url 空格 协议版本 \r\n  请求行
    # get /abc/abc HTTP/1.1\r\n
    # 头部 key:value/r/n
    # /r/n body
    r = r[0].decode('utf-8').split('\r\n', 1)
    rl = r[0].split()  # request line
    if len(rl) != 3: raise AssertionError('bad request line')
    elif rl[2] != 'HTTP/1.1': raise AssertionError('not http 1.1')
    method = rl[0].upper()
    url = rl[1]
    if "%" in url:
      url = parse.unquote(url)
    url_s = url.split('?')

    # 解析url
    path = url_s[0]
    ul = len(url_s)
    query_str = None
    if ul > 2:
      raise AssertionError('query str too much ?')
    elif ul == 2:
      query_str = url_s[1]

    #解析 header
    headers = {}
    lines = r[1].split('\r\n')
    for i in lines:
      hd = i.split(': ')
      assert len(hd) == 2, 'header format err'
      headers[hd[0].lower()] = hd[1]

    body_length = int(headers.get('content-length',0))
    req = Request(method,path,query_str,
                  url,headers,body_length,body,
                  self.protocol.loop)
    self.body_expect_length = body_length
    return req

  # 如果 parse 抛出 AssertionError 说明是一个坏的request
  # feed 喂食
  def feed_data(self, r: bytes):
    if self.is_new_request:
      req = self._parse(r)
      # 65535 是64k
      # print('body的长度是:', self.body_expect_length)
      # print('第一次接收到body长度是:', self.body_recv_length)
      if self.body_recv_length == self.body_expect_length:
        # 一次性接收完成整个请求
        self.protocol.on_request(req)
      elif self.body_recv_length < self.body_expect_length:
        # 请求没有一次接收完成,下次接收body
        self.is_new_request = False
        req.body_over = False
        self.protocol.on_request(req)
      else:
        raise AssertionError('body','body len > content len')
    else:
      # 接收body
      nrl = len(r) # new recv length
      # print('收到长度:',nrl)
      nl = self.body_recv_length + nrl
      bel = self.body_expect_length
      # print('接收body chunk,完成长度:', nl)
      if nl == bel:
        # 接收长度等于 content-length
        # 接收完成
        self.protocol.on_body_over(r)
        self.is_new_request = True
      elif nl < bel:
        # 未完成接收
        self.protocol.on_body(r)
        self.body_recv_length = nl
      else:
        raise AssertionError('body len > content len')


# todo 做一个formData的解析类
#
# class FormData:
#   def __init__(self,req:Request):
#     self.req = req
#     self.boundary = None
#
#   def read_line(self):
#     bl = self.req.body.split(b'\r\n',1)
#     self.req.body = bl[1]
#     return bl[0]
