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
                  vcpus=None, 
                  profile_data=None, bridge=None, arch=None, no_gfx=False, fullvirt=True):

    vtype = "qemu"
    if virtinst.util.is_kvm_capable():
       vtype = "kvm"
    elif virtinst.util.is_kqemu_capable():
       vtype = "kqemu"
    print "- using qemu hypervisor, type=%s" % vtype

    if arch is not None and arch.lower() == "x86":
        arch = "i686"

    guest = virtinst.FullVirtGuest(hypervisorURI="qemu:///system",type=vtype, arch=arch)
   
    if not profile_data.has_key("install_tree"):
        raise VirtCreateException("Cannot find install source in kickstart file, aborting.")
   
 
    if not profile_data["install_tree"].endswith("/"):
       profile_data["install_tree"] = profile_data["install_tree"] + "/"

    # virt manager doesn't like nfs:// and just wants nfs:
    # (which cobbler should fix anyway)
    profile_data["install_tree"] = profile_data["install_tree"].replace("nfs://","nfs:")

    guest.location = profile_data["install_tree"]
   
     
    guest.extraargs = extra

    guest.set_name(name)
    guest.set_memory(ram)
    guest.set_vcpus(vcpus)
    # for KVM, we actually can't disable this, since it's the only
    # console it has other than SDL
    guest.set_graphics("vnc")

    if uuid is not None:
        guest.set_uuid(uuid)

    for d in disks:
        print "- adding disk: %s of size %s" % (d[0], d[1])
        if d[1] == 0:
            raise VirtCreateException("this virtualization type does not work without a disk image, set virt-size in Cobbler to non-zero")
        guest.disks.append(virtinst.VirtualDisk(d[0], size=d[1]))

    if profile_data.has_key("interfaces"):

        counter = 0
        interfaces = profile_data["interfaces"].keys()
        interfaces.sort()
        #for (iname,intf) in profile_data["interfaces"].iteritems():
        for iname in interfaces:
            intf = profile_data["interfaces"][iname]

            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()

            profile_bridge = profile_data["virt_bridge"]

            intf_bridge = intf["virt_bridge"]
            if intf_bridge == "":
                if profile_bridge == "":
                    raise VirtCreateException("virt-bridge setting is not defined in cobbler")
                intf_bridge = profile_bridge
                

            nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac, bridge=intf_bridge)
            guest.nics.append(nic_obj)
            counter = counter + 1

    else:

            profile_bridge = profile_data["virt_bridge"]
            if profile_bridge == "":
                raise VirtCreateException("virt-bridge setting is not defined in cobbler")

            nic_obj = virtinst.VirtualNetworkInterface(macaddr=random_mac(), bridge=profile_bridge)
            guest.nics.append(nic_obj)

    guest.start_install()

    return "use virt-manager and connect to qemu to manage guest: %s" % name

