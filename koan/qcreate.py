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

def random_mac():
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


def start_install(name=None, ram=None, disks=None, mac=None,
                  uuid=None,  
                  extra=None,
                  vcpus=None, virt_graphics=None, 
                  profile_data=None, bridge=None, arch=None):

    vtype = "qemu"
    if virtinst.util.is_kvm_capable():
       vtype = "kvm"
    elif virtinst.util.is_kqemu_capable():
       vtype = "kqemu"
    print "- using qemu hypervisor, type=%s" % vtype

    if arch is not None and arch.lower() == "x86":
        arch = "i686"

    guest = virtinst.FullVirtGuest(hypervisorURI="qemu:///system",type=vtype, arch=arch)
    
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

    for d in disks:
        print "- adding disk: %s of size %s" % (d[0], d[1])
        guest.disks.append(virtinst.VirtualDisk(d[0], size=d[1]))

    if profile_data.has_key("interfaces"):

        counter = 0
        for (name,intf) in profile_data["interfaces"].iteritems():

            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()

            bridge2 = intf["virt_bridge"]
            if bridge2 == "":
                bridge2 = bridge

            nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac, bridge=bridge2)
            guest.nics.append(nic_obj)
            counter = counter + 1

    else:
            # for --profile you just get one NIC, go define a system if you want more.

            # FIXME: ever want to allow --virt-mac on the command line?  Too much complexity?
            nic_obj = virtinst.VirtualNetworkInterface(macaddr=random_mac(), bridge=bridge)
            guest.nics.append(nic_obj)

    guest.start_install()

    return "use virt-manager and connect to qemu to manage guest: %s" % name

