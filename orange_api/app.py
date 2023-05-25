import asyncio
import traceback

from orange_api.router.base import BaseEndpoint
from orange_kit.log import OrangeLog

from .http.error import CloseTransport
from .http.response import get_error_response
from .http.request import Request


#最大 body 的长度 一般情况是2M 如果超过6m的body 需要在路由函数设置
from .server import run_server
from .utils.log import orange_api_log

default_max_body_length = 1024*1024*6  #6m
log = OrangeLog('orange_api',enable_debug=False)

class Orange(object):
  __slots__ = (
    "router_list","server","backlog","timeout",
    "exception_handler","init_func_list","auto_close_func_list"
  )
  def __init__(self):
    # 中间件 有去有回
    # self.middleware_list = []
    self.router_list = []
    self.server = None
    self.backlog = 1000
    self.timeout = 20
    self.exception_handler = None
    self.init_func_list = []
    self.auto_close_func_list = []

  def start(self,port=5000,host='0.0.0.0'):
    try:
      asyncio.run(self.__start(port,host))
    except KeyboardInterrupt:
      # 在本例中，只有Ctrl-C会终止loop，然后像前例中进行善后工作
      # print('<Got signal: SIGINT, shutting down.>')
      for ac_func in self.auto_close_func_list:
        if ac_func is not None: ac_func()
      print("shutting down")

  async def __start(self,port,host):
    # todo 通用配置类 环境配置
    for (ac_func, is_async) in self.init_func_list:
      if is_async:
        auto_close_func = await ac_func()
      else:
        auto_close_func = ac_func()
      self.auto_close_func_list.append(auto_close_func)

    await run_server(self, port, host)

  def add_router(self,router):
    """添加路由模块,优先级按添加顺序执行"""
    self.router_list.append(router)

  def add_exception_handler(self, handler):
     self.exception_handler = handler

  def add_init_func(self,func,is_async=True):
    """
    添加初始化函数, 这些函数按添加顺序, 在http服务启动前运行
    如果需要在程序结束后执行释放操作, 初始化函数可以返回一个
    函数用于释放操作, 这个函数不能是 async 函数
    """
    self.init_func_list.append((func,is_async))

  async def __call__(self, req:Request):
    # code = 200
    if req.body_length > default_max_body_length:
      # 检测body长度是否超限 超过限制的 文件要分块上传
      orange_api_log.error('body too len')
      req.transport.close()
      return

    try:
      endpoint: BaseEndpoint | None = None
      for router in self.router_list:
        endpoint = router.match_path(req)
        if endpoint is not None: break
      if endpoint is None:
        # 路由不存在
        resp = get_error_response(404)
      else:
        # 执行路由函数
        resp = await endpoint.execute_func(req)
        if resp is None and req.response_over is False:
          # 路由函数没有正常返回响应体
          orange_api_log.error('没有返回值,也没有发送response')
          resp = get_error_response(500)
        elif req.response_over is True:
          # 在路由函数中已经发送过response
          return
    except CloseTransport as ct:
        # 手动关闭连接
        req.transport.close()
        orange_api_log.error(ct.msg)
        return
    except asyncio.CancelledError:
      # task被取消时出现的异常
      orange_api_log.error('task cancel')
      raise
    except BaseException as e:
      resp = None
      if self.exception_handler is not None:
        resp = self.exception_handler(e)
      if resp is None:
        print(e.__class__)
        traceback.print_exc()
        # code = 500
        resp = get_error_response(500)

    try:
      req.send(resp.build())
      req.response_over = True
    except BaseException as e:
      # resp没有build方法, 返回类型不是正确的response类型
      if resp is None:
        print(e.__class__)
        traceback.print_exc()
        orange_api_log.error(traceback.format_exc())
        resp = get_error_response(500)
        req.send(resp.build())
        req.response_over = True

