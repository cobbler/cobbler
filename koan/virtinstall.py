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

from __future__ import print_function

import os
import re
import shlex
from . import utils
from cexceptions import InfoException

# The virtinst module will no longer be availabe to import in some
# distros. We need to get all the info we need from the virt-install
# command line tool. This should work on both old and new variants,
# as the virt-install command line tool has always been provided by
# python-virtinst (and now the new virt-install rpm).
# virt-install 1.0.1 responds to --version on stderr. WTF? Check both.
rc, response, stderr_response = utils.subprocess_get_response(
    shlex.split('virt-install --version'), True, True)
if rc == 0:
    if response:
        virtinst_version = response
    else:
        virtinst_version = stderr_response
else:
    virtinst_version = None

# This one's trickier. We need a list of supported os varients, but
# the man page explicitly says not to parse the result of this command.
# But we need it, and there's no other way to get it. I spoke with the
# virt-install maintainers and they said the point of that message
# is that you can't absolutely depend on the output not changing, but
# at the moment it's the only option for us. Long term plans are for
# virt-install to switch to libosinfo for OS metadata tracking, which
# provides a library and tools for querying valid OS values. Until
# that's available and pervasive the best we can do is to use the
# module if it's availabe and if not parse the command output.
supported_variants = set()
try:
    from virtinst import osdict
    for ostype in osdict.OS_TYPES.keys():
        for variant in osdict.OS_TYPES[ostype]["variants"].keys():
            supported_variants.add(variant)
except:
    try:
        rc, response = utils.subprocess_get_response(
            shlex.split('virt-install --os-variant list'))
        variants = response.split('\n')
        for variant in variants:
            supported_variants.add(variant.split()[0])
    except:
        pass  # No problem, we'll just use generic


def _sanitize_disks(disks):
    ret = []
    for d in disks:
        driver_type = None
        if len(d) > 2:
            driver_type = d[2]

        if d[1] != 0 or d[0].startswith("/dev"):
            ret.append((d[0], d[1], driver_type))
        else:
            raise InfoException(
                "this virtualization type does not work without a disk image, set virt-size in Cobbler to non-zero"
            )

    return ret


def _sanitize_nics(nics, bridge, profile_bridge, network_count):
    ret = []

    if network_count is not None and not nics:
        # Fill in some stub nics so we can take advantage of the loop logic
        nics = {}
        for i in range(int(network_count)):
            nics["foo%s" % i] = {
                "interface_type": "na",
                "mac_address": None,
                "virt_bridge": None,
            }

    if not nics:
        return ret

    interfaces = sorted(nics.keys())
    counter = -1
    vlanpattern = re.compile("[a-zA-Z0-9]+\.[0-9]+")

    for iname in interfaces:
        counter = counter + 1
        intf = nics[iname]

        if (intf["interface_type"] in ("bond", "bridge", "bonded_bridge_slave") or
                vlanpattern.match(iname) or iname.find(":") != -1):
            continue

        mac = intf["mac_address"]

        if not bridge:
            intf_bridge = intf["virt_bridge"]
            if intf_bridge == "":
                if profile_bridge == "":
                    raise InfoException(
                        "virt-bridge setting is not defined in cobbler")
                intf_bridge = profile_bridge

        else:
            if bridge.find(",") == -1:
                intf_bridge = bridge
            else:
                bridges = bridge.split(",")
                intf_bridge = bridges[counter]

        ret.append((intf_bridge, mac))

    return ret


def create_image_file(disks=None, **kwargs):
    disks = _sanitize_disks(disks)
    for path, size, driver_type in disks:
        if driver_type is None:
            continue
        if os.path.isdir(path) or os.path.exists(path):
            continue
        if str(size) == "0":
            continue
        utils.create_qemu_image_file(path, size, driver_type)


