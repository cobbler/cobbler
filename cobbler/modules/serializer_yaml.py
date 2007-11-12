"""
Serializer code for cobbler

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import os
import sys
import glob

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from rhpl.translate import _, N_, textdomain, utf8
import utils
import yaml   # Howell-Clark version
import cexceptions
import os

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "serializer"

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    Will create intermediate paths if it can.  Returns True on Success,
    False on permission errors.
    """
    filename = get_filename(obj.collection_type())
    try:
        fd = open(filename,"w+")
    except IOError, ioe:
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
           try:
               os.makedirs(dirname)
               # evidentally this doesn't throw exceptions.
           except OSError, ose:
               pass
        try:
           fd = open(filename,"w+")
        except IOError, ioe3:
           raise cexceptions.CX(_("Need permissions to write to %s") % filename)
           return False
    datastruct = obj.to_datastruct()
    encoded = yaml.dump(datastruct)
    fd.write(encoded)
    fd.close()
    return True

def get_filename(collection_type):
    # FIXME: use this everywhere
    ending = collection_type
    if not ending.endswith("s"):
        ending = ending + "s"
    return "/var/lib/cobbler/%s" % ending

def deserialize_raw(collection_type):
    filename = get_filename(collection_type)
    try:
        fd = open(filename,"r")
    except IOError, ioe:
        return [{}]
    data = fd.read()
    datastruct = yaml.load(data).next()  # first record
    fd.close()
    return datastruct 

def deserialize(obj,topological=False):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  Returns True assuming
    files could be read and contained decent YAML.  Otherwise returns
    False.
    """
    filename = get_filename(obj.collection_type())
    try:
        fd = open(filename,"r")
    except IOError, ioe:
        # if it doesn't exist, that's cool -- it's not a bug until we try
        # to write the file and can't create it.
        if not os.path.exists(filename):
            return True
        else:
            raise cexceptions.CX(_("Need permissions to read %s") % obj.filename())
    data = fd.read()
    datastruct = yaml.load(data).next()  # first record
    fd.close()

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

