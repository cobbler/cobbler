import exceptions

class Serializable:

   def filename(self):
       return None

   def from_datastruct(self,datastruct):
       raise exceptions.NotImplementedError

   def to_datastruct(self):
       raise exceptions.NotImplementedError

