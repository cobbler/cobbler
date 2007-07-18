# Virtualization installation functions.  
# Currently somewhat Xen/paravirt specific, will evolve later.
#
# Copyright 2006-2007 Red Hat, Inc.
# Michael DeHaan <mdehaan@redhat.com>
#
# Original version based on virtguest-install
# Jeremy Katz <katzj@redhat.com>
# Option handling added by Andrew Puch <apuch@redhat.com>
# Simplified for use as library by koan, Michael DeHaan <mdehaan@redhat.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os, sys, time, stat
import tempfile
import random
from optparse import OptionParser
import exceptions
import errno
import re
import virtinst

class VirtCreateException(exceptions.Exception):
    pass

def randomUUID():
    """
    Generate a random UUID.  Copied from xend/uuid.py
    """
    return [ random.randint(0, 255) for x in range(0, 16) ]


def uuidToString(u):
    """
    return uuid as a string
    """
    return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
                     "%02x" * 6]) % tuple(u)

def get_uuid(uuid):
    """
    return the passed-in uuid, or a random one if it's not set.
    """
    if uuid:
       return uuid
    return uuidToString(randomUUID())

def start_paravirt_install(name=None, ram=None, disk=None, mac=None,
                           uuid=None, kernel=None, initrd=None, 
                           extra=None, path=None,
                           vcpus=None, virt_graphics=False, special_disk=False):


    guest = virtinst.ParaVirtGuest()
    guest.set_boot((kernel,initrd))
    guest.set_extra_args(extra)
    guest.set_name(name)
    guest.set_memory(ram)
    if vcpus is None:
        vcpus = 1
    guest.set_vcpus(vcpus)
    if virt_graphics:
        guest.set_graphics("vnc")
    else:
        guest.set_graphics(False)
    if uuid is not None:
        guest.set_uuid(uuid)

    disk_path = path
    disk_obj = virtinst.XenDisk(disk_path, size=disk)

    try:
        nic_obj = virtinst.XenNetworkInterface(macaddr=mac, type="user")
    except:
        # try to be backward compatible
        nic_obj = virtinst.XenNetworkInterface(macaddr=mac)

    guest.disks.append(disk_obj)
    guest.nics.append(nic_obj)

    guest.start_install()
    
    return "reconnect with xm console %s" % name 
     
