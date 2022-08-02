from .base_endpoint import Endpoint
from ..http.request import Request


class Router:
  def match_path(self,req: Request) -> Endpoint:
    pass
