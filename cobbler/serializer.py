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

import yaml                # Howell-Clark version

from cexceptions import *
import utils
import api as cobbler_api
import modules.serializer_yaml as serializer_yaml
import ConfigParser

MODULE_CACHE = {}
cp = ConfigParser.ConfigParser()
cp.read("/etc/cobbler/modules.conf")

def serialize(obj):
    """
    Save a collection to disk or other storage.  
    """
    
    storage_module = __get_storage_module(obj.collection_type())
    storage_module.serialize(obj)
    return True

def serialize_item(collection, item):
    storage_module = __get_storage_module(collection.collection_type())
    save_fn = getattr(storage_module, "serialize_item", None)
    if save_fn is None:
        # print "DEBUG: WARNING: full serializer"
        return storage_module.serialize(collection)
    else:
        # print "DEBUG: partial serializer"
        return save_fn(collection,item)

def serialize_delete(collection, item):
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
    storage_module = __get_storage_module(collection_type)
    return storage_module.deserialize_raw(collection_type)

def __get_storage_module(collection_type):


    if not MODULE_CACHE.has_key(collection_type):
         value = cp.get("serializers",collection_type)
         module = cobbler_api.BootAPI().modules[value]
         MODULE_CACHE[collection_type] = module
         return module
    else:
         return MODULE_CACHE[collection_type]

