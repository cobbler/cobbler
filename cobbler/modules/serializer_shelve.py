"""
Serializer code for cobbler

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

NOTE: as it stands, the performance of this serializer is not great
      nor has it been throughly tested.  It is, however, about 4x faster 
      than the YAML version.  It could be optimized further.

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

## FIXME: serializer needs a close() call
## FIXME: investigate locking

import distutils.sysconfig
import os
import sys
import glob
import traceback
from rhpl.translate import _, N_, textdomain, utf8
import os
import shelve
import time
#import gdbm # FIXME: check if available in EL4?
import bsddb

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils

DATABASES = {}

def open_db(collection_type):
    if DATABASES.has_key(collection_type):
        return DATABASES[collection_type]
    ending = collection_type
    if not ending.endswith("s"):
        ending = ending + "s"
    while 1:
        try:
            filename = "/var/lib/cobbler/%s.shelve" % ending

	    internal_db = bsddb.btopen( filename, 'c', 0644 )


            #internal_db = gdbm.open(filename, 'c', 0644)
            database = shelve.BsdDbShelf(internal_db)
            DATABASES[collection_type] = database
            return database
        except:
            traceback.print_exc()
            print "- can't access %s right now, waiting..." % filename
            time.sleep(1)
	    continue

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return True 

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    Will create intermediate paths if it can.  Returns True on Success,
    False on permission errors.
    """

    # FIXME: this needs to understand deletes
    # FIXME: create partial serializer and don't use this
    fd = open_db(obj.collection_type())

    for entry in obj:
        fd[entry.name] = entry.to_datastruct()
    # fd.sync()
    return True

def serialize_item(obj, item):
    fd = open_db(obj.collection_type())
    fd[item.name] = item.to_datastruct()
    # fd.sync()
    return True

# NOTE: not heavily tested
def serialize_delete(obj, item):
    fd = open_db(obj.collection_type())
    if fd.has_key(item.name):
        print "DEBUG: deleting: %s" % item.name
        del fd[item.name]
    # fd.sync()
    return True

def deserialize_raw(collection_type):
    fd = open_db(collection_type)
    datastruct = []
    # FIXME: see if we can call items() directly
    for (key,value) in fd.iteritems():
        datastruct.append(value)
    # fd.close()
    return datastruct

def deserialize(obj,topological=False):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  Returns True assuming
    files could be read and contained decent YAML.  Otherwise returns
    False.
    """
    fd = open_db(obj.collection_type())

    datastruct = []
    for (key,value) in fd.iteritems():
       datastruct.append(value)

    # fd.close()

    if topological and type(datastruct) == list:
       # in order to build the graph links from the flat list, sort by the
       # depth of items in the graph.  If an object doesn't have a depth, sort it as
       # if the depth were 0.  It will be assigned a proper depth at serialization
       # time.  This is a bit cleaner implementation wise than a topological sort,
       # though that would make a shiny upgrade.
       datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    return True

def __depth_cmp(item1, item2):
    if not item1.has_key("depth"):
       return 1
    if not item2.has_key("depth"):
       return -1
    return cmp(item1["depth"],item2["depth"])

