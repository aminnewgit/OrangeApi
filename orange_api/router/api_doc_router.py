
from orange_kit import json_dumps
from orange_kit.model.base_enum import get_enum_dict
from orange_kit.model.vo import get_vo_base_dict
from .api_router import ApiRouter
from ..http.response import Response

class ApiDataEndpoint:
  __slots__ = ("doc_data_resp","api_data", "body")

  def __init__(self, api_data):
    self.api_data = api_data
    self.doc_data_resp = None
    self.body = None

  async def execute_func(self,req):
    if self.body is None:
      enum_dict = get_enum_dict()
      enum_dict = {k: v.__get_define_tuple__() for k, v in enum_dict.items()}
      vo_base_dict = get_vo_base_dict()
      vo_base_dict = {k: v.get_field_define_list() for k, v in vo_base_dict.items()}
      resp_data = {
        'code': 1,
        'data': {
          'api': self.api_data,
          'enumDict': enum_dict,
          'voBaseDict': vo_base_dict,
        }
      }
      self.body = json_dumps(resp_data).encode('utf-8')

    headers = [
      ('Content-Type', "application/json"),
      ('connection', 'keep-alive'),
      ('Access-Control-Allow-Origin', '*'),
      ('Access-Control-Allow-Headers', 'X-Requested-With'),
      ('Access-Control-Allow-Methods', 'GET,POST,OPTIONS'),
    ]
    resp = Response(self.body, headers)
    return resp

class ApiDocRouter:

  __slots__ = ("api_doc_data_endpoint","api_doc_url")

  def __init__(self, api_router:ApiRouter):
    doc_data = api_router.get_doc_data()
    self.api_doc_data_endpoint = ApiDataEndpoint(doc_data)
    self.api_doc_url = api_router.__url_prefix__ + "/api-doc-data"
    print(self.api_doc_url)

  def match_path(self, req):
    if req.method == "GET" and req.path == self.api_doc_url:
      return self.api_doc_data_endpoint




