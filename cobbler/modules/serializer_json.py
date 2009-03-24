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
import simplejson

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _
import utils
from cexceptions import *
import os

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "serializer"

def serialize_item(obj, item):
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    datastruct = item.to_datastruct_with_cache()
    fd = open(filename,"w+")
    ydata = simplejson.dumps(datastruct, sort_keys=True, indent=4)
    if ydata is None or ydata == "":
       raise CX("internal json error, tried to write empty file to %s, data was %s" % (filename, datastruct))
    fd.write(ydata)
    fd.close()
    return True

def serialize_delete(obj, item):
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    if os.path.exists(filename):
        os.remove(filename)
    return True

def deserialize_item_raw(collection_type, item_name):
    # this new fn is not really implemented performantly in this module.
    # yet.
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (collection_type,item_name)
    if not os.path.exists(filename):
        return None
    fd = open(filename)
    datastruct = simplejson.loads(fd.read())
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
    results = []
    files = glob.glob("/var/lib/cobbler/config/%ss.d/*" % collection_type)
    for f in files:
        fd = open(f)
        ydata = fd.read()
        if ydata is None or ydata == "":
            raise CX("error, empty file %s" % f)
        try:
            datastruct = simplejson.loads(ydata)
        except:
            raise CX("error parsing json file: %s" % f)
        results.append(datastruct)
        fd.close()
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

if __name__ == "__main__":
    print deserialize_item_raw("distro","D1")


