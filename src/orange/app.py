import asyncio
import traceback
from .router import ApiRouter
from .server import start
from .http.error import SendError, get_error_response, ResponseNow, CloseTransport
from .http.request import Request
from .log import log_error


#最大 body 的长度 一般情况是2M 如果超过6m的body 需要在路由函数设置
default_max_body_length = 1024*1024*6  #6m


class Orange(object):
  def __init__(self):
    # 中间件 有去有回
    # self.middleware_list = []
    self.router_list = []
    self.server = None
    self.backlog = 1000
    self.timeout = 20

  def run_server(self,port=5000,host='0.0.0.0'):
    start(self, port, host)

  # todo 写router基类
  def add_router(self,router):
    self.router_list.append(router)

  async def __call__(self, req:Request):
    code = 200

    if req.body_length > default_max_body_length:
      # 检测body长度是否超限 超过限制的 文件要分块上传
      # todo 要返回信息 或许要放到服务器
      print('body too len')
      req.transport.close()
      return

    try:
      endpoint = None
      for router in self.router_list:
        endpoint = router.match_path(req)
        if endpoint is not None: break
      if endpoint is None:
        # 路由不存在
        resp = get_error_response(404)
      else:
        # 执行路由函数
        resp = await endpoint.function()
        if resp is None and req.response_over is False:
          # 没有返回值,也没有发送response
          code = 500
          resp = get_error_response(500)
        elif req.response_over is True:
          # 在路由函数中已经发送过response
          return
    except ResponseNow as rn:
      # 路由函数内部通过异常直接发送响应
      resp = rn.resp
    except CloseTransport as ct:
        # 手动关闭连接
        req.transport.close()
        log_error(ct.msg,req)
        return
    except SendError as e:
      # 通过抛出sendError来终止本次请求,返回错误状态,
      code = e.code
      resp = get_error_response(code)
    except asyncio.CancelledError:
      # task被取消时出现的异常
      print('task cancel')
      raise
    except BaseException as e:
      print(e.__class__)
      traceback.print_exc()
      code = 500
      resp = get_error_response(500)
    req.send(resp)
    req.response_over = True
    print(req.method, req.url, code)

