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
"""


import os, sys, time, stat
import tempfile
import random
from optparse import OptionParser
import exceptions
import errno
import re
import virtinst

IMAGE_DIR = "/var/lib/vmware/images"
VMX_DIR = "/var/lib/vmware/vmx"

# FIXME: what to put for guestOS
# FIXME: are other settings ok?
TEMPLATE = """
#!/usr/bin/vmware
config.version = "8"
virtualHW.version = "4"
numvcpus = "2"
scsi0.present = "TRUE"
scsi0.virtualDev = "lsilogic"
scsi0:0.present = "TRUE"
scsi0:0.writeThrough = "TRUE"
ide1:0.present = "TRUE"
ide1:0.deviceType = "cdrom-image"
Ethernet0.present = "TRUE"
Ethernet0.AddressType = "static"
Ethernet0.Address = "%(MAC_ADDRESS)s"
Ethernet0.virtualDev = "e1000"
guestOS = "linux"
priority.grabbed = "normal"
priority.ungrabbed = "normal"
powerType.powerOff = "hard"
powerType.powerOn = "hard"
powerType.suspend = "hard"
powerType.reset = "hard"
floppy0.present = "FALSE"
scsi0:0.filename = "%(VMDK_IMAGE)s"
displayName = "%(IMAGE_NAME)s"
memsize = "%(MEMORY)s"
"""
#ide1:0.filename = "%(PATH_TO_ISO)s"

class VirtCreateException(exceptions.Exception):
    pass

def random_mac():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-50-56, allocated to
    VMWare. Last 3 fields are random.
    return: MAC address string
    """
    mac = [ 0x00, 0x50, 0x56,
        random.randint(0x00, 0x3f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def make_disk(disksize,image):
    cmd = "vmware-vdiskmanager -c -a lsilogic -s %sGb -t 0 %s" % (disksize, image)
    print "- %s" % cmd
    rc = os.system(cmd)
    if rc != 0:
       raise VirtCreateException("command failed")

def make_vmx(path,vmdk_image,image_name,mac_address,memory):
    template_params =  {
        "VMDK_IMAGE"  : vmdk_image,
        "IMAGE_NAME"  : image_name,
        "MAC_ADDRESS" : mac_address.lower(),
        "MEMORY"      : memory
    }
    templated = TEMPLATE % template_params
    fd = open(path,"w+")
    fd.write(templated)
    fd.close()

def register_vmx(vmx_file):
    cmd = "vmware-cmd -s register %s" % vmx_file
    print "- %s" % cmd
    rc = os.system(cmd)
    if rc!=0:
       raise VirtCreateException("vmware registration failed")
    
def start_vm(vmx_file):
    os.chmod(vmx_file,0755)
    cmd = "vmware-cmd %s start" % vmx_file
    print "- %s" % cmd
    rc = os.system(cmd)
    if rc != 0:
       raise VirtCreateException("vm start failed")

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
                  virt_auto_boot=False,
                  qemu_driver_type=None,
                  qemu_net_type=None):

    if profile_data.has_key("file"):
        raise koan.InfoException("vmware does not work with --image yet")

    mac = None
    if not profile_data.has_key("interfaces"):
        print "- vmware installation requires a system, not a profile"
        return 1
    for iname in profile_data["interfaces"]:
        intf = profile_data["interfaces"][iname]
        mac = intf["mac_address"]
    if mac is None:
        print "- no MAC information available in this record, cannot install"
        return 1

    print "DEBUG: name=%s" % name
    print "DEBUG: ram=%s" % ram
    print "DEBUG: mac=%s" % mac
    print "DEBUG: disks=%s" % disks
    # starts vmware using PXE.  disk/mem info come from Cobbler
    # rest of the data comes from PXE which is also intended
    # to be managed by Cobbler.

    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    if not os.path.exists(VMX_DIR):
        os.makedirs(VMX_DIR)

    if len(disks) != 1:
       raise VirtCreateException("vmware support is limited to 1 virtual disk")

    diskname = disks[0][0]
    disksize = disks[0][1]

    image = "%s/%s" % (IMAGE_DIR, name)
    print "- saving virt disk image as %s" % image
    make_disk(disksize,image)
    vmx = "%s/%s" % (VMX_DIR, name)
    print "- saving vmx file as %s" % vmx
    make_vmx(vmx,image,name,mac,ram)
    register_vmx(vmx)
    start_vm(vmx)

