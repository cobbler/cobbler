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

def start_install(name=None, ram=None, disk=None, mac=None,
                  uuid=None,  
                  extra=None, path=None,
                  vcpus=None, virt_graphics=None, 
                  special_disk=False, profile_data=None, bridge=None, arch=None):

    type = "qemu"
    if virtinst.util.is_kvm_capable():
       type = "kvm"
    elif virtinst.util.is_kqemu_capable():
       type = "kqemu"
    print "type=%s" % type

    guest = virtinst.FullVirtGuest(hypervisorURI="qemu:///system",type=type, arch=arch)
    
    if not profile_data["install_tree"].endswith("/"):
       profile_data["install_tree"] = profile_data["install_tree"] + "/"

    # virt manager doesn't like nfs:// and just wants nfs:
    # (which cobbler should fix anyway)
    profile_data["install_tree"] = profile_data["install_tree"].replace("nfs://","nfs:")

    guest.location = profile_data["install_tree"]
   
     
    guest.extraargs = extra

    guest.set_name(name)
    guest.set_memory(ram)
    if vcpus is None:
        vcpus = 1
    guest.set_vcpus(vcpus)
    
    
    # -- FIXME: workaround for bugzilla 249072 
    #if virt_graphics:
    #    guest.set_graphics("vnc")
    #else:
    #    guest.set_graphics(False)
    guest.set_graphics("vnc")

    if uuid is not None:
        guest.set_uuid(uuid)

    disk_path = path
    disk_obj = virtinst.VirtualDisk(disk_path, size=disk)

    try:
        # undocumented testing feature:
        # if we want another networking type we can specify --virt-bridge=OFF
        if bridge != "OFF":
            nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac, type="bridge", bridge=bridge)
        else:        
            nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac, type="user")

    except:
        # try to be backward compatible
        print "- trying old style network setup"
        nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac)

    guest.disks.append(disk_obj)
    guest.nics.append(nic_obj)

    guest.start_install()

    return "use virt-manager and connect to qemu to manage guest: %s" % name

