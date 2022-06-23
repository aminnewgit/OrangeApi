from typing import Callable


class Endpoint:
  def __init__(self,function:Callable,is_async:bool):
    self.function = function
    self.is_async:bool = is_async

