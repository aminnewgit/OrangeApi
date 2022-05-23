from orange import ApiModule, get_file_resp_async

api = ApiModule('test')

@api.get('/favicon.ico')
async def favicon():
  return await get_file_resp_async('service/static/favicon.ico')

@api.get('/static/vue.js')
async def send_vue():
  return await get_file_resp_async('service/static/vue.js')
  # return send_file('service/static/vue.js')

@api.get('/')
async def send_index():
  resp = await get_file_resp_async('service/static/index.html')
  return resp


# @api.get('/hello',is_async=False)
# def send_index():
#   return json_resp('hello')
