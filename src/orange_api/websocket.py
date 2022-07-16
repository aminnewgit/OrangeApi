import asyncio
import base64
import hashlib
import json
import struct

from orange_kit import json_dumps
from .http.response import Response, get_error_response

SUPPORTED_VERSIONS = ('13', '8', '7')
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

MSG_SOCKET_DEAD = "Socket is dead"
MSG_ALREADY_CLOSED = "Connection is already closed"
MSG_CLOSED = "Connection closed"

OPCODE_CONTINUATION = 0x00
OPCODE_TEXT = 0x01
OPCODE_BINARY = 0x02
OPCODE_CLOSE = 0x08
OPCODE_PING = 0x09
OPCODE_PONG = 0x0a

opcode_dict = {
  'test': 0x01,
  'binary': 0x02,
  'close': 0x08,
  'ping': 0x09,
  'pong': 0x0a,
}

opcode_to_type = {
  0x01:'test',
  0x02:'binary',
  0x08:'close',
  0x09:'ping',
  0x0a:'pong',
}

FIN_MASK = 0x80
OPCODE_MASK = 0x0f
MASK_MASK = 0x80
LENGTH_MASK = 0x7f

RSV0_MASK = 0x40
RSV1_MASK = 0x20
RSV2_MASK = 0x10

# bitwise mask that will determine the reserved bits for a frame header
HEADER_FLAG_MASK = RSV0_MASK | RSV1_MASK | RSV2_MASK

# https://zhuanlan.zhihu.com/p/407711596

class WebSocketError(Exception):
  pass


class WsMessageReader:
  def __init__(self,data: bytes):
    self.data = data
    self.pos = 0
    self.length = len(data)

  def read(self,size):
    if self.pos + size > self.length:
      raise WebSocketError("Unexpected EOF while decoding ws message")
    start = self.pos
    end = self.pos + size
    self.pos = end
    return self.data[start : end]


def mask_payload(mask, payload, length):
  payload = bytearray(payload)
  mask = bytearray(mask)
  for i in range(length):
    payload[i] ^= mask[i % 4]
  return payload

def decode_ws_frame(bytes_msg: bytes):

  reader = WsMessageReader(bytes_msg)

  data = reader.read(2)

  first_byte, second_byte = struct.unpack('!BB', data)

  fin = (first_byte & FIN_MASK) == FIN_MASK
  opcode = first_byte & OPCODE_MASK
  flags = first_byte & HEADER_FLAG_MASK
  length = second_byte & LENGTH_MASK

  # fine 最后一帧为1 还有后续帧为0
  # opcode
  # 0x00 continuation 0x01 text 0x02 binary
  # 0x08 close 0x09 ping 0x0a pong

  if opcode > 0x07:
    # fin = 0 // 这几种只有1帧
    if fin is False:
      raise WebSocketError(
        "Received fragmented control frame: {0!r}".format(data))

    # 并且长度不会超过125
    if length > 125:
      raise WebSocketError(
        "Control frame cannot be larger than 125 bytes: "
        "{0!r}".format(data))

  # message = cls(fin,opcode,flags,length)

  # 如果 length 等于 126 说明还有扩展长度数据
  if length == 126:
    # 16 bit length  2 + 2bytes  最大  65535  63kb
    data = reader.read(4)
    length = struct.unpack('!H', data)[0]

  elif length == 127:
    # 64 bit length  2 + 8bytes
    data = reader.read(8)
    length = struct.unpack('!Q', data)[0]

  has_mask = (second_byte & MASK_MASK) == MASK_MASK
  mask = None
  if has_mask:
    mask = reader.read(4)

  payload = reader.read(length)

  if mask is not None:
    payload = mask_payload(mask, payload, length)

  return opcode,payload

