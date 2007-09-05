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

MODULE_CACHE = {}

def serialize(obj):
    """
    Save a collection to disk or other storage.  
    """
    storage_module = __get_storage_module(obj.collection_type())
    storage_module.serialize(obj)
    return True

def deserialize(obj,topological=False):
    """
    Fill in an empty collection from disk or other storage
    """
    storage_module = __get_storage_module(obj.collection_type())
    return storage_module.deserialize(obj,topological)


def __get_storage_module(collection_type):

    if MODULE_CACHE.has_key(collection_type):
        return MODULE_CACHE[collection_type]
    config = cobbler_api.BootAPI()._config
    settings = config.settings()
    storage_module_name = settings.storage_modules.get(collection_type, None)
    if not storage_module_name:
        raise CX(_("Storage module not set for objects of type %s") % collection_type)
    storage_module = config.modules.get(storage_module_name, None)
    if not storage_module:
        raise CX(_("Storage module %s not present") % storage_module_name)
    MODULE_CACHE[collection_type] = storage_module
    return storage_module
  
