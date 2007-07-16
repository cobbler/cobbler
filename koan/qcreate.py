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

class VirtCreateException(exceptions.Exception):
    pass

def start_install(name=None, ram=None, disk=None, mac=None,
                  uuid=None, kernel=None, initrd=None, 
                  extra=None, path=None,
                  vcpus=None, virt_graphics=None):

    if os.path.isdir(path):
       path = os.path.join(path, name)
     
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
    if virt_graphics:
        print "- access your installation with vncviewer :0"
    print "- restart with qemu-kvm -hda %s -M %s" % (path, ram)

    cmd2 = "qemu-kvm -m %s -hda %s" % (ram,path)
    cmd2 = cmd2  + " -kernel %s" % (kernel)
    cmd2 = cmd2  + " -initrd %s" % (initrd)
    cmd2 = cmd2  + " -net nic,macaddr=%s -net user" % (mac)
    cmd2 = cmd2  + " -daemonize -append \"%s\"" % (extra)

    if virt_graphics:
        # FIXME: detect vnc collisions?
        cmd2 = cmd2  + " -vnc :0 -serial vc -monitor vc"
    else:
        cmd2 = cmd2  + " -nographic"

    print cmd2

    rc2 = os.system(cmd2)
    if rc2 != 0:
       return "installation failed"

    return "installation complete"

