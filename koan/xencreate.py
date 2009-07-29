"""
Virtualization installation functions.  
Currently somewhat Xen/paravirt specific, will evolve later.

Copyright 2006-2008 Red Hat, Inc.
Michael DeHaan <mdehaan@redhat.com>

Original version based on virtguest-install
Jeremy Katz <katzj@redhat.com>
Option handling added by Andrew Puch <apuch@redhat.com>
Simplified for use as library by koan, Michael DeHaan <mdehaan@redhat.com>

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
"""

import os, sys, time, stat
import tempfile
import random
import exceptions
import errno
import re
import virtinst
import app as koan

try:
    import virtinst.DistroManager as DistroManager
except:
    # older virtinst, this is probably ok
    # but we know we can't do Xen fullvirt installs
    pass
import traceback

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
                  uuid=None,  
                  extra=None, 
                  vcpus=None,  
                  profile_data=None, 
                  arch=None, 
                  no_gfx=False, 
                  fullvirt=False, 
                  bridge=None, 
                  virt_type=None,
                  virt_auto_boot=False):

    if profile_data.has_key("file"):
        raise koan.InfoException("Xen does not work with --image yet")

    if fullvirt:
        # FIXME: add error handling here to explain when it's not supported
        guest = virtinst.FullVirtGuest(installer=DistroManager.PXEInstaller())
    else:
        guest = virtinst.ParaVirtGuest()

    extra = extra.replace("&","&amp;")

    if not fullvirt:
        guest.set_boot((profile_data["kernel_local"], profile_data["initrd_local"]))
        # fullvirt OS's will get this from the PXE config (managed by Cobbler)
        guest.extraargs = extra
    else:
        print "- fullvirt mode"
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

    if not no_gfx:
        guest.set_graphics("vnc")
    else:
        guest.set_graphics(False)

    if uuid is not None:
        guest.set_uuid(uuid)

    for d in disks:
        if d[1] != 0 or d[0].startswith("/dev"):
            guest.disks.append(virtinst.XenDisk(d[0], size=d[1]))
        else:
            raise koan.InfoException("this virtualization type does not work without a disk image, set virt-size in Cobbler to non-zero")

    counter = 0

    if profile_data.has_key("interfaces"):

        interfaces = profile_data["interfaces"].keys()
        interfaces.sort()
        counter = -1
        vlanpattern = re.compile("[a-zA-Z0-9]+\.[0-9]+")

        for iname in interfaces:
            counter = counter + 1
            intf = profile_data["interfaces"][iname]

            if intf["bonding"] == "master" or vlanpattern.match(iname) or iname.find(":") != -1: 
                continue

            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()

            if not bridge:
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


            nic_obj = virtinst.XenNetworkInterface(macaddr=mac, bridge=intf_bridge)
            guest.nics.append(nic_obj)
            counter = counter + 1
   
    else:
            # for --profile you just get one NIC, go define a system if you want more.
            # FIXME: can mac still be sent on command line in this case?

            if bridge is None:
                profile_bridge = profile_data["virt_bridge"]
            else:
                profile_bridge = bridge

            if profile_bridge == "":
                raise koan.InfoException("virt-bridge setting is not defined in cobbler")

            nic_obj = virtinst.XenNetworkInterface(macaddr=random_mac(), bridge=profile_bridge)
            guest.nics.append(nic_obj)
            
        


    guest.start_install()
    
    return "use virt-manager or reconnect with virsh console %s" % name 
     
