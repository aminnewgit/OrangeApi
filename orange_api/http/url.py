def formate_url_path(path: str | None):
  if path is None: return None
  path = path.strip()
  if path == '': return None

  if path.startswith("/") is False:
    path = "/" + path

  if path.endswith("/"):
    path = path[:-1]

  return path