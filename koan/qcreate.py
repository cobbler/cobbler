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
                           extra=None, nameoverride=None, path=None,
                           vcpus=None):

    usename = name
    if nameoverride is not None:
       usename = nameoverride


    if os.path.isdir(path):
       path = os.path.join(path, usename)
     
    if os.path.exists(path):
       # FIXME: EVIL!
       os.remove(path)
       # return "ERROR: path (%s) exists" % path

    cmd = "qemu-img create -f qcow2 %s %sG" % (path, disk)
    rc = os.system(cmd)

    if rc != 0:
       return "image creation failed"
    
    #cmd2 = "qemu-kvm -m %s -hda %s" % (ram,path)
    cmd2 = "qemu -m %s -hda %s" % (ram,path)
    cmd2 = cmd2  + " -kernel %s" % (kernel)
    cmd2 = cmd2  + " -initrd %s" % (initrd)
    #cmd2 = cmd2 + " -append \"%s\"  -net nic -net tap" % (extra) 
    cmd2 = cmd2  + " -append \"%s\"  " % (extra) 

    print cmd2

    rc2 = os.system(cmd2)
    if rc2 != 0:
       return "installation failed"

    return "installation complete"

