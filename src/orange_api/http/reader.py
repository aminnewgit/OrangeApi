import io

# StringIO顾名思义就是在内存中读写str
# StringIO操作的只能是str，
# 如果要操作二进制数据，就需要使用BytesIO。


# 缓存中数据小于给定的size 就一直从数据源中按块读取数据,
# 直到数据源中不再能读取数据 且 总数居大小 小于size 返回所有数据
# 如果读取处的数据总数大于size 只返回size大小的数据 多余的留在缓存中
# 如果size为none且缓存中有数据,就直接返回缓存中的所有数据
# 如果size 为None 缓存中没有数据 直接从数据源读取一次数据

class Reader(object):
  def __init__(self,sock,sock_read_size=8192):
    self.buffer = io.BytesIO()
    self.sock = sock
    self.sock_read_size = sock_read_size

  def get_data_from_sock(self):
    # BlockingIOError: [Errno 11] Resource temporarily unavailable 错误
    try:
      return self.sock.recv(self.sock_read_size)
    except BlockingIOError:
      return

  def read(self, size=None):
    if size == 0:
      return b""
    if size < 0:
      size = None

    #  第一个参数 为 偏移量，就是将光标移动几个位置
    #  第二个参数 为 相对于谁偏移
    # 一共有 3个值： 默认值就是 0
    # 0代表从文件开头开始算起，
    # 1代表从当前位置开始算起，
    # 2代表从文件末尾算起。
    self.buffer.seek(0, 2)  # 跳转到缓存末尾


    # tell() 函数 返回光标当前位置
    # 如果size为none 并且 缓存光标不在0位置(意味着缓存有数据)
    # 就直接返回缓存中的所有数据
    if size is None and self.buffer.tell():
      d = self.buffer.getvalue()
      self.buffer = io.BytesIO()
      return d

    # 如果size 为None 缓存中没有数据 直接从socket读取一次数据
    if size is None:
      d = self.get_data_from_sock()
      return d

    # 一直读取到给定的 size 或接受不到数据
    while self.buffer.tell() < size:
      chunk = self.get_data_from_sock()
      if not chunk:
        d = self.buffer.getvalue()
        self.buffer = io.BytesIO()
        return d
      self.buffer.write(chunk)

    data = self.buffer.getvalue()
    self.buffer = io.BytesIO()
    self.buffer.write(data[size:])
    return data[:size]

  # 向缓存尾部追加数据
  def push(self, data):
    self.buffer.seek(0, 2)
    self.buffer.write(data)