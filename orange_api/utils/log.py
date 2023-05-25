import traceback
from orange_kit.log import OrangeLog

orange_api_log = OrangeLog("ai_eval_service")
orange_api_log.enable_debug_log()

# todo 处理error ,记录request 的内容



def log_error(msg,req,err=None):
  if err is not None:
    traceback.print_exc()
  print(msg)