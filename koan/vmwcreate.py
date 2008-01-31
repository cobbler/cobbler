# Virtualization installation functions.  
#
# Copyright 2007-2008 Red Hat, Inc.
# FIXME: your name here
# Michael DeHaan <mdehaan@redhat.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# module for creating fullvirt guests via KVM/kqemu/qemu
# requires python-virtinst-0.200.

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

def random_mac():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-16-3E, allocated to
    Xensource, Inc.  Last 3 fields are random.
    return: MAC address string
 
    FIXME: if VMware has their own range, adapt to that range
    """
    mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def start_install(name=None, ram=None, disks=None, mac=None,
                  uuid=None,  
                  extra=None,
                  vcpus=None, 
                  profile_data=None, bridge=None, arch=None, no_gfx=False, fullvirt=True):

    print "- starting vmware-based install, via PXE"
    # FIXME: TODO
    return "installation finished"

