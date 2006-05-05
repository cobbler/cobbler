# Michael DeHaan <mdehaan@redhat.com>

import api
import utils
import syck  # PySyck 0.61 or greater, not syck-python 0.55
import msg

def serialize(obj):
   if obj.filename() is None:
      raise Exception("not serializable")
   fd = open(obj.filename(),"w+")
   datastruct = obj.to_datastruct()
   encoded = syck.dump(datastruct)
   fd.write(encoded)
   fd.close()
   return True

def deserialize(obj):
   if obj.filename() is None:
      raise Exception("not serializable")
   try:
       fd = open(obj.filename(),"r")
   except:
       print msg.m("parse_error") % obj.filename()
       return
   data = fd.read()
   datastruct = syck.load(data)
   fd.close()
   obj.from_datastruct(datastruct)
   return True
