# Virtualization installation functions.  
#
# Copyright 2007 Red Hat, Inc.
# Michael DeHaan <mdehaan@redhat.com>
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


class VirtCreateException(exceptions.Exception):
    pass

def start_install(name=None, ram=None, disk=None, mac=None,
                  uuid=None, kernel=None, initrd=None, 
                  extra=None, nameoverride=None, path=None,
                  vcpus=None, virt_graphics=None):

    usename = name
    if nameoverride is not None:
       usename = nameoverride

    if mac is None:
       mac = randomMAC()
    print "using MAC: %s" % mac


    if os.path.isdir(path):
       path = os.path.join(path, usename)
     
    if os.path.exists(path):
       msg = "ERROR: disk path (%s) exists. " % path
       msg = msg + "You can delete it, try a "
       msg = msg + "different --virt-path, or specify a different --virt-name."
       msg = msg + "However, koan will not overwrite an existing file."
       return msg

    cmd = "qemu-img create -f qcow2 %s %sG" % (path, disk)
    rc = os.system(cmd)

    if rc != 0:
       return "image creation failed"

    print "- starting background install to %s" % path
    if not virt_graphics:
        print "- access your installation with vncviewer :0"
    print "- restart with qemu-kvm -hda %s -M %s" % (path, ram)

    cmd2 = "qemu -m %s -hda %s" % (ram,path)
    cmd2 = cmd2  + " -kernel %s" % (kernel)
    cmd2 = cmd2  + " -initrd %s" % (initrd)
    cmd2 = cmd2  + " -net nic,macaddr=%s -net user" % (mac)
    cmd2 = cmd2  + " -daemonize -append \"%s\"" % (extra)

    if virt_graphics:
        # FIXME: detect vnc collisions?
        cmd2 = cmd2  + " -vnc :0 -serial vc -monitor vc"

    print cmd2

    rc2 = os.system(cmd2)
    if rc2 != 0:
       return "installation failed"

    return "installation complete"

