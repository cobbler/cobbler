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

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "serializer"

def serialize_item(obj, item):
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    datastruct = item.to_datastruct()
    fd = open(filename,"w+")
    fd.write(yaml.dump(datastruct))
    fd.close()
    return True

def serialize_delete(obj, item):
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    os.remove(filename)
    return True

def deserialize_item_raw(collection_type, item_name):
    # this new fn is not really implemented performantly in this module.
    # yet.
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (collection_type,item_name)
    if not os.path.exists(filename):
        return None
    fd = open(filename)
    datastruct = yaml.load(fd.read()).next()
    fd.close() 
    return datastruct

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    FIXME: Return False on access/permission errors.
    This should NOT be used by API if serialize_item is available.
    """
    ctype = obj.collection_type()
    if ctype == "settings":
        return True
    for x in obj:
        serialize_item(obj,x)
    return True

def deserialize_raw(collection_type):
    old_filename = "/var/lib/cobbler/%ss" % collection_type
    if collection_type == "settings":
         fd = open("/etc/cobbler/settings")
         datastruct = yaml.load(fd.read()).next()
         fd.close()
         return datastruct
    elif os.path.exists(old_filename):
         # for use in migration
         sys.stderr.write("reading from old config format: %s\n" % old_filename)
         fd = open(old_filename)
         datastruct = yaml.load(fd.read()).next()
         fd.close()
         return datastruct
    else:
         results = []
         files = glob.glob("/var/lib/cobbler/config/%ss.d/*" % collection_type)
         for f in files:
             fd = open(f)
             results.append(yaml.load(fd.read()).next())
             fd.close()
         return results    

def deserialize(obj,topological=False):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  
    """
    old_filename = "/var/lib/cobbler/%ss" % obj.collection_type()
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
       datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    if os.path.exists(old_filename):
       # we loaded it in from the old filename, so now migrate to new fmt
       sys.stderr.write("auto-removing old config format: %s\n" % old_filename)
       serialize(obj)
       os.remove(old_filename)
    return True

def __depth_cmp(item1, item2):
    if not item1.has_key("depth"):
       return 1
    if not item2.has_key("depth"):
       return -1
    return cmp(item1["depth"],item2["depth"])

if __name__ == "__main__":
    print deserialize_item_raw("distro","D1")


