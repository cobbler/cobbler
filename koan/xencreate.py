# Virtualization installation functions.  
# Currently somewhat Xen/paravirt specific, will evolve later.
#
# Copyright 2006-2007 Red Hat, Inc.
# Michael DeHaan <mdehaan@redhat.com>
#
# Original version based on virtguest-install
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
import exceptions
import errno
import re
import virtinst
try:
    import virtinst.DistroManager as DistroManager
except:
    # older virtinst, this is probably ok
    # but we know we can't do Xen fullvirt installs
    pass
import traceback

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


def start_install(name=None, ram=None, disks=None,
                           uuid=None,  
                           extra=None, 
                           vcpus=None,  
                           profile_data=None, arch=None, no_gfx=False, fullvirt=False):


    if fullvirt:
        # FIXME: add error handling here to explain when it's not supported
        guest = virtinst.FullVirtGuest(installer=DistroManager.PXEInstaller())
    else:
        guest = virtinst.ParaVirtGuest()

    if not fullvirt:
        guest.set_boot((profile_data["kernel_local"], profile_data["initrd_local"]))
        # fullvirt OS's will get this from the PXE config (managed by Cobbler)
        guest.extraargs = extra

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
        if d[1] != 0:
            guest.disks.append(virtinst.XenDisk(d[0], size=d[1]))

    counter = 0

    if profile_data.has_key("interfaces"):

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
    

            nic_obj = virtinst.XenNetworkInterface(macaddr=mac, bridge=intf_bridge)
            guest.nics.append(nic_obj)
            counter = counter + 1
   
    else:
            # for --profile you just get one NIC, go define a system if you want more.
            # FIXME: can mac still be sent on command line in this case?

            profile_bridge = profile_data["virt_bridge"]
            if profile_bridge == "":
                raise VirtCreateException("virt-bridge setting is not defined in cobbler")

            nic_obj = virtinst.XenNetworkInterface(macaddr=random_mac(), bridge=profile_bridge)
            guest.nics.append(nic_obj)
            
        


    guest.start_install()
    
    return "use virt-manager or reconnect with virsh console %s" % name 
     