def build_commandline(uri,
                      name=None,
                      ram=None,
                      disks=None,
                      uuid=None,
                      extra=None,
                      vcpus=None,
                      profile_data=None,
                      arch=None,
                      gfx_type=None,
                      fullvirt=False,
                      bridge=None,
                      virt_type=None,
                      virt_auto_boot=False,
                      virt_pxe_boot=False,
                      qemu_driver_type=None,
                      qemu_net_type=None,
                      qemu_machine_type=None,
                      wait=0,
                      noreboot=False,
                      osimport=False):

    # Set flags for CLI arguments based on the virtinst_version
    # tuple above. Older versions of python-virtinst don't have
    # a version easily accessible, so it will be None and we can
    # easily disable features based on that (RHEL5 and older usually)

    disable_autostart = False
    disable_virt_type = False
    disable_boot_opt = False
    disable_driver_type = False
    disable_net_model = False
    disable_machine_type = False
    oldstyle_macs = False
    oldstyle_accelerate = False

    if not virtinst_version:
        print("- warning: old virt-install detected, a lot of features will "
              "be disabled")
        disable_autostart = True
        disable_boot_opt = True
        disable_virt_type = True
        disable_driver_type = True
        disable_net_model = True
        disable_machine_type = True
        oldstyle_macs = True
        oldstyle_accelerate = True

    import_exists = False  # avoid duplicating --import parameter
    disable_extra = False  # disable --extra-args on --import
    if osimport:
        disable_extra = True

    is_import = uri.startswith("import")
    if is_import:
        # We use the special value 'import' for imagecreate.py. Since
        # it is connection agnostic, just let virt-install choose the
        # best hypervisor.
        uri = ""
        fullvirt = None

    is_xen = uri.startswith("xen")
    is_qemu = uri.startswith("qemu")
    if is_qemu:
        if virt_type != "kvm":
            fullvirt = True
        else:
            fullvirt = None

    floppy = None
    cdrom = None
    location = None
    importpath = None

    if is_import:
        importpath = profile_data.get("file")
        if not importpath:
            raise InfoException("Profile 'file' required for image install")

    elif "file" in profile_data:
        if is_xen:
            raise InfoException("Xen does not work with --image yet")

        # this is an image based installation
        input_path = profile_data["file"]
        print("- using image location %s" % input_path)
        if input_path.find(":") == -1:
            # this is not an NFS path
            cdrom = input_path
        else:
            (tempdir, filename) = utils.nfsmount(input_path)
            cdrom = os.path.join(tempdir, filename)

        autoinst = profile_data.get("autoinst", "")
        if autoinst != "":
            # we have a (windows?) answer file we have to provide
            # to the ISO.
            print("I want to make a floppy for %s" % autoinst)
            floppy = utils.make_floppy(autoinst)
    elif is_qemu or is_xen:
        # images don't need to source this
        if "install_tree" not in profile_data:
            raise InfoException(
                "Cannot find install source in autoinst file, aborting.")

        if not profile_data["install_tree"].endswith("/"):
            profile_data["install_tree"] = profile_data["install_tree"] + "/"

        location = profile_data["install_tree"]

    disks = _sanitize_disks(disks)
    nics = _sanitize_nics(profile_data.get("interfaces"),
                          bridge,
                          profile_data.get("virt_bridge"),
                          profile_data.get("network_count"))
    if not nics:
        # for --profile you get one NIC, go define a system if you want more.
        # FIXME: can mac still be sent on command line in this case?

        if bridge is None:
            bridge = profile_data["virt_bridge"]

        if bridge == "":
            raise InfoException(
                "virt-bridge setting is not defined in cobbler")
        nics = [(bridge, None)]

    kernel = profile_data.get("kernel_local")
    initrd = profile_data.get("initrd_local")
    breed = profile_data.get("breed")
    os_version = profile_data.get("os_version")
    if os_version and breed == "ubuntu":
        os_version = "ubuntu%s" % os_version
    if os_version and breed == "debian":
        os_version = "debian%s" % os_version

    net_model = None
    disk_bus = None
    machine_type = None

    if is_qemu:
        net_model = qemu_net_type
        disk_bus = qemu_driver_type
        machine_type = qemu_machine_type

    if machine_type is None:
        machine_type = "pc"

    cmd = "virt-install "
    if uri:
        cmd += "--connect %s " % uri

    cmd += "--name %s " % name
    cmd += "--ram %s " % ram
    cmd += "--vcpus %s " % vcpus

    if uuid:
        cmd += "--uuid %s " % uuid

    if virt_auto_boot and not disable_autostart:
        cmd += "--autostart "

    if gfx_type is None:
        cmd += "--nographics "
    else:
        cmd += "--%s " % gfx_type

    if is_qemu and virt_type:
        if not disable_virt_type:
            cmd += "--virt-type %s " % virt_type

    if is_qemu and machine_type and not disable_machine_type:
        cmd += "--machine %s " % machine_type

    if fullvirt or is_qemu or is_import:
        if fullvirt is not None:
            cmd += "--hvm "
        elif oldstyle_accelerate:
            cmd += "--accelerate "

        if virt_pxe_boot or is_xen:
            cmd += "--pxe "
        elif cdrom:
            cmd += "--cdrom %s " % cdrom
        elif location:
            cmd += "--location %s " % location
            if is_qemu and extra and not(virt_pxe_boot) and not(disable_extra):
                cmd += ("--extra-args=\"%s\" " % (extra))
        elif importpath:
            cmd += "--import "
            import_exists = True

        if arch:
            cmd += "--arch %s " % arch
    else:
        cmd += "--paravirt "
        if not disable_boot_opt:
            cmd += ("--boot kernel=%s,initrd=%s,kernel_args=\"%s\" " %
                    (kernel, initrd, extra))
        else:
            if location:
                cmd += "--location %s " % location
                if extra:
                    cmd += "--extra-args=\"%s\" " % extra

    if breed and breed != "other":
        if os_version and os_version != "other":
            if breed == "suse":
                suse_version_re = re.compile("^(opensuse[0-9]+)\.([0-9]+)$")
                if suse_version_re.match(os_version):
                    os_version = suse_version_re.match(os_version).groups()[0]
            # make sure virt-install knows about our os_version,
            # otherwise default it to virtio26 or generic26
            # found = False
            if os_version not in supported_variants:
                if "virtio26" in supported_variants:
                    os_version = "virtio26"
                else:
                    os_version = "generic26"
                print("- warning: virt-install doesn't know this os_version, "
                      "defaulting to %s" % os_version)
            cmd += "--os-variant %s " % os_version
        else:
            distro = "unix"
            if breed in ["debian", "suse", "redhat"]:
                distro = "linux"
            elif breed in ["windows"]:
                distro = "windows"

            cmd += "--os-type %s " % distro

    if importpath:
        # This needs to be the first disk for import to work
        cmd += "--disk path=%s " % importpath

    for path, size, driver_type in disks:
        print("- adding disk: %s of size %s (driver type=%s)" %
              (path, size, driver_type))
        cmd += "--disk path=%s" % (path)
        if str(size) != "0":
            cmd += ",size=%s" % size
        if disk_bus:
            cmd += ",bus=%s" % disk_bus
        if driver_type and not disable_driver_type:
            cmd += ",format=%s" % driver_type
        cmd += " "

    if floppy:
        cmd += "--disk path=%s,device=floppy " % floppy

    for bridge, mac in nics:
        cmd += "--network bridge=%s" % bridge
        if net_model and not disable_net_model:
            cmd += ",model=%s" % net_model
        if mac:
            if oldstyle_macs:
                cmd += " --mac=%s" % mac
            else:
                cmd += ",mac=%s" % mac
        cmd += " "

    cmd += "--wait %d " % int(wait)
    if noreboot:
        cmd += "--noreboot "
    if osimport and not(import_exists):
        cmd += "--import "
    cmd += "--noautoconsole "

    return shlex.split(cmd.strip())
