#
# Virtualization installation functions.  
# Code originated from xenguest-install.
# Currently somewhat Xen specific, but it goes through libvirt,
# so this may change later.
#
# Copyright 2005-2006  Red Hat, Inc.
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
import virtinst   # NEW!

class VirtCreateException(exceptions.Exception):
    pass

def randomMAC():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-16-3E, allocated to
    Xensource, Inc.  Last 3 fields are random.
    return: MAC address string
    """
    mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

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

def get_mac(mac):
    """
    return the passed-in MAC, or a random one if it's not set.
    """
    if mac:
       return mac
    return randomMAC()


def start_paravirt_install(name=None, ram=None, disk=None, mac=None,
                           uuid=None, kernel=None, initrd=None, extra=None):


    if mac == None:
       mac = randomMAC()
    macname = mac.replace(":","_")

    guest = virtinst.ParaVirtGuest()
    guest.set_boot((kernel,initrd))
    guest.set_extra_args(extra)
    guest.set_name(macname)   
    guest.set_memory(ram)
    guest.set_vcpus(1)            # FIXME!
    guest.set_graphics(False)
    if uuid is not None:
        guest.set_uuid(uuid)

    disk_path = "/var/lib/xen/images/%s" % macname
    disk_obj = virtinst.XenDisk(disk_path, size=disk)

    nic_obj = virtinst.XenNetworkInterface(macaddr=mac)

    guest.disks.append(disk_obj)
    guest.nics.append(nic_obj)

    guest.start_install()
    
    return "reconnect with xm console %s" % macname 
     
