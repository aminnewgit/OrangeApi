from ..http.response import get_file_resp_async


class StaticEndpoint:
  __slots__ = ("execute_func",)

  def __init__(self, file_path, max_age):
    async def send_file(req):
      return await get_file_resp_async(file_path,max_age)
    self.execute_func = send_file


class StaticRouter:

  __slots__ = ("url_map","routes",'file_root_path','uri_prefix','max_age')

  def __init__(self, file_root_path:str, uri_prefix:str, max_age:int=None, url_map:dict=None,):
    self.url_map = url_map                # 一个 url -> file map 用于指定特殊路径对应特殊文件
    self.routes = {}

    # 文件根路径必须 / 为结尾
    if file_root_path.endswith('/') is False:
      file_root_path += '/'
    self.file_root_path = file_root_path

    # uri 前缀必须 / 为开头
    if uri_prefix.startswith('/') is False:
      raise ValueError("StaticRouter uri_prefix 必须以'/'为开头")
    self.uri_prefix = uri_prefix

    # 最大缓存时间单位s 如果值为None 表示不缓存
    self.max_age = max_age


  # 匹配路由
  def match_path(self,req) -> StaticEndpoint | None :
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

