"""
Serializer code for cobbler
Now adapted to support different storage backends

Copyright 2006-2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import errno
import os
from utils import _
import fcntl

from cexceptions import *
import utils
import api as cobbler_api

LOCK_ENABLED = True
LOCK_HANDLE = None

def __grab_lock():
   if not LOCK_ENABLED:
       return
   if not os.path.exists("/var/lib/cobbler/lock"):
       fd = open("/var/lib/cobbler/lock","w+")
       fd.close()
   LOCK_HANDLE = open("/var/lib/cobbler/lock","r")
   fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_EX)

def __release_lock():
   if not LOCK_ENABLED:
       return
   LOCK_HANDLE = open("/var/lib/cobbler/lock","r")
   fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
   LOCK_HANDLE.close()

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
        # print "DEBUG: WARNING: full serializer"
        rc = storage_module.serialize(collection)
    else:
        # print "DEBUG: partial serializer"
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
        # print "DEBUG: full delete"
        rc = storage_module.serialize(collection)
    else:
        # print "DEBUG: partial delete"
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

def __get_storage_module(collection_type):
    """
    Look up serializer in /etc/cobbler/modules.conf
    """    
    capi = cobbler_api.BootAPI()
    return capi.get_module_from_file("serializers",collection_type)


