"""
Serializer code for cobbler.
Experimental:  mongodb version

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
James Cammarata <jimi@sngx.net>

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
import traceback
import exceptions

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _
import utils
from cexceptions import *
import os
import ConfigParser

pymongo_loaded = False

try:
    from pymongo import Connection
    pymongo_loaded = True
except:
    # FIXME: log message
    pass

cp = ConfigParser.ConfigParser()
cp.read("/etc/cobbler/mongodb.conf")

host = cp.get("connection","host")
port = int(cp.get("connection","port"))
mongodb = None

def __connect():
    # TODO: detect connection error
    global mongodb
    try:
        mongodb = Connection('localhost', 27017)['cobbler']
        return True
    except:
        # FIXME: log error
        return False

def register():
    """
    The mandatory cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    if not pymongo_loaded:
        return ""
    return "serializer"

def what():
    """
    Module identification function
    """
    return "serializer/mongodb"

def serialize_item(obj, item):
    if not __connect():
        # FIXME: log error
        return False
    collection = mongodb[obj.collection_type()]
    data = collection.find_one({'name':item.name})
    if data:
        collection.update({'name':item.name}, item.to_datastruct())
    else:
        collection.insert(item.to_datastruct())
    return True

def serialize_delete(obj, item):
    if not __connect():
        # FIXME: log error
        return False
    collection = mongodb[obj.collection_type()]
    collection.remove({'name':item.name})
    return True

def deserialize_item_raw(collection_type, item_name):
    if not __connect():
        # FIXME: log error
        return False
    collection = mongodb[obj.collection_type()]
    data = collection.find_one({'name':item.name})
    return data

def serialize(obj):
    """
    Save an object to the database.
    """
    # TODO: error detection
    ctype = obj.collection_type()
    for x in obj:
        serialize_item(obj,x)
    return True

def deserialize_raw(collection_type):
    if not __connect():
        # FIXME: log error
        return False
    collection = mongodb[collection_type]
    return collection.find()

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

