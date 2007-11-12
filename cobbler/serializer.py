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
from rhpl.translate import _, N_, textdomain, utf8

from cexceptions import *
import utils
import api as cobbler_api

def serialize(obj):
    """
    Save a collection to disk or other storage.  
    """
    storage_module = __get_storage_module(obj.collection_type())
    storage_module.serialize(obj)
    return True

def serialize_item(collection, item):
    """
    Save an item.
    """
    storage_module = __get_storage_module(collection.collection_type())
    save_fn = getattr(storage_module, "serialize_item", None)
    if save_fn is None:
        # print "DEBUG: WARNING: full serializer"
        return storage_module.serialize(collection)
    else:
        # print "DEBUG: partial serializer"
        return save_fn(collection,item)

def serialize_delete(collection, item):
    """
    Delete an object from a saved state.
    """
    storage_module = __get_storage_module(collection.collection_type())
    delete_fn = getattr(storage_module, "serialize_delete", None)
    if delete_fn is None:
        # print "DEBUG: full delete"
        return storage_module.serialize(collection)
    else:
        # print "DEBUG: partial delete"
        return delete_fn(collection,item)
    

def deserialize(obj,topological=False):
    """
    Fill in an empty collection from disk or other storage
    """
    storage_module = __get_storage_module(obj.collection_type())
    return storage_module.deserialize(obj,topological)

def deserialize_raw(collection_type):
    """
    Return the datastructure corresponding to the serialized
    disk state, without going through the Cobbler object system.
    Much faster, when you don't need the objects.
    """
    storage_module = __get_storage_module(collection_type)
    return storage_module.deserialize_raw(collection_type)

def __get_storage_module(collection_type):
    """
    Look up serializer in /etc/cobbler/modules.conf
    """    
    capi = cobbler_api.BootAPI()
    return capi.get_module_from_file("serializers",collection_type)


