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

import os
import re
import shlex

import app as koan
import utils

def _sanitize_disks(disks):
    ret = []
    for d in disks:
        driver_type = None
        if len(d) > 2:
            driver_type = d[2]

        if d[1] != 0 or d[0].startswith("/dev"):
            ret.append((d[0], d[1], driver_type))
        else:
            raise koan.InfoException("this virtualization type does not work without a disk image, set virt-size in Cobbler to non-zero")

    return ret

def _sanitize_nics(nics, bridge, profile_bridge):
    ret = []

    if not nics:
        return ret

    interfaces = nics.keys()
    interfaces.sort()
    counter = -1
    vlanpattern = re.compile("[a-zA-Z0-9]+\.[0-9]+")

    for iname in interfaces:
        counter = counter + 1
        intf = nics[iname]

        if (intf["interface_type"] in ("master","bond","bridge") or
            vlanpattern.match(iname) or iname.find(":") != -1):
            continue

        mac = intf["mac_address"]

        if not bridge:
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

        ret.append((intf_bridge, mac))

    return ret


def build_commandline(uri,
                      name=None,
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
                      virt_auto_boot=False,
                      qemu_driver_type=None,
                      qemu_net_type=None):

    is_xen = uri.startswith("xen")
    is_qemu = uri.startswith("qemu")
    if is_qemu:
        fullvirt = True

    floppy = None
    cdrom = None
    location = None

    if profile_data.has_key("file"):
        if is_xen:
            raise koan.InfoException("Xen does not work with --image yet")

        # this is an image based installation
        input_path = profile_data["file"]
        print "- using image location %s" % input_path
        if input_path.find(":") == -1:
            # this is not an NFS path
            cdrom = input_path
        else:
            (tempdir, filename) = utils.nfsmount(input_path)
            cdrom = os.path.join(tempdir, filename)

        kickstart = profile_data.get("kickstart","")
        if kickstart != "":
            # we have a (windows?) answer file we have to provide
            # to the ISO.
            print "I want to make a floppy for %s" % kickstart
            floppy = utils.make_floppy(kickstart)
    elif is_qemu:
        # images don't need to source this
        if not profile_data.has_key("install_tree"):
            raise koan.InfoException("Cannot find install source in kickstart file, aborting.")

        if not profile_data["install_tree"].endswith("/"):
            profile_data["install_tree"] = profile_data["install_tree"] + "/"

        location = profile_data["install_tree"]


    disks = _sanitize_disks(disks)
    nics = _sanitize_nics(profile_data.get("interfaces"),
                          bridge,
                          profile_data.get("virt_bridge"))
    if not nics:
        # for --profile you get one NIC, go define a system if you want more.
        # FIXME: can mac still be sent on command line in this case?

        if bridge is None:
            bridge = profile_data["virt_bridge"]

        if bridge == "":
            raise koan.InfoException("virt-bridge setting is not defined in cobbler")
        nics = [(bridge, None)]


    kernel = profile_data.get("kernel_local")
    initrd = profile_data.get("initrd_local")
    breed = profile_data.get("breed")
    os_version = profile_data.get("os_version")
    if os_version and breed == "ubuntu":
        os_version = "ubuntu%s" % os_version

    net_model = None
    disk_bus = None
    if is_qemu:
        net_model = qemu_net_type
        disk_bus = qemu_driver_type

    cmd = "virt-install --connect %s " % uri

    cmd += "--name %s " % name
    cmd += "--ram %s " % ram
    cmd += "--vcpus %s " % vcpus

    if uuid:
        cmd += "--uuid %s " % uuid

    if virt_auto_boot:
        cmd += "--autostart "

    if no_gfx:
        cmd += "--nographics "
    else:
        cmd += "--vnc "

    if is_qemu and virt_type:
        cmd += "--virt-type %s " % virt_type

    if fullvirt or is_qemu:
        cmd += "--hvm "
        if is_xen:
            cmd += "--pxe "

        elif cdrom:
            cmd += "--cdrom %s " % cdrom
        elif location:
            cmd += "--location %s " % location

        if arch:
            cmd += "--arch %s " % arch
    else:
        cmd += "--paravirt "
        cmd += ("--boot kernel=%s,initrd=%s,kernel_args=\"%s\" " %
                (kernel, initrd, extra))

    if breed and breed != "other":
        if os_version and os_version != "other":
            cmd += "--os-variant %s " % os_version
        else:
            distro = "unix"
            if breed in [ "debian", "suse", "redhat" ]:
                distro = "linux"
            elif breed in [ "windows" ]:
                distro = "windows"

            cmd += "--os-type %s " % distro

    for path, size, driver_type in disks:
        print ("- adding disk: %s of size %s (driver type=%s)" %
               (path, size, driver_type))
        cmd += "--disk path=%s" % (path)
        if str(size) != "0":
            cmd += ",size=%s" % size
        if disk_bus:
            cmd += ",bus=%s" % disk_bus
        if driver_type:
            cmd += ",driver_type=%s" % driver_type
        cmd += " "

    if floppy:
        cmd += "--disk path=%s,device=floppy " % floppy

    for bridge, mac in nics:
        cmd += "--network bridge=%s" % bridge
        if mac:
            cmd += ",mac=%s" % mac
        if net_model:
            cmd += ",model=%s" % net_model
        cmd += " "

    cmd += "--wait 0 "
    cmd += "--noautoconsole "

    return shlex.split(cmd.strip())
