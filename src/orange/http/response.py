import os,json
from .error import get_error_response
from .import get_expires_gmt_time


expires = 60*60*24
max_age = f'max-age={expires}'
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


def build_header(header_dict):
  h = 'HTTP/1.1 200 OK\r\n'
  for k, v in header_dict.items():
    h += f'{k}: {v}\r\n'
  header =  h.encode('utf-8') + b'\r\n'
  return header

def json_resp(py_obj):
  body = json.dumps(py_obj, ensure_ascii=False)  # indent=2 缩进
  body = body.encode('utf-8')
  header_dict = {
    'Content-Type': "application/json",
    'Content-Length': len(body)
  }

  response = build_header(header_dict) + body
  return response

def send_file(file_path):
  # 检查文件是否存在
  if os.path.exists(file_path):
    # 获取扩展名
    suffix = file_path.split('.', 1)[1]
    # 二进制方式读取
    with open(file_path, 'rb') as f:
      body = f.read()
      header_dict = {
        'Content-Type': mime_type.get(suffix, 'application/octet-stream'),
        'Content-Length': len(body),
        'Cache-Control': max_age,
        # 'Expires':get_expires_gmt_time(expires)
      }
      header = build_header(header_dict)
      return header + body


http_status = {
  101: "Switching Protocols",
  200: "OK",
  400: "Bad Request",
  401: "Unauthorized",
  404: "Not Found",
  405: "Method Not Allowed",
  500: "Internal Server Error",
}

class Response:
  def __init__(self):
    self.status_code = 200
    self.headers = None

  def build(self):
    resp = f'HTTP/1.1 {self.status_code} {http_status.get(self.status_code)}\r\n'
    if self.headers is not None:
      for k, v in self.headers:
        resp += f'{k}: {v}\r\n'
    return resp.encode('utf-8') + b'\r\n'
