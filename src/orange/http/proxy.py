import asyncio
from ..server import req_dict
from .request import Request

class ProxyRequest:
  def __getattr__(self, item):
    task_id = id(asyncio.current_task())
    req = req_dict[task_id]
    try:
      return object.__getattribute__(req,item)
    except KeyError:
      return None

  def __setattr__(self, key, value):
    task_id = id(asyncio.current_task())
    req = req_dict[task_id]
    return object.__setattr__(req, key,value)


def  get_request() -> Request:
  task_id = id(asyncio.current_task())
  return req_dict[task_id]

def _get_request() -> Request:
  return ProxyRequest()

request = _get_request()