from orange_api.router.base import BaseEndpoint
from ..http.response import get_file_resp_async


class StaticEndpoint:

  __slots__ = ("execute_func",)

  def __init__(self, file_path, max_age):
    async def send_file():
      return await get_file_resp_async(file_path,max_age)
    self.execute_func = send_file

  # todo 不带/  自动去除/
class VueRouter:
  __slots__ = (
    'vue_public_path',
    'file_root_path',    # vue文件存储的目录
    'html_endpoint',
    'file_split_path',
    "url_map",
    'max_age',
    )
  def __init__(self, file_root_path:str, vue_public_path:str, max_age:int=None, url_map:dict=None,):
    self.url_map = url_map
    self.max_age = max_age

    if file_root_path.endswith("/") is False:
      file_root_path = file_root_path + "/"
    self.file_root_path = file_root_path

    if vue_public_path.endswith("/"):
      self.file_split_path = vue_public_path
      self.vue_public_path = vue_public_path[:-1]
    else:
      self.file_split_path = vue_public_path + "/"
      self.vue_public_path = vue_public_path

    vue_html_path = file_root_path + "index.html"

    self.html_endpoint = StaticEndpoint(vue_html_path,None)

  # 匹配路由
  def match_path(self,req) -> BaseEndpoint | None :
    uri = req.path
    if req.method != "GET": return
    elif uri.startswith(self.vue_public_path):
      if len(uri.split(".")) == 1:
        return self.html_endpoint
      else:
        path = self.file_root_path + uri.split(self.file_split_path)[1]
        return StaticEndpoint(path,self.max_age)
    else:
      if self.url_map is not None:
        file = self.url_map.get(uri)
        max_age = self.max_age
        if type(file) is tuple:
          file,max_age = file
        if file is not None:
          return StaticEndpoint(self.file_root_path + file,max_age)

