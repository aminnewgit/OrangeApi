from typing import Callable
from ..http.request import Request
from ..http.url import formate_url_path

# todo 标注函数说明 两种方式都留下,一种在get中desc, 后期添加不传path, 就是desc, 直接使用函数名做路径,
# 使用函数名做路径有两种 方式 一种是下滑线变斜杠 一种下划线驼峰


# auth_filter 鉴权过滤器 用于登陆和权限验证, 并想req 对象中加载session 数据
# 优先级顺序(从高到低): 单体api过滤器->api模块过滤器->路由过滤器
# 定义了优先级高的过滤器会覆盖优先级低的过滤器
#

class ApiEndpoint:
  __slots__ = (
    "method",
    "path",
    "path_list",
    "api_func",

    "doc",
    "name",

    "auth_filter",
    "auth_ignore",
    "permission",

    "api_module",
    "api_router",
    "filter_list"
  )

  def __init__(self,method,path,api_func,api_module):

    self.path = path
    self.path_list = [path]

    self.method:str = method
    self.api_func: Callable = api_func  # 执行函数

    self.name = api_func.__name__
    self.doc = None

    self.auth_filter = None
    self.auth_ignore = None
    self.permission = None

    self.api_module: ApiModule = api_module
    self.api_router: ApiRouter | None = None

    self.filter_list = []

  async def execute_func (self, req: Request):
    for filter_func in self.filter_list:
      await filter_func(req,self)
    return await self.api_func()

  def add_path_prefix(self,path_prefix):
    if path_prefix is None: return self.path
    self.path_list.insert(0,path_prefix)
    self.path = "".join(self.path_list)
    return self.path

  def init(self):
    annotation_dict = self.api_func.__dict__.get("__annotation_dict__",{})

    self.doc = annotation_dict.get('doc')
    self.permission = annotation_dict.get('permission')
    self.auth_ignore = annotation_dict.get("auth_ignore")

    # 获取健全过滤器
    if self.auth_ignore is True: return
    auth_filter = annotation_dict.get('auth_filter')
    if auth_filter is None:
      auth_filter = self.api_module.__auth_filter__
    if auth_filter is None:
      auth_filter = self.api_router.__auth_filter__
    if auth_filter is not None:
      self.auth_filter = auth_filter
      self.filter_list.append(auth_filter)
    # 给filter增加描述, 文档生成filter路径

  def get_doc_dict(self):
    return {
      "title":self.doc[0],
      "desc": self.doc[1],
      "name": self.name,
      "method": self.method,
      'path': self.path,
      'need_login': self.auth_filter is not None,
      'permission': self.permission
    }


# 根路径模块 path是'' 如果由前缀 就是 '/prefix'
# 正常 path 前后不加 '/'
class ApiModule(object):

  __slots__ = ("__url_prefix__", "__endpoint_list__","__auth_filter__",
               "__module_name__", "__doc_title__","__doc_desc__")

  def __init__(self,name,url_prefix="",desc="",title=""):
    self.__url_prefix__ = formate_url_path(url_prefix)
    self.__module_name__ = name
    self.__doc_title__ = title
    self.__doc_desc__ = desc
    self.__auth_filter__ = None
    self.__endpoint_list__: list[ApiEndpoint] = []

  # ===== 添加路由函数 =====
  def _add(self, method:str, path:str, func):
    endpoint = ApiEndpoint(method,path,func, self)
    endpoint.add_path_prefix(self.__url_prefix__)
    self.__endpoint_list__.append(endpoint)

  # 注册路由装饰器
  def get(self, path:str):
    def decorator(f):
      self._add('GET', path, f)
      return f
    return decorator

  def post(self, path:str):
    def decorator(f):
      self._add("POST", path, f)
      return f
    return decorator

  # ===== 注解保存 =====
  @staticmethod
  def _set_annotation(f,key,value):
    a_dict = f.__dict__.get('__annotation_dict__')
    if a_dict is None:
      a_dict = {}
      f.__annotation_dict__ = a_dict
    a_dict[key] = value

  # ===== 设置文档信息 =====
  def doc(self,name,desc=''):
    """文档描述"""
    def decorator(f):
      self._set_annotation(f,'doc',(name,desc))
      return f
    return decorator

  # ===== 鉴权过滤器注册 =====
  def reg_module_auth_filter(self,f):
    """注册api模块鉴权过滤器"""
    self.__auth_filter__ = f
    return f

  def reg_api_auth_filter(self,f):
    """注册单个api鉴权过滤器"""
    self._set_annotation(f, 'auth_filter', f)
    return f

  # =====鉴权配置 =====
  def permission(self,permission):
    """注册权限"""
    def decorator(f):
      self._set_annotation(f, 'permission', permission)
      return f
    return decorator

  def ignore_auth(self, f):
    """忽略鉴权"""
    self._set_annotation(f, 'auth_ignore', True)
    return f

  # ===== 文档生成 =====
  def __get_api_doc_list__(self):
    return {
      "moduleName": self.__module_name__,
      "title": self.__doc_title__,
      'desc': self.__doc_desc__,
      'apiList': [api.get_doc_dict() for api in self.__endpoint_list__]
    }


class ApiRouter:

  __slots__ = ("__api_dict__","__url_prefix__",
               "__module_list__","__auth_filter__")

  def __init__(self,url_prefix:str=None):
    self.__api_dict__ = {"GET":{},"POST":{}}
    self.__url_prefix__ = formate_url_path(url_prefix)
    self.__module_list__:list[ApiModule] = []
    self.__auth_filter__ = None


  # 追加子模块
  def add(self, module: ApiModule):
    self.__module_list__.append(module)
    for api_endpoint in module.__endpoint_list__:
      # 处理 method
      method_dict = self.__api_dict__.get(api_endpoint.method)
      if method_dict is None:
        raise ValueError(f'{module.__module_name__}-{api_endpoint.name} method not allowed')

      # 处理path
      path = api_endpoint.add_path_prefix(self.__url_prefix__)
      exist_api = method_dict.get(path)
      if exist_api is not None:
        raise KeyError(f'{module.__module_name__}-{api_endpoint.name} path repeat')

      # 保存endpoint
      api_endpoint.api_router = self
      method_dict[path] = api_endpoint

      # 初始化endpoint
      api_endpoint.init()

  # 匹配路由
  def match_path(self,req) -> ApiEndpoint | None :
    method_dict = self.__api_dict__.get(req.method)
    if method_dict is None: return
    endpoint = method_dict.get(req.path)
    return endpoint

  def reg_auth_filter(self, f):
    """注册router鉴权过滤器"""
    self.__auth_filter__ = f
    return f

  # 创建文档api
  def get_doc_data(self):
   return {
     "urlPrefix": self.__url_prefix__,
     "moduleList":[module.__get_api_doc_list__() for module in self.__module_list__]
   }

