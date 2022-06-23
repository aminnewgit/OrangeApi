from typing import Callable



from .base_endpoint import Endpoint
from .base_router import Router


class ApiEndpoint(Endpoint):
  def __init__(self, path, method, function, is_root_path:bool, is_async:bool):
    super().__init__(function,is_async)
    self.path = path
    self.method = method
    self.is_root_path = is_root_path


# 根路径模块 path是'' 如果由前缀 就是 '/prefix'
# 正常 path 前后不加 '/'
class ApiModule(object):
  def __init__(self,name,base_path=""):
    self.base_path = base_path
    self.api_dict = {}
    self.name = name

  def add(self,method:str,path:str,function:Callable ,is_root_path:bool=False,is_async:bool=True):
    # 路由重复检测
    method = method.upper()
    if is_root_path is False:
      path = f'{self.base_path}{path}'

    method_dict = self.api_dict.get(method)
    if method_dict is None:
      method_dict = {}
      self.api_dict[method] = method_dict
    else:
      exist_api = method_dict.get(path)
      if exist_api is not None:
        raise KeyError(f'{self.name} add api repeat {path}')
    method_dict[path] = ApiEndpoint(path,method,function,is_root_path,is_async)

  # 注册路由装饰器
  def get(self, path:str, is_root_path:bool=False, is_async:bool=True):
    def decorator(f):
      self.add('GET',path,f,is_root_path,is_async)
      return f
    return decorator

  def post(self, path:str, is_root_path:bool=False, is_async:bool=True):
    def decorator(f):
      self.add("POST",path, f, is_root_path, is_async)
      return f

    return decorator

  def api(self, method:str, path:str, is_root_path:bool=False, is_async:bool=True):
    def decorator(f):
      self.add(method, path, f, is_root_path, is_async)
      return f

    return decorator

class ApiRouter(Router):
  def __init__(self,base_path:str=None):
    self.routes = {}
    self.base_path = base_path

  # 追加子模块
  def add(self, module: ApiModule):
    for method, method_api_dict in module.api_dict.items():
      method_routes = self.routes.get(method)
      if method_routes is None:
        method_routes = {}
        self.routes[method] = method_routes

      for api_path,api in method_api_dict.items():
        if self.base_path is not None and api.is_root_path is False:
            api_path = self.base_path + api_path
        exist_api = method_routes.get(api_path)
        if exist_api is not None:
          raise KeyError(f'{module.name} add api repeat {api_path}')
        method_routes[api_path] = api

  # 匹配路由
  def match_path(self,req) -> Endpoint :
    method_dict = self.routes.get(req.method)
    if method_dict is None: return None
    endpoint = method_dict.get(req.path)
    return endpoint

  def print_routes(self):
    for method,routes in self.routes.items():
      for path in routes.keys():
        print(method,path)

