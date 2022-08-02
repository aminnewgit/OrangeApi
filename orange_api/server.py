import asyncio
# import traceback
# import uvloop

from .http.request import RequestParser,Request
from .websocket import WebSocketClient


class ServerState:
  def __init__(self):
    self.task_set=set()
    self.task_num = 0
    self.conn_set=set()
    self.conn_num = 0
    self.ws_set=set()
    self.ws_num=0

server_state = ServerState()
req_dict = {}

class HttpProtocol(asyncio.Protocol):
  def __init__(self,app):
    self.app = app

    # 每一连接的信息
    self.transport = None
    self.loop = asyncio.get_running_loop()
    self.parser = RequestParser(self)

    # 每一次request
    self.current_req = None
    self.current_task = None

    # 如果不是一次完成body接收 初始化这些事件和锁
    self.body_read_event:asyncio.Event = None
    self.body_over_event:asyncio.Event = None

    self.web_socket_client: WebSocketClient = None

  # transport 连接的生命周期
  def connection_made(self, transport):
    self.transport = transport
    # peername = transport.get_extra_info('peername')
    # print(f'{id(transport)} new conn ip: {peername}')

  def data_received(self,data):
    if self.web_socket_client is None:
      self.http_received(data)
    else:
      self.web_socket_client.feed_data(data)

  def http_received(self, data):
    # print(f'{id(self)} 接收信息',len(data))
    try :
      self.parser.feed_data(data)
    except AssertionError as e:
      print('bad request',e.args)
      if e.args[0] == 'body':
        task_id = id(self.current_task)
        del req_dict[task_id]
        if self.current_task is not None:
          self.current_task.cancel()
          self.current_task = None
        self.current_req = None
      self.transport.close()

  def eof_received(self):
    pass
    # print('eof_receive')

  def connection_lost(self,exc):
    # print(f'{id(self.transport)} lost',exc)
    if self.web_socket_client is not None:
      self.web_socket_client.clean()

  # request 接收生命周期
  def on_request(self,req:Request):
    # 在keep-alive 时 request的发送规律
    # chrome 在没有收到response之前不会发送下一个request
    # chrome 在收到response但是request没有发送完时 xhr 的状态不会从3到4 触发返回值
    #
    # 要求request头部要一次性接收完成,如果一次接收不完头部,认为是badRequest.
    # 单次request 第一次接收的data, request_parser 解析完.
    req.transport = self.transport
    req.protocol = self
    self.current_req = req
    # body没有一次完成接收完成.
    if req.body_over is False:
      if self.body_read_event is None:
        self.body_read_event = asyncio.Event() # 用于存储文件
        self.body_over_event = asyncio.Event()
      req.body_read_event = self.body_read_event
      req.body_over_event = self.body_over_event
      self.body_over_event.clear()
      self.body_read_event.clear()

    self.creat_webapp_task(req)

  def on_body(self,body_chunk):
    self.body_read_event.clear()
    self.current_req.body += body_chunk
    self.body_read_event.set()

  def on_body_over(self,body_chunk):
    self.body_read_event.clear()
    self.current_req.body += body_chunk
    self.body_read_event.set()
    self.body_over_event.set()
    # print('body 接收完成')

  # webapp task 协程生命周期
  def creat_webapp_task(self,req):
    # 启动协程任务
    task = self.loop.create_task(self.run_webapp(req))
    task.add_done_callback(self.webapp_task_over)
    server_state.task_set.add(task)

  async def run_webapp(self, req):
    # 储存req 以便req 代理调用
    task = asyncio.current_task()
    self.current_task = task
    task_id = id(task)
    req_dict[task_id] = req
    # print(id(self.transport), req.method, req.url)
    await self.app(req)

  @staticmethod
  def webapp_task_over(task):
    # print('task over',id(task))
    try:
      del req_dict[id(task)]
    except KeyError:
      pass
    server_state.task_set.discard(task)


async def run_server(app,port,host):
  loop = asyncio.get_running_loop()

  def create_protocol():
    return HttpProtocol(app)
  await loop.create_server(create_protocol,host,port)
  print(f"server start http://{host}:{port}")
  print(f"server start http://localhost:{port}")
  while True:
    await asyncio.sleep(1)



