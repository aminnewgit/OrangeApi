import json

from orange import ApiModule,json_resp,get_request

from orange.http.response import Response
from orange.websocket import WebSocketClient


api = ApiModule('test')



ws_dict = {}

class WsUser:
  def __init__(self,user_id,client):
    self.id = user_id
    self.client = client


def broadcast(data):
  for user in ws_dict.values():
    # if user.id != client.id :
    client: WebSocketClient = user.client
    client.send_json(data)

def on_message(msg,client):
  user = ws_dict.get(client.id)
  msg = json.loads(msg)
  data = {
    'userId': user.id,
    'type':'msg',
    'data': msg.get('data'),
    'time': msg.get('time')
  }
  broadcast(data)

def on_close(client: WebSocketClient):
  user = ws_dict.pop(client.id)
  data = {
    "type": "logout",
    "userId": user.id,
  }
  broadcast(data)

def user_login(user_id,ws_client):
  user = WsUser(user_id, ws_client)
  data = {
    "type": "login",
    "userId": user_id,
  }
  broadcast(data)
  ws_dict[ws_client.id] = user
  ws_client.on_message = on_message
  ws_client.on_close = on_close
  print(f'用户登录:{user_id},当前用户数: ', len(ws_dict))

@api.get('/ws')
async def send_index():
  req = get_request()
  resp: Response
  query = req.parse_query()
  user_id = query.get('id')
  # todo 先连接 ws 返回错误信息 然后断开
  if user_id is None: return json_resp("not user")
  ws_client: WebSocketClient
  resp,ws_client = req.upgrade_websocket()
  if ws_client is not None:
    user_login(user_id, ws_client)
  return resp