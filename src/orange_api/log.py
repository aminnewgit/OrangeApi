import traceback

def log_error(msg,req,err=None):
  if err is not None:
    traceback.print_exc()
  print(msg)