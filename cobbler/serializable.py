import exceptions

class Serializable:

   def filename():
       return None

   def from_datastruct(datastruct):
       raise exceptions.NotImplementedError

   def to_datastruct():
       raise exceptions.NotImplementedError

