import asyncio

from orange_kit import json_dumps
from .websocket_client import WebSocketClient


class WsServiceBase:
  def accept_client(self, req):
    ws_client: WebSocketClient
    resp, ws_client = req.upgrade_websocket()
    if ws_client is not None:
      self.client_login(ws_client)
    return resp


  def client_login(self, ws_client):
    pass



class WsChannelBase:

  def __init__(self):
    self.client_list = []
    self.client_dict = {}

  def broadcast(self,data):
    loop = asyncio.get_running_loop()
    # loop.run_in_executor(None, self.__broadcast_task, data)
    loop.create_task(self.__broadcast_task(data))

  async def __broadcast_task(self, data):
    # print('broadcast',data)
    data = json_dumps(data)
    data = data.encode("utf-8")
    for client in self.client_list:
      # if user.id != client.id :
      ws: WebSocketClient = client.ws_client
      ws.send_text_from_bytes(data)

  def add_client(self,client,data):
    pass

  def remove_client(self,client,data):
    pass

  async def on_cmd(self,client,data):
    pass