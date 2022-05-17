import os,json

from email.utils import formatdate

def get_gmt_time():
  formatdate(None, usegmt=True)

# timeout 单位是秒
def get_expires_gmt_time(timeout):
  formatdate(None, usegmt=True)
