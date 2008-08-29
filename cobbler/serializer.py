"""
Serializer code for cobbler
Now adapted to support different storage backends

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

import errno
import os
from utils import _
import fcntl
import traceback
import sys
import signal

from cexceptions import *
import api as cobbler_api

LOCK_ENABLED = True
LOCK_HANDLE = None
BLOCK_SIGNAL = True

def handler(num,frame): 
   print sys.stderr, "Ctrl-C not allowed during writes.  Please wait."
   return True
    
def no_ctrl_c():
   signal.signal(signal.SIGINT, handler)
   return True

def ctrl_c_ok():
   signal.signal(signal.SIGINT, signal.default_int_handler)
   return True   

def __grab_lock():
    """
    Dual purpose locking:
    (A) flock to avoid multiple process access
    (B) block signal handler to avoid ctrl+c while writing YAML
    """
    try:
        if LOCK_ENABLED:
            if not os.path.exists("/var/lib/cobbler/lock"):
                fd = open("/var/lib/cobbler/lock","w+")
                fd.close()
            LOCK_HANDLE = open("/var/lib/cobbler/lock","r")
            fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_EX)
        if BLOCK_SIGNAL:
            no_ctrl_c()
        return True
    except:
        # this is pretty much FATAL, avoid corruption and quit now.
        traceback.print_exc()
        sys.exit(7)

def __release_lock():
    if LOCK_ENABLED:
        LOCK_HANDLE = open("/var/lib/cobbler/lock","r")
        fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
        LOCK_HANDLE.close()
    if BLOCK_SIGNAL:
        ctrl_c_ok()
    return True

def serialize(obj):
    """
    Save a collection to disk or other storage.  
    """
    __grab_lock()
    storage_module = __get_storage_module(obj.collection_type())
    storage_module.serialize(obj)
    __release_lock()
    return True

def serialize_item(collection, item):
    """
    Save an item.
    """
    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    save_fn = getattr(storage_module, "serialize_item", None)
    if save_fn is None:
        rc = storage_module.serialize(collection)
    else:
        rc = save_fn(collection,item)
    __release_lock()
    return rc

def serialize_delete(collection, item):
    """
    Delete an object from a saved state.
    """
    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    delete_fn = getattr(storage_module, "serialize_delete", None)
    if delete_fn is None:
        rc = storage_module.serialize(collection)
    else:
        rc = delete_fn(collection,item)
    __release_lock()
    return rc

def deserialize(obj,topological=False):
    """
    Fill in an empty collection from disk or other storage
    """
    __grab_lock()
    storage_module = __get_storage_module(obj.collection_type())
    rc = storage_module.deserialize(obj,topological)
    __release_lock()
    return rc

def deserialize_raw(collection_type):
    """
    Return the datastructure corresponding to the serialized
    disk state, without going through the Cobbler object system.
    Much faster, when you don't need the objects.
    """
    __grab_lock()
    storage_module = __get_storage_module(collection_type)
    rc = storage_module.deserialize_raw(collection_type)
    __release_lock()
    return rc

def deserialize_item(collection_type, item_name):
    """
    Get a specific record.
    """
    __grab_lock()
    storage_module = __get_storage_module(collection_type)
    rc = storage_module.deserialize_item(collection_type, item_name)
    __release_lock()
    return rc

def deserialize_item_raw(collection_type, item_name):
    __grab_lock()
    storage_module = __get_storage_module(collection_type)
    rc = storage_module.deserialize_item_raw(collection_type, item_name)
    __release_lock()
    return rc

def __get_storage_module(collection_type):
    """
    Look up serializer in /etc/cobbler/modules.conf
    """    
    capi = cobbler_api.BootAPI()
    return capi.get_module_from_file("serializers",collection_type,"serializer_yaml")

if __name__ == "__main__":
    __grab_lock()
    __release_lock()

