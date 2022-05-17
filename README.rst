OrangeApi
=============
OrangeApi 是一个轻量web框架, 并且附带了web服务, 无需任何额外的库就可以运行.OrangeApi不是WSGI框架,
整个框架基于asyncio,在不选择uvloop作为事件循环的时候windows和linux均可运行.原生支持websocket.

写这个框架时有一个想法,就是除了python内建库不在使用其他库,自己就可以独立运行

python要求3.6以上

最小例子:

.. code-block:: python

    from orange import Orange,ApiRouter,ApiModule,send_file,json_resp

    api = ApiModule('test')

    @api.get('/')
    async def favicon():
      return json_resp("hello_word")


    @api.get('/favicon.ico')
    async def favicon():
      return send_file('static/favicon.ico')

    api_router = ApiRouter()

    api_router.add(ws_api)

    app = Orange()

    app.add_router(api_router)

    # app.print_routes()
    app.run_server(port=5606)



安装
------------
暂时只能复制到项目下使用, 后面会更新pip安装
