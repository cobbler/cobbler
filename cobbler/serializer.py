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

import yaml   # Howell-Clark version
import errno
import os

from cexceptions import *
import utils

from rhpl.translate import _, N_, textdomain, utf8

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    Will create intermediate paths if it can.  Returns True on Success,
    False on permission errors.
    """
    # FIXME: DEBUG
    filename = obj.filename()
    try:
        fd = open(filename,"w+")
    except IOError, ioe:
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
           try:
               os.makedirs(dirname)
               # evidentally this doesn't throw exceptions.
           except OSError, ose:
               raise CX(_("Need permissions to write to %s") % os.path.dirname(dirname))
        try:
           fd = open(filename,"w+")
        except IOError, ioe3:
           raise CX(_("Need permissions to write to %s") % filename)
           return False
    datastruct = obj.to_datastruct()
    encoded = yaml.dump(datastruct)
    fd.write(encoded)
    fd.close()
    return True

def deserialize(obj):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  Returns True assuming
    files could be read and contained decent YAML.  Otherwise returns
    False.
    """
    filename = obj.filename()
    try:
        fd = open(filename,"r")
    except IOError, ioe:
        # if it doesn't exist, that's cool -- it's not a bug until we try
        # to write the file and can't create it.
        if not os.path.exists(filename):
            return True
        else:
            raise CX(_("Need permissions to read %s") % obj.filename())
    data = fd.read()
    datastruct = yaml.load(data).next()  # first record
    fd.close()
    obj.from_datastruct(datastruct)
    return True


