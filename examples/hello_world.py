from src.orange import ApiModule, send_file, ApiRouter, Orange, json_resp

api = ApiModule('test')


@api.get('/')
async def favicon():
  return json_resp("hello")


api_router = ApiRouter()
api_router.add(api)

app = Orange()
app.add_router(api_router)

# app.print_routes()
app.run_server(port=6060)

