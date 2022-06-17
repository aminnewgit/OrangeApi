def line_to_hump(string):
  upper = False
  new_str = ''
  for char in string:
    if upper is True:
      new_str += char.upper()
      upper = False
    elif char == '_':
      upper = True
    else:
      new_str += char
  return new_str