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

    # FIXME: this is always fixed currently, and should not be.
    return cobbler_api.BootAPI().modules["serializer_yaml"]

  
