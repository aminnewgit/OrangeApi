from typing import Callable

from .base_endpoint import Endpoint
from .base_router import Router
from ..http.response import get_file_resp_async, get_max_age


class StaticEndpoint(Endpoint):
  def __init__(self, file_path, max_age):
    async def send_file():
      return await get_file_resp_async(file_path,max_age)
    super().__init__(send_file, is_async=True)

# todo 不带/  自动去除/
class StaticRouter(Router):
  def __init__(self, file_root_path:str, uri_prefix:str, max_age:int=None, url_map:dict=None,):
    self.url_map = url_map
    self.routes = {}
    self.file_root_path = file_root_path
    self.uri_prefix = uri_prefix
    self.max_age = max_age

  # 匹配路由
  def match_path(self,req) -> Endpoint :
    uri = req.path
    if req.method != "GET": return
    elif uri.startswith(self.uri_prefix):
      path = self.file_root_path + uri.split(self.uri_prefix)[1]
      return StaticEndpoint(path,self.max_age)
    else:
      if self.url_map is not None:
        file = self.url_map.get(uri)
        max_age = self.max_age
        if type(file) is tuple:
          file,max_age = file
        if file is not None:
          return StaticEndpoint(self.file_root_path + file,max_age)

