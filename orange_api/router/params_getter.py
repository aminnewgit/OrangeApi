from inspect import signature

from orange_kit.model import VoBase
from orange_kit.model.exception import FieldValidationError
from orange_kit.model.field import get_type_define
from orange_kit.utils import line_to_hump
from ..http.request import Request

# todo enum 类型支持

class FromBodyJson:
  __slots__ = ("type","__name__", "body_type")
  def __init__(self):
    self.type = None
    self.__name__ = "FromBodyJson"
    self.body_type = 'json'


class FromQuery:
  __slots__ = ("require","default","desc","type","alias","__name__", "body_type")
  def __init__(self,require=False,default=None,desc='',alias=None):
    self.require = require
    self.default = default
    self.desc = desc
    self.type = None
    self.alias = alias
    self.__name__ = "FromQuery"
    self.body_type = None

class FromSession:
  __slots__ = ("type","__name__", "body_type")
  def __init__(self):
    self.type = None
    self.__name__ = "FromSession"
    self.body_type = None


# class FromHeader:
#   def __init__(self):
#     pass

def get_vo_base_field_info(k,param_type):
  return {"cate": 'VoBase', 'k': k, 'type': f"{param_type.__module__}.{param_type.__name__}",}


base_type_set = {int,float,str,bool}
# warp_type_set = {dict,list} 这个不需要, 这个就用VoBase了


async def request_context_getter(kwarg_dict:dict, param_name:str, req:Request, param_define):
  kwarg_dict[param_name] = req

async def query_base_type_getter(kwarg_dict:dict, param_name:str, req:Request, param_define: FromQuery):
    raw_query = req.parse_query()
    value = raw_query.get(param_define.alias)

    default_value = param_define.default
    require = param_define.require
    typ = param_define.type

    if value is None:
      if require is True:
        raise FieldValidationError(f'字段{param_define.alias}是必填项')
      value = default_value
    else:
      if typ is str:
        value = value.strip()
        if require is True and value == "" :
          raise FieldValidationError(f'字段{param_define.alias}是必填项')
      else:
        try:
          value = typ(value)
        except ValueError as e:
          raise FieldValidationError(f'字段{param_define.alias}的值不能转化为类型:{typ.__name__}')
    kwarg_dict[param_name] = value

async def query_vo_base_getter(kwarg_dict:dict, param_name:str, req:Request, param_define: FromQuery):
  value = req.parse_query()
  kwarg_dict[param_name] = param_define.type(value)

async def body_json_vo_base_getter(kwarg_dict:dict, param_name:str, req:Request, param_define):
  value = await req.get_json()
  kwarg_dict[param_name] = param_define.type(value)

async def session_getter(kwarg_dict:dict, param_name:str, req:Request, param_define):
  kwarg_dict[param_name] = req.session


class ParamsGetter:
  __slots__ = ("endpoint","api_func_name","api_module_name",
               "params_getter_tuple","query_params_list",
               "body_params_list","body_type","return_type","response_content_type")
  def __init__(self,endpoint):
    from .api_router import ApiEndpoint
    self.endpoint: ApiEndpoint = endpoint
    self.api_func_name = self.endpoint.api_func.__name__

    self.api_module_name = self.endpoint.api_module.__module_name__
    self.params_getter_tuple = tuple()

    self.query_params_list = []
    self.body_params_list = []
    self.body_type = None

    self.return_type = None
    self.response_content_type = "json"

  def set_body_type(self,param_type):
    if param_type is None: return
    if self.body_type is None:
      self.body_type = param_type.body_type
    else:
      if self.body_type != param_type.body_type:
        ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name} 不能定义多种body类型的参数")

  def set_return_type(self,sig):
    # todo 处理泛型
    return_type = sig.return_annotation  # 出参类型
    if return_type.__name__ == '_empty': return
    else:
      self.return_type = get_type_define(return_type)


  def init(self,api_func):
    # 虽然用字典取值更快, 但是这里是初始化的时候执行的, 所以对速度要求不高,用比较简单的写法
    sig = signature(api_func)
    self.set_return_type(sig)
    param_getter_list = []
    for k, v in sig.parameters.items():
      param_define = v.default   # 入参的定义就是 参数的默认值
      param_type = v.annotation  # 入参类型

      if param_define.__name__ == '_empty':
        param_define = None

      self.set_body_type(param_define)

      # 获取入参
      if param_define is None:
        if param_type != Request:
          raise ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name}的参数{k}定义错误")
        else:
          param_getter_list.append((k,request_context_getter,None))
      elif isinstance(param_define,FromQuery):
        param_define.type = param_type
        if param_type in base_type_set:
          if param_define.alias is None:
            param_define.alias = line_to_hump(k)
          param_getter_list.append((k, query_base_type_getter, param_define))
          self.query_params_list.append({
            "cate":'Base','k':param_define.alias,'type':param_type.__name__,'require':param_define.require,
            'desc':param_define.desc,'default':param_define.default,
          })
        elif issubclass(param_type,VoBase):
          param_getter_list.append((k, query_vo_base_getter, param_define))
          self.query_params_list.append(get_vo_base_field_info(k,param_type))
        else:
          raise ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name}的参数{k}不支持的类型定义或没有定义类型")
      elif isinstance(param_define,FromBodyJson):
        param_define.type = param_type
        if issubclass(param_type,VoBase):
          param_getter_list.append((k, body_json_vo_base_getter, param_define))
          self.body_params_list.append(get_vo_base_field_info(k,param_type))
        else:
          raise ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name}的参数{k}FromBodyJson模式只支持VoBase类型")
      elif isinstance(param_define, FromSession):
        if self.endpoint.auth_filter is None:
          raise ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name}的参数{k} api没有定义鉴权过滤器 不能获取session")
        param_getter_list.append((k, session_getter, param_define))
      else:
        raise ValueError(f"api模块:{self.api_module_name}的api函数:{self.api_func_name}的参数{k}定义错误")

    self.params_getter_tuple = tuple(param_getter_list)

  async def get_params_dict(self,req: Request):
    param_dict = {}
    for param_name,getter,param_define in self.params_getter_tuple:
      await getter(param_dict,param_name,req,param_define)
    return param_dict
