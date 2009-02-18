"""
Virtualization installation functions for image based deployment

Copyright 2008 Red Hat, Inc.
Bryan Kearney <bkearney@redhat.com>

Original version based on virt-image
David Lutterkort <dlutter@redhat.com>

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
import shutil
import random
import exceptions
import errno
import virtinst
try:
   from virtinst import ImageParser, Guest, CapabilitiesParser, VirtualNetworkInterface
except:
   # if this fails, this is ok, the user just won't be able to use image objects...
   # keeping this dynamic allows this to work on older EL.
   pass
import libvirt

import app as koan

#FIXME this was copied
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


def transform_arch(arch):
    if arch == "i386":
        return "i686"
    else:
        return arch
        
def copy_image(original_file, new_location):
    shutil.copyfile(original_file, new_location)
    return new_location
    
    
def process_disk(image, boot, file, location, target):
    image_location = copy_image(file, location)
    # Create the disk
    disk = ImageParser.Disk()
    disk.format = "raw"
    disk.file = image_location
    disk.use = "user"
    disk.id = image_location
    image.storage[disk.id] = disk
    
    #Create the drive
    drive = ImageParser.Drive()
    drive.id = image_location
    drive.target = target 
    drive.disk = disk
    boot.disks.append(drive)
    #dev api
    #boot.drives.append(drive)  
    
    
def process_networks(domain, guest, profile_data, bridge):
    # Create a bridge or default network for every requested nic. If there are more
    # bridges then nics discard the last one.
    domain.interface = int(profile_data["network_count"])
    bridges = []
    #use the provided bridge first
    guest_bridge = bridge
    if guest_bridge is None:
        guest_bridge = profile_data["virt_bridge"]
        
    # Look for commas
    if (guest_bridge is not None) and (len(guest_bridge.strip()) > 0):
        if guest_bridge.find(",") == -1:
            bridges.append(guest_bridge)
        else:
            bridges == guest_bridge.split(",")
    
    for cnt in range(0,domain.interface):
        if cnt < len(bridges):
            nic = VirtualNetworkInterface(random_mac(), type="bridge", bridge = bridges[cnt])
            #dev api
            #nic = VirtualNetworkInterface(random_mac(), type="bridge", bridge = bridge, conn=guest.conn)                
        else: 
            default_network = virtinst.util.default_network()
            #dev api
            #default_network = virtinst.util.default_network(guest.conn)
            nic = VirtualNetworkInterface(random_mac(), type=default_network[0], network=default_network[1])
        guest.nics.append(nic)

def start_install(name=None, ram=None, disks=None,
                           uuid=None,  
                           extra=None, 
                           vcpus=None,  
                           profile_data=None, arch=None, no_gfx=False, fullvirt=False, bridge=None, virt_type=None):                 
                           
    #FIXME how to do a non-default connection
    #Can we drive off of virt-type?
    connection = None
    
    if (virt_type is None ) or (virt_type == "auto"):
        connection = virtinst.util.default_connection()
    elif virt_type.lower()[0:3] == "xen":
        connection = "xen"
    else:
        connection = "qemu:///system"
        
    connection = libvirt.open(connection)
    capabilities = virtinst.CapabilitiesParser.parse(connection.getCapabilities())   
    image_arch = transform_arch(arch)       

    image = ImageParser.Image() 
    #dev api
    #image = ImageParser.Image(filename="") #FIXME, ImageParser should take in None
    image.name = name

    domain = ImageParser.Domain()
    domain.vcpu = vcpus
    domain.memory = ram
    image.domain = domain
    
    boot = ImageParser.Boot()
    boot.type = "hvm" #FIXME HARDCODED
    boot.loader = "hd" #FIXME HARDCODED
    boot.arch = image_arch
    domain.boots.append(boot)
    
    #FIXME Several issues. Single Disk, type is hardcoded
    #And there is no way to provision with access to "file"
    process_disk(image, boot, profile_data["file"], disks[0][0], "hda")
    
    #FIXME boot_index??
    installer = virtinst.ImageInstaller(boot_index = 0, image=image, capabilities=capabilities)                               
    guest = virtinst.FullVirtGuest(connection = connection, installer=installer, arch=image_arch)

    extra = extra.replace("&","&amp;")

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
                   
    process_networks(domain, guest, profile_data, bridge)                   
    
    guest.start_install()
    
    return "use virt-manager or reconnect with virsh console %s" % name 
     
