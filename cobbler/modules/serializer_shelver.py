"""
Serializer code for cobbler

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import distutils.sysconfig
import os
import sys
import glob
import traceback

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _
import utils
import yaml   # Howell-Clark version
import cexceptions
import os
import shelve
#import gdbm
import dumbdbm

#d = gdbm.open(FILENAME, 'c')
#d.reorganize()
#d.close() 

class DbInstance:
    __shared_state = {}
    __has_loaded = False

    def __init__(self):
       self.__dict__ = DbInstance.__shared_state
       if not DbInstance.__has_loaded:
           filename = "/var/lib/cobbler/config/shelf_db"
           if not os.path.exists(filename):
               db_pre = dumbdbm.open(filename, 'c')
               db_pre.close()
           self.db = shelve.open(filename, 'c', writeback=True)
      
def __open():
    dbi = DbInstance()
    return dbi.db

def __close(db):
    pass

def register():
    """
    The mandatory cobbler module registration hook.
    """
    # FIXME: run only when used, not loaded
    db = __open()
    if not db.has_key("distro"): 
       db["distro"] = {}
    if not db.has_key("profile"):
       db["profile"] = {}
    if not db.has_key("system"):
       db["system"] = {}
    if not db.has_key("repo"):
       db["repo"] = {}
    if not db.has_key("image"):
       db["image"] = {}
    if not db.has_key("ip_map"):
       db["ip_map"] = {}
    if not db.has_key("mac_map"):
       db["mac_map"] = {}
    __close(db)
    return "serializer"

def serialize_item(obj, item, sync=True):
    datastruct = item.to_datastruct()
    db = __open()
    # print "serializing: %s, %s <- %s" % (item.TYPE_NAME, item.name, datastruct)
    db[item.TYPE_NAME][item.name] = datastruct
    if sync:
        db.sync()
    __close(db)
    return True

def serialize_delete(obj, item):
    db = __open()
    # print "writing: %s" % item.TYPE_NAME
    del db[item.TYPE_NAME][name]
    db.sync()
    __close(db)
    return True

def deserialize_item_raw(collection_type, item_name):
    db = __open()
    # print "reading raw: %s" % collection_type
    data = db[collection_type][item_name]
    __close(db)
    return data

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    FIXME: Return False on access/permission errors.
    This should NOT be used by API if serialize_item is available.
    """
    db = __open()
    if obj.collection_type() == "settings":
        return True
    for x in obj:
        serialize_item(obj,x,sync=False)
    db.sync()
    return True

def deserialize_raw(collection_type):
    if collection_type == "settings":
         fd = open("/etc/cobbler/settings")
         datastruct = yaml.load(fd.read()).next()
         fd.close()
         return datastruct
    else:
         db = __open()
         # print "getting keys for: %s" % collection_type
         keys = db[collection_type].keys()
         results = []
         for k in keys:
             # print "found key: %s" % k
             results.append(db[collection_type][k])
         __close(db)
         return results    

def deserialize(obj,topological=True):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  
    """
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
       datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    return True

def __depth_cmp(item1, item2):
    d1 = item1.get("depth",1)
    d2 = item2.get("depth",1)
    return cmp(d1,d2)



