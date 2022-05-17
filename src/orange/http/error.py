class SendError(Exception):
  def __init__(self,code:int=404):
    self.code = code

# 立刻返回响应
# 如果 close 为 True 返回响应后立刻 关闭连接
class ResponseNow(Exception):
  def __init__(self,resp:bytes):
    self.resp = resp

class CloseTransport(Exception):
  def __init__(self,msg:str):
    self.msg = msg



not_found = b'HTTP/1.1 404 NOT FOUND\r\n\r\n<h1>NOT FOUND</h1>'
e = {
  404: not_found,
  400: b'HTTP/1.1 400 Bad Request\r\n\r\n<h1>Bad Request<h1>',
  401: b'HTTP/1.1 403 Unauthorized\r\n\r\n<h1>Unauthorized<h1>',
  413: b'HTTP/1.1 413 Request Entity Too Large\r\n\r\nRequest Entity Too Large',
  500: b'HTTP/1.1 500 Internal Server Error\r\n\r\n<h1>Internal Server Error<h1>'

}

def get_error_response(code=404):
  resp = e.get(code, not_found)
  return resp