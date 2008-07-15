# Virtualization installation functions for wrapping virt-image
# and making it easier to clone centrally managed VMs repeatedly.
#
# Copyright 2007-2008 Red Hat, Inc.
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


def start_install(name=None, ram=None, disks=None, mac=None,
                  uuid=None,  
                  extra=None,
                  vcpus=None, 
                  profile_data=None, arch=None, no_gfx=False, fullvirt=True, bridge=None):

    print "DEBUG: remote data ... "
    keyz = profile_data.keys()
    keyz.sort()
    for x in keyz:
        print "  %s : %s " % (x, profile_data[x])

    virt_ram = profile_data.get("virt_ram","")
    virt_cpus = profile_data.get("virt_cpus","")
    virt_bridge = profile_data.get("virt_bridge","")
    virt_bridge = profile_data.get("virt_path","")
    img_filename = profile_data.get("file","")
    xml_filename = profile_data.get("xml_file","")   

    interfaces = []


    if img_filename == "":
        raise koan.InfoException("--file is required in cobbler to use this mode")

    if xml_filename == "":
        raise koan.InfoException("--xml-file is required in cobbler to use this mode")

    if img_filename.find("nfs://") != -1:
        (tempdir, filename) = utils.nfsmount(img_filename)
        img_filename = os.path.join(tempdir, filename)

    if xml_filename.find("nfs://") != -1:
        (tempdir2, filename2) = utils.nfsmount(xml_filename)
        xml_filename = os.path.join(tempdir2, filename2)

    # FIXME: here we have to surgery on the filename(s) in the XML file or otherwise
    # move the image file we downloaded to the path in the XML file.  Probably
    # the former.

    if not os.path.exists(img_filename):
        raise koan.InfoException("cannot access: %s" % img_filename)
    if not os.path.exists(xml_filename):
        raise koan.InfoException("cannot access: %s" % xml_filename)

    cmds = [ "/usr/bin/virt-image" ]

    if name is not None:
        cmds.append("--name=%s" % name)
    if virt_ram != "":
        cmds.append("--ram=%s" % virt_ram)
    if virt_cpus != "":
        cmds.append("--vcpus=%s" % virt_cpus)
    if no_gfx:
        cmds.append("--nographics")
    cmds.append("--image=%s" % xml_filename)

    # FIXME: we share a variant of this in all the virt modules, should be made functional
    # with a callback and moved to utils.py 
    if profile_data.has_key("interfaces"):
        counter = 0
        for iname in interfaces:
            intf = profile_data["interfaces"][iname]
            mac = intf["mac_address"]
            if mac == "":
                mac = random_mac()
                cmds.append("--mac=%s" % mac)
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

            cmds.append("--network=%s" % intf_bridge)

    print "- %s" % " ".join(cmds)
    rc = subprocess.call(cmds, shell=False)
    if rc != 0:
       raise koan.InfoException("command failed")

    return "virt-image exited successfully"



