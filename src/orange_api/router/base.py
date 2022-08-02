from typing import Callable
from ..http.request import Request

# 这两个类为endpoint和router的标准形式, 可以不继承 只要有对应属性就可以

class BaseEndpoint:
  __slots__ = ("execute_func","is_async")
  def __init__(self,function:Callable):
    self.execute_func:Callable = function  # 执行函数


class BaseRouter:
  def match_path(self,req: Request) -> BaseEndpoint:
    pass
