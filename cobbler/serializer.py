# Michael DeHaan <mdehaan@redhat.com>

import api
import util

def serialize(obj):
   fd = open(obj.filename(),"w+")
   datastruct = obj.to_datastruct()
   yaml = syck.dump(datastruct)
   fd.write(yaml)
   fd.close()
   return True

def deserialize(obj):
   fd = open(obj.filename(),"r")
   data = fd.read()
   datastruct = yaml.load(data)
   fd.close()
   return obj.from_datastruct(datastruct)
