import asyncio
import os

from orange_kit.json import json_dumps
from email.utils import formatdate



def json_resp(data):
  body = json_dumps(data)  # indent=2 缩进
  body = body.encode('utf-8')
  headers = [
    ('Content-Type',"application/json"),
  ]
  return Response(body,headers)

def get_gmt_time():
  formatdate(None, usegmt=True)

# timeout 单位是秒
def get_expires_gmt_time(timeout):
  formatdate(None, usegmt=True)

def get_max_age(expires:int):
  # expires 单位秒
  return f'max-age={expires}'

mime_type = {
  'html': 'text/html; charset=UTF-8',
  'css': 'text/css',
  'js': 'application/javascript',
  # 'ttf': 'application/octet-stream',
  'ico': 'image/x-icon',
  'icon': 'image/x-icon',
  'gif': 'image/gif',
  'jpg': 'image/jpg',
  'png': 'image/png',
}

http_status = {
  101: "Switching Protocols",
  200: "OK",
  400: "Bad Request",
  401: "Unauthorized",
  413: "Request Entity Too Large",
  404: "Not Found",
  405: "Method Not Allowed",
  500: "Internal Server Error",
}

class Response:
  def __init__(self,body: bytes, headers=None, status_code = 200):
    if headers is None: headers = []
    self.status_code = status_code
    self.headers = headers
    self.body = body

  def build(self):
    resp = f'HTTP/1.1 {self.status_code} {http_status.get(self.status_code)}\r\n'
    if self.body is not None:
      self.headers.append(('Content-Length',len(self.body)))
    for k, v in self.headers:
      resp += f'{k}: {v}\r\n'
    resp = resp.encode('utf-8') + b'\r\n'
    if self.body is not None:
       resp = resp + self.body
    return resp

def get_error_response(code):
  status_str = http_status.get(code)
  if status_str is None:
    status_str = f"http status code {code} not support"
    code = 500
  return Response(status_str.encode('utf-8'),None,code)

def get_file_resp(file_path,max_age):
  # 检查文件是否存在
  if os.path.exists(file_path):
    # 获取扩展名
    suffix = file_path.split('.', 1)[1]
    # 二进制方式读取
    with open(file_path, 'rb') as f:
      body = f.read()
      headers = [
        ('Content-Type', mime_type.get(suffix, 'application/octet-stream')),
        # 'Expires':get_expires_gmt_time(expires)
      ]
      if max_age is None:
        headers.append(('Cache-Control', 'no-cache'))
      else:
        headers.append(('Cache-Control', get_max_age(max_age)))
      return Response(body,headers)
  else:
    return get_error_response(404)

def get_file_resp_async(file_path,max_age):
  loop = asyncio.get_running_loop()
  return loop.run_in_executor(None,get_file_resp,file_path,max_age)


