from .app import Orange
from .router.api_router import ApiModule,ApiRouter
from .router.static_router import StaticRouter
from .http.response import json_resp,get_file_resp,get_file_resp_async,Response
from .http.request import Request
from .http.proxy import request,get_request
from .http.error import CloseTransport



# todo websocket 使用协议切换
# todo endpoint 使用 metadata
# todo 定义vo (valueObject) 基类,  增加json 直接解析
# endpoint  元数据 就是一些,关于路由函数的数据 比如解析数据等


