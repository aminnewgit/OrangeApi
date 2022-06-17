from abc import ABCMeta
from orange.vo.utils import line_to_hump


class __VoMetaclass(ABCMeta):
  def __new__(mcs, name, bases, namespace, **kwargs):
    if name != "VoBase":
      # print(name,namespace)
      an_dict = namespace.get("__annotations__")
      field_list = []
      field_dict = {}
      field_name_list = []
      if an_dict is not None:
        for index,(field_name,field_type) in enumerate(an_dict.items()):
          # 处理字段定义
          field = namespace.get(field_name)
          if field is None:
            field = VoField(field_name)
          field.name = field_name
          field.type = field_type
          field.index = index
          field.camel_case = line_to_hump(field_name)   # 转驼峰

          # 字段索引
          field_list.append(field)
          field_dict[field_name] = field
          field_name_list.append(field_name)

          # 给类 属性复制 属性名 方便快速引用
          namespace[field_name] = field_name

      namespace["__field_name_list__"] = tuple(field_name_list)
      namespace["__field_list__"] = tuple(field_list)
      namespace["__field_dict__"] = field_dict


    return super().__new__(mcs, name, bases, namespace, **kwargs)

class VoBase(metaclass=__VoMetaclass):
  """value object base class"""

  __field_name_list__: tuple
  __field_list__: tuple
  __field_dict__: dict

  def get_camel_case_dict(self):
    data = self.__dict__
    out_dict = {}
    for field in self.__class__.__field_list__:
      out_dict[field.camel_case] = data.get(field.name)
    return out_dict

  def __repr__(self):
    return f"{self.__class__.__name__} {self.__dict__.__repr__()}"

  def __init__(self,data_dict=None):
    if data_dict is None :
      for field in self.__class__.__field_list__:
        self.__setattr__(field.name, None)
    else:
      for field in self.__class__.__field_list__:
        val = data_dict.get(field.name)
        if val is None:
          val = data_dict.get(field.camel_case)
        self.__setattr__(field.name,val)

  def __init_by_camel_case__(self,data_dict):
    for field in self.__class__.__field_list__:
      val = data_dict.get(field.camel_case)
      self.__setattr__(field.name, val)


class VoField:
  desc:str

  __slots__ = ("desc","name",'db_map_json','index','camel_case','type')

  def __init__(self,desc,db_map_json = False):
    self.desc = desc
    self.name = None
    self.db_map_json = db_map_json
    self.index = None
    self.camel_case = None
    self.type = None

  def __repr__(self):
    return "VoField"