"""
Virtualization installation functions.  

Copyright 2007-2008 Red Hat, Inc.
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA

module for creating fullvirt guests via KVM/kqemu/qemu
requires python-virtinst-0.200.
"""

import os, sys, time, stat
import tempfile
import random
from optparse import OptionParser
import exceptions
import errno
import re
import tempfile
import shutil
import virtinst
import app as koan
import sub_process as subprocess
import utils

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


def start_install(name=None, 
                  ram=None, 
                  disks=None, 
                  mac=None,
                  uuid=None,  
                  extra=None,
                  vcpus=None, 
                  profile_data=None, 
                  arch=None, 
                  no_gfx=False, 
                  fullvirt=True, 
                  bridge=None, 
                  virt_type=None,
                  virt_auto_boot=False):

    vtype = "qemu"
    if virtinst.util.is_kvm_capable():
       vtype = "kvm"
       arch = None # let virtinst.FullVirtGuest() default to the host arch
    elif virtinst.util.is_kqemu_capable():
       vtype = "kqemu"
    print "- using qemu hypervisor, type=%s" % vtype

    if arch is not None and arch.lower() in ["x86","i386"]:
        arch = "i686"

    guest = virtinst.FullVirtGuest(hypervisorURI="qemu:///system",type=vtype, arch=arch)

    if not profile_data.has_key("file"):
        # images don't need to source this 
        if not profile_data.has_key("install_tree"):
            raise koan.InfoException("Cannot find install source in kickstart file, aborting.")
   
 
        if not profile_data["install_tree"].endswith("/"):
            profile_data["install_tree"] = profile_data["install_tree"] + "/"

        # virt manager doesn't like nfs:// and just wants nfs:
        # (which cobbler should fix anyway)
        profile_data["install_tree"] = profile_data["install_tree"].replace("nfs://","nfs:")

    if profile_data.has_key("file"):
        # this is an image based installation
        input_path = profile_data["file"]
        print "- using image location %s" % input_path
        if input_path.find(":") == -1:
            # this is not an NFS path
            guest.cdrom = input_path
        else:
            (tempdir, filename) = utils.nfsmount(input_path)
            guest.cdrom = os.path.join(tempdir, filename)     

        kickstart = profile_data.get("kickstart","")
        if kickstart != "":
            # we have a (windows?) answer file we have to provide
            # to the ISO.
            print "I want to make a floppy for %s" % kickstart
            floppy_path = utils.make_floppy(kickstart)
            guest.disks.append(virtinst.VirtualDisk(device=virtinst.VirtualDisk.DEVICE_FLOPPY, path=floppy_path))
        

    else:
        guest.location = profile_data["install_tree"]
   
    extra = extra.replace("&","&amp;") 
    guest.extraargs = extra

    if profile_data.has_key("breed"):
        breed = profile_data["breed"]
        if breed != "other" and breed != "":
            if breed in [ "debian", "suse", "redhat" ]:
                guest.set_os_type("linux")
            elif breed in [ "windows" ]:
                guest.set_os_type("windows")
            else:
                guest.set_os_type("unix")
            if profile_data.has_key("os_version"):
                # FIXME: when os_version is not defined and it's linux, do we use generic24/generic26 ?
                version = profile_data["os_version"]
                if version != "other" and version != "":
                    try:
                        guest.set_os_variant(version)
                    except:
                        print "- virtinst library does not understand variant %s, treating as generic" % version
                        pass

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
        if d[1] != 0 or d[0].startswith("/dev"):
            guest.disks.append(virtinst.VirtualDisk(d[0], size=d[1]))
        else:
            raise koan.InfoException("this virtualization type does not work without a disk image, set virt-size in Cobbler to non-zero")

    if profile_data.has_key("interfaces"):

        counter = 0
        interfaces = profile_data["interfaces"].keys()
        interfaces.sort()
        vlanpattern = re.compile("[a-zA-Z0-9]+\.[0-9]+")
        for iname in interfaces:
            intf = profile_data["interfaces"][iname]

            if intf["bonding"] == "master" or vlanpattern.match(iname) or iname.find(":") != -1:
                continue

            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()

            if bridge is None:
                profile_bridge = profile_data["virt_bridge"]

                intf_bridge = intf["virt_bridge"]
                if intf_bridge == "":
                    if profile_bridge == "":
                        raise koan.InfoException("virt-bridge setting is not defined in cobbler")
                    intf_bridge = profile_bridge
            else:
                if bridge.find(",") == -1:
                    intf_bridge = bridge
                else:
                    bridges = bridge.split(",")  
                    intf_bridge = bridges[counter]
            nic_obj = virtinst.VirtualNetworkInterface(macaddr=mac, bridge=intf_bridge)
            guest.nics.append(nic_obj)
            counter = counter + 1

    else:

            if bridge is not None:
                profile_bridge = bridge
            else:
                profile_bridge = profile_data["virt_bridge"]

            if profile_bridge == "":
                raise koan.InfoException("virt-bridge setting is not defined in cobbler")

            nic_obj = virtinst.VirtualNetworkInterface(macaddr=random_mac(), bridge=profile_bridge)
            guest.nics.append(nic_obj)

    guest.start_install()

    return "use virt-manager and connect to qemu to manage guest: %s" % name

