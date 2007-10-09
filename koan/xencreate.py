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


def start_paravirt_install(name=None, ram=None, disks=None,
                           uuid=None,  
                           extra=None, 
                           vcpus=None, virt_graphics=False, 
                           profile_data=None, bridge=None, arch=None):


    guest = virtinst.ParaVirtGuest()
    guest.set_boot((profile_data["kernel_local"], profile_data["initrd_local"]))
    guest.extraargs = extra
    guest.set_name(name)
    guest.set_memory(ram)
    if vcpus is None:
        vcpus = 1
    guest.set_vcpus(vcpus)
    if virt_graphics:
        guest.set_graphics("vnc")
    else:
        guest.set_graphics(False)
    if uuid is not None:
        guest.set_uuid(uuid)

    for d in disks:
        guest.disks.append(virtinst.XenDisk(d[0], size=d[1]))

    counter = 0

    if profile_data.has_key("interfaces"):

        for (name,intf) in profile_data["interfaces"].iteritems():

            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()
    
            bridge2 = intf["virt_bridge"]
            if bridge2 == "":
                bridge2 = bridge

            nic_obj = virtinst.XenNetworkInterface(macaddr=mac, bridge=bridge2)
            guest.nics.append(nic_obj)
            counter = counter + 1
   
    else:
            # for --profile you just get one NIC, go define a system if you want more.
            # FIXME: can mac still be sent on command line in this case?

            nic_obj = virtinst.XenNetworkInterface(macaddr=random_mac(), bridge=bridge)
            guest.nics.append(nic_obj)
            
        


    guest.start_install()
    
    return "use virt-manager or reconnect with virsh console %s" % name 
     