def encode_ws_frame(opcode, payload: bytes):
  # 服务器向客户端发送信息是不需要mask的
  length = len(payload)
  second_byte = 0
  extra = b""
  frame = bytearray()

  # fin 1 rsv1~3 1  1111 0000 0xF0
  # fin 1 rsv1~3 0  1000 0000 0xF0
  first_byte = opcode | 0x80

  # now deal with length complexities
  if length < 126:
    second_byte += length
  elif length <= 0xffff:
    second_byte += 126
    extra = struct.pack('!H', length)
  elif length <= 0xffffffffffffffff:
    second_byte += 127
    extra = struct.pack('!Q', length)
  else:
    raise WebSocketError("send payload too length")

  # if mask is not None:
  #   second_byte |= MASK_MASK

  frame.append(first_byte)
  frame.append(second_byte)
  frame.extend(extra)
  frame.extend(payload)

  # if mask is not None:
  #   frame.extend(mask)
  return frame

class WebSocketClient:
  def __init__(self):
    self.on_message = None
    self.on_close = None
    self.transport = None
    self.Data = None
    self.id = None
    self.is_close = False

  def exec_on_message(self,msg,opcode):
    if self.on_message is not None:
      self.on_message(msg,self)
    else:
      print(opcode_to_type.get(opcode),msg)

  def feed_data(self, data: bytes):
    # 0x01:'text', 0x02:'binary', 0x08:'close',0x09:'ping',0x0a:'pong',
    opcode,payload = decode_ws_frame(data)
    # print(opcode_to_type.get(opcode),payload)
    if opcode == 0x01 :
      payload = payload.decode('utf-8')
      self.exec_on_message(payload,opcode)
    elif opcode == 0x02:
      self.exec_on_message(payload, opcode)
    elif opcode == 0x08:
      self.close()
    # todo ping pong

  def close(self):
    self.transport.close()


  def clean(self):
    if self.on_close is not None:
      self.on_close(self)

  def _send(self, opcode, data):
    frame = encode_ws_frame(opcode,data)
    self.transport.write(frame)

  def send_json(self,data):
    data = json.dumps(data, ensure_ascii=False)
    self._send(0x01,data.encode('utf-8'))

  def send_text(self,text):
    self._send(0x01,text.encode('utf-8'))

  def send_text_from_bytes(self, text: bytes):
    self._send(0x01, text)

  def send_bytes(self,data):
    self._send(0x02,data)

  def can_upgrade(self, req):

    headers = req.headers
    # Can only upgrade connection if using GET method.
    status_code = 101
    if req.method != 'GET': status_code = 405
    elif headers.get('connection') != "Upgrade": status_code = 400
    elif headers.get("upgrade") != "websocket": status_code = 400
    elif headers.get("sec-websocket-version") not in SUPPORTED_VERSIONS: status_code = 400
    else:
      key = headers.get("sec-websocket-key")
      if key is None:
        return get_error_response(400)

      key = key.strip()
      try:
        key_len = len(base64.b64decode(key))
      except TypeError:
        # "Invalid key:
        return get_error_response(400)

      if key_len != 16:
        return get_error_response(400)

      # Sec-WebSocket-Extensions:

      accept = base64.b64encode(hashlib.sha1((key + GUID).encode("latin-1")).digest()).decode("latin-1")

      headers =  [
        ("Upgrade", "websocket"),
        ("Connection", "Upgrade"),
        ("Sec-WebSocket-Accept", accept)
      ]
      self.transport = req.transport
      return Response(None,headers,status_code)
    return get_error_response(status_code)

class WsClientChannelBase:

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

  def accept_client(self,req):
    ws_client: WebSocketClient
    resp, ws_client = req.upgrade_websocket()

    if ws_client is not None:

      def on_message(msg,_ws_client):
        self.on_message(msg,_ws_client)

      def on_close(_ws_client):
        self.on_close(_ws_client)

      ws_client.on_message = on_message
      ws_client.on_close = on_close
      self.client_login(ws_client)
    return resp

  def client_login(self, ws_client):
    pass

  def on_message(self, msg, ws_client):
    pass

  def on_close(self,ws_client):
    pass
