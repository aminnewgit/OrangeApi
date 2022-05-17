import asyncio

def read_once_all_binary(path):
  with open(path,'rb') as f:
    return f.read()

def write_once(path,data,mode):
  with open(path,mode) as f:
    f.write(data)

def open_write_not_close(path,data,mode):
  f = open(path,mode)
  f.write(data)
  return f

def write(fd,data):
  fd.write(data)

def close(fd):
  fd.close()


def async_read_once_all_binary(loop,path):
  return loop.run_in_executor(None, read_once_all_binary, path)

def async_write_once(loop,path,data,mode='wb'):
  return loop.run_in_executor(None,write_once,path,data,mode)

def async_open_write_not_close(loop,path,data,mode='wb'):
  return loop.run_in_executor(None,open_write_not_close,path,data,mode)

def async_write(loop,fd,data):
  return loop.run_in_executor(None,write, fd, data)

def async_close(loop,fd):
  return loop.run_in_executor(None,close,fd)


