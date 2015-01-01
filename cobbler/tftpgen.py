"""
Generate files provided by TFTP server based on Cobbler object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import os.path
import re
import shutil
import socket
import string

from cexceptions import CX
import templar
import utils


class TFTPGen:
    """
    Generate files provided by TFTP server
    """
    def __init__(self, collection_mgr, logger):
        """
        Constructor
        """
        self.collection_mgr = collection_mgr
        self.logger = logger
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.images = collection_mgr.images()
        self.templar = templar.Templar(collection_mgr)
        self.bootloc = utils.tftpboot_location()

    def copy_bootloaders(self):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in
        /etc/cobbler/settings.
        """
        dst = self.bootloc
        grub_dst = os.path.join(dst, "grub")
        boot_dst = os.path.join(dst, "boot/grub")

        # copy syslinux from one of two locations
        try:
            try:
                utils.copyfile_pattern(
                    '/var/lib/cobbler/loaders/pxelinux.0',
                    dst, api=self.api, cache=False, logger=self.logger)
                utils.copyfile_pattern(
                    '/var/lib/cobbler/loaders/menu.c32',
                    dst, api=self.api, cache=False, logger=self.logger)
            except:
                utils.copyfile_pattern(
                    '/usr/share/syslinux/pxelinux.0',
                    dst, api=self.api, cache=False, logger=self.logger)
                utils.copyfile_pattern(
                    '/usr/share/syslinux/menu.c32',
                    dst, api=self.api, cache=False, logger=self.logger)

        except:
            utils.copyfile_pattern(
                '/usr/lib/syslinux/pxelinux.0',
                dst, api=self.api, cache=False, logger=self.logger)
            utils.copyfile_pattern(
                '/usr/lib/syslinux/menu.c32',
                dst, api=self.api, cache=False, logger=self.logger)

        # copy yaboot which we include for PowerPC targets
        utils.copyfile_pattern(
            '/var/lib/cobbler/loaders/yaboot', dst,
            require_match=False, api=self.api, cache=False, logger=self.logger)

        utils.copyfile_pattern(
            '/var/lib/cobbler/loaders/boot/grub/*', boot_dst,
            require_match=False, api=self.api, cache=False, logger=self.logger)

        try:
            utils.copyfile_pattern(
                '/usr/lib/syslinux/memdisk',
                dst, api=self.api, cache=False, logger=self.logger)
        except:
            utils.copyfile_pattern(
                '/usr/share/syslinux/memdisk', dst,
                require_match=False, api=self.api, cache=False, logger=self.logger)

        # Copy gPXE/iPXE bootloader if it exists
        utils.copyfile_pattern(
            '/usr/share/*pxe/undionly.kpxe', dst,
            require_match=False, api=self.api, cache=False, logger=self.logger)

        # Copy grub EFI bootloaders if possible:
        utils.copyfile_pattern(
            '/var/lib/cobbler/loaders/grub*.efi', grub_dst,
            require_match=False, api=self.api, cache=False, logger=self.logger)

        pxegrub_imported = False
        for i in self.distros:
            if 'nexenta' == i.breed and not pxegrub_imported:
                # name_without_arch = i.name[:-7] # removing -x86_64 from the fin on the string.
                if os.path.isdir(os.path.join(self.bootloc, 'boot')):
                    shutil.rmtree(os.path.join(self.bootloc, 'boot'))
                shutil.copytree(os.path.join('/var', 'www', 'cobbler', 'distro_mirror', i.name, 'boot'),
                                os.path.join(self.bootloc, 'boot'))
                pxegrub_imported = True

    def copy_images(self):
        """
        Like copy_distros except for images.
        """
        errors = list()
        for i in self.images:
            try:
                self.copy_single_image_files(i)
            except CX, e:
                errors.append(e)
                self.logger.error(e.value)

        # FIXME: using logging module so this ends up in cobbler.log?

    def copy_single_distro_files(self, d, dirtree, symlink_ok):
        distros = os.path.join(dirtree, "images")
        distro_dir = os.path.join(distros, d.name)
        utils.mkdir(distro_dir)
        kernel = utils.find_kernel(d.kernel)    # full path
        initrd = utils.find_initrd(d.initrd)    # full path

        if kernel is None:
            raise CX("kernel not found: %(file)s, distro: %(distro)s" % {"file": d.kernel, "distro": d.name})

        if initrd is None:
            raise CX("initrd not found: %(file)s, distro: %(distro)s" % {"file": d.initrd, "distro": d.name})

        # Koan manages remote kernel itself, but for consistent PXE
        # configurations the synchronization is still necessary
        if not utils.file_is_remote(kernel):
            b_kernel = os.path.basename(kernel)
            dst1 = os.path.join(distro_dir, b_kernel)
            utils.linkfile(kernel, dst1, symlink_ok=symlink_ok, api=self.api, logger=self.logger)
        else:
            b_kernel = os.path.basename(kernel)
            dst1 = os.path.join(distro_dir, b_kernel)
            utils.copyremotefile(kernel, dst1, api=None, logger=self.logger)

        if not utils.file_is_remote(initrd):
            b_initrd = os.path.basename(initrd)
            dst2 = os.path.join(distro_dir, b_initrd)
            utils.linkfile(initrd, dst2, symlink_ok=symlink_ok, api=self.api, logger=self.logger)
        else:
            b_initrd = os.path.basename(initrd)
            dst1 = os.path.join(distro_dir, b_initrd)
            utils.copyremotefile(initrd, dst1, api=None, logger=self.logger)

        if "nexenta" == d.breed:
            try:
                os.makedirs(os.path.join(distro_dir, 'platform', 'i86pc', 'kernel', 'amd64'))
                os.makedirs(os.path.join(distro_dir, 'platform', 'i86pc', 'amd64'))
            except OSError:
                pass
            b_kernel = os.path.basename(kernel)
            utils.linkfile(kernel, os.path.join(distro_dir, 'platform', 'i86pc', 'kernel', 'amd64', b_kernel),
                           symlink_ok=symlink_ok, api=self.api, logger=self.logger)
            b_initrd = os.path.basename(initrd)
            utils.linkfile(initrd, os.path.join(distro_dir, 'platform', 'i86pc', 'amd64', b_initrd),
                           symlink_ok=symlink_ok, api=self.api, logger=self.logger)

            # the [:-7] removes the architecture
            if os.path.isdir(os.path.join('/var', 'www', 'cobbler', 'links', d.name, 'install_profiles')):
                shutil.rmtree(os.path.join('/var', 'www', 'cobbler', 'links', d.name, 'install_profiles'))
            shutil.copytree(os.path.join('/var', 'lib', 'cobbler', 'autoinstall_templates', 'install_profiles'),
                            os.path.join('/var', 'www', 'cobbler', 'links', d.name, 'install_profiles'))

    def copy_single_image_files(self, img):
        images_dir = os.path.join(self.bootloc, "images2")
        filename = img.file
        if not os.path.exists(filename):
            # likely for virtual usage, cannot use
            return
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        newfile = os.path.join(images_dir, img.name)
        utils.linkfile(filename, newfile, api=self.api, logger=self.logger)

    def write_all_system_files(self, system, menu_items):

        profile = system.get_conceptual_parent()
        if profile is None:
            raise CX("system %(system)s references a missing profile %(profile)s" % {"system": system.name, "profile": system.profile})

        distro = profile.get_conceptual_parent()
        image_based = False
        image = None
        if distro is None:
            if profile.COLLECTION_TYPE == "profile":
                raise CX("profile %(profile)s references a missing distro %(distro)s" % {"profile": system.profile, "distro": profile.distro})
            else:
                image_based = True
                image = profile

        pxe_metadata = {'pxe_menu_items': menu_items}

        # generate one record for each described NIC ..
        for (name, interface) in system.interfaces.iteritems():

            f1 = utils.get_config_filename(system, interface=name)
            if f1 is None:
                self.logger.warning("invalid interface recorded for system (%s,%s)" % (system.name, name))
                continue

            if image_based:
                working_arch = image.arch
            else:
                working_arch = distro.arch

            if working_arch is None:
                raise "internal error, invalid arch supplied"

            # for tftp only ...
            grub_path = None
            if working_arch in ["i386", "x86", "x86_64", "arm", "standard"]:
                # pxelinux wants a file named $name under pxelinux.cfg
                f2 = os.path.join(self.bootloc, "pxelinux.cfg", f1)

                # Only generating grub menus for these arch's:
                grub_path = os.path.join(self.bootloc, "grub", f1.upper())

            elif working_arch.startswith("ppc"):
                # Determine filename for system-specific bootloader config
                filename = "%s" % utils.get_config_filename(system, interface=name).lower()
                # to inherit the distro and system's boot_loader values correctly
                blended_system = utils.blender(self.api, False, system)
                if blended_system["boot_loader"] == "pxelinux":
                    # pxelinux wants a file named $name under pxelinux.cfg
                    f2 = os.path.join(self.bootloc, "pxelinux.cfg", f1)
                elif distro.boot_loader == "grub2":
                    f2 = os.path.join(self.bootloc, "boot/grub", "grub.cfg-" + filename)
                else:
                    f2 = os.path.join(self.bootloc, "etc", filename)

                    # Link to the yaboot binary
                    f3 = os.path.join(self.bootloc, "ppc", filename)
                    if os.path.lexists(f3):
                        utils.rmfile(f3)
                    os.symlink("../yaboot", f3)
            else:
                continue

            if system.is_management_supported():
                if not image_based:
                    self.write_pxe_file(f2, system, profile, distro, working_arch, metadata=pxe_metadata)
                    if grub_path:
                        self.write_pxe_file(grub_path, system, profile, distro, working_arch, format="grub")
                else:
                    self.write_pxe_file(f2, system, None, None, working_arch, image=profile, metadata=pxe_metadata)
            else:
                # ensure the file doesn't exist
                utils.rmfile(f2)
                if grub_path:
                    utils.rmfile(grub_path)

    def make_pxe_menu(self):
        self.make_actual_pxe_menu()

    def get_menu_items(self):
        """
        Generates menu items for pxe and grub
        """
        # sort the profiles
        profile_list = [profile for profile in self.profiles]

        def sort_name(a, b):
            return cmp(a.name, b.name)

        profile_list.sort(sort_name)

        # sort the images
        image_list = [image for image in self.images]
        image_list.sort(sort_name)

        # Build out menu items and append each to this master list, used for
        # the default menus:
        pxe_menu_items = ""
        grub_menu_items = ""

        # For now, profiles are the only items we want grub EFI boot menu entries for:
        for profile in profile_list:
            if not profile.enable_menu:
                # This profile has been excluded from the menu
                continue
            distro = profile.get_conceptual_parent()
            if distro.name.find('exenta') != -1:
                # nexenta has a separate menu
                continue

            contents = self.write_pxe_file(
                filename=None,
                system=None, profile=profile, distro=distro, arch=distro.arch,
                include_header=False)
            if contents is not None:
                pxe_menu_items += contents + "\n"

            grub_contents = self.write_pxe_file(
                filename=None,
                system=None, profile=profile, distro=distro, arch=distro.arch,
                include_header=False, format="grub")
            if grub_contents is not None:
                grub_menu_items += grub_contents + "\n"


        # image names towards the bottom
        for image in image_list:
            if os.path.exists(image.file):
                contents = self.write_pxe_file(
                    filename=None,
                    system=None, profile=None, distro=None, arch=image.arch,
                    image=image)
                if contents is not None:
                    pxe_menu_items += contents + "\n"

        return {'pxe': pxe_menu_items, 'grub': grub_menu_items}

    def get_menu_items_nexenta(self):
        """
        Generates menu items for nexenta
        """
        # sort the profiles
        profile_list = [profile for profile in self.profiles]

        def sort_name(a, b):
            return cmp(a.name, b.name)

        profile_list.sort(sort_name)

        # Build out menu items and append each to this master list, used for
        # the default menus:
        pxe_menu_items = ""
        grub_menu_items = ""

        # For now, profiles are the only items we want grub EFI boot menu entries for:
        for profile in profile_list:
            if not profile.enable_menu:
                # This profile has been excluded from the menu
                continue
            distro = profile.get_conceptual_parent()

            if distro.name.find('nexenta') != -1:
                contents = self.write_pxe_file(
                    filename=None,
                    system=None, profile=profile, distro=distro, arch=distro.arch,
                    include_header=False)
                if contents is not None:
                    pxe_menu_items += contents + "\n"

                grub_contents = self.write_pxe_file(
                    filename=None,
                    system=None, profile=profile, distro=distro, arch=distro.arch,
                    include_header=False, format="nexenta")
                if grub_contents is not None:
                    grub_menu_items += grub_contents + "\n"

        return {'pxe': pxe_menu_items, 'grub': grub_menu_items}

    def make_actual_pxe_menu(self):
        """
        Generates both pxe and grub boot menus.
        """
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")

        if default is None:
            timeout_action = "local"
        else:
            timeout_action = default.profile

        menu_items = self.get_menu_items()

        # Write the PXE menu:
        metadata = {"pxe_menu_items": menu_items['pxe'], "pxe_timeout_profile": timeout_action}
        outfile = os.path.join(self.bootloc, "pxelinux.cfg", "default")
        template_src = open(os.path.join(self.settings.boot_loader_conf_template_dir, "pxedefault.template"))
        template_data = template_src.read()
        self.templar.render(template_data, metadata, outfile, None)
        template_src.close()

        # Write the grub menu:
        metadata = {"grub_menu_items": menu_items['grub']}
        outfile = os.path.join(self.bootloc, "grub", "efidefault")
        template_src = open(os.path.join(self.settings.boot_loader_conf_template_dir, "efidefault.template"))
        template_data = template_src.read()
        self.templar.render(template_data, metadata, outfile, None)
        template_src.close()

        # write the nexenta menu
        menu_items = self.get_menu_items_nexenta()
        metadata = {"grub_menu_items": menu_items['grub']}
        outfile = os.path.join(self.bootloc, "boot", 'grub', 'menu.lst')
        template_src = open(os.path.join(self.settings.boot_loader_conf_template_dir, "nexenta_grub_menu.template"))
        template_data = template_src.read()
        self.templar.render(template_data, metadata, outfile, None)
        template_src.close()


    def write_pxe_file(self, filename, system, profile, distro, arch,
                       image=None, include_header=True, metadata=None, format="pxe"):
        """
        Write a configuration file for the boot loader(s).
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py

        Can be used for different formats, "pxe" (default) and "grub".
        """
        if arch is None:
            raise "missing arch"

        if image and not os.path.exists(image.file):
            return None     # nfs:// URLs or something, can't use for TFTP

        if metadata is None:
            metadata = {}

        (rval, settings) = utils.input_string_or_dict(self.settings.to_dict())
        if rval:
            for key in settings.keys():
                metadata[key] = settings[key]
        # ---
        # just some random variables
        template = None
        buffer = ""

        # ---
        autoinstall_path = None
        kernel_path = None
        initrd_path = None
        img_path = None

        if image is None:
            # not image based, it's something normalish

            img_path = os.path.join("/images", distro.name)

            if 'nexenta' == distro.breed:
                kernel_path = os.path.join("/images", distro.name, 'platform', 'i86pc', 'kernel', 'amd64', os.path.basename(distro.kernel))
                initrd_path = os.path.join("/images", distro.name, 'platform', 'i86pc', 'amd64', os.path.basename(distro.initrd))
            else:
                kernel_path = os.path.join("/images", distro.name, os.path.basename(distro.kernel))
                initrd_path = os.path.join("/images", distro.name, os.path.basename(distro.initrd))

            # Find the automatic installation file if we inherit from another profile
            if system:
                blended = utils.blender(self.api, True, system)
            else:
                blended = utils.blender(self.api, True, profile)
            autoinstall_path = blended.get("autoinstall", "")

            # update metadata with all known information
            # this allows for more powerful templating
            metadata.update(blended)

        else:
            # this is an image we are making available, not kernel+initrd
            if image.image_type == "direct":
                kernel_path = os.path.join("/images2", image.name)
            elif image.image_type == "memdisk":
                kernel_path = "/memdisk"
                initrd_path = os.path.join("/images2", image.name)
            else:
                # CD-ROM ISO or virt-clone image? We can't PXE boot it.
                kernel_path = None
                initrd_path = None

        if img_path is not None and "img_path" not in metadata:
            metadata["img_path"] = img_path
        if kernel_path is not None and "kernel_path" not in metadata:
            metadata["kernel_path"] = kernel_path
        if initrd_path is not None and "initrd_path" not in metadata:
            metadata["initrd_path"] = initrd_path

        # ---
        # choose a template
        if system:
            if format == "grub":
                if system.netboot_enabled:
                    template = os.path.join(self.settings.boot_loader_conf_template_dir, "grubsystem.template")
                else:
                    local = os.path.join(self.settings.boot_loader_conf_template_dir, "grublocal.template")
                    if os.path.exists(local):
                        template = local
            else:   # pxe
                if system.netboot_enabled:
                    template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem.template")

                    if arch.startswith("ppc"):
                        # to inherit the distro and system's boot_loader values correctly
                        blended_system = utils.blender(self.api, False, system)
                        if blended_system["boot_loader"] == "pxelinux":
                            template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_ppc.template")
                        elif distro.boot_loader == "grub2":
                            template = os.path.join(self.settings.boot_loader_conf_template_dir, "grub2_ppc.template")
                        else:
                            template = os.path.join(self.settings.boot_loader_conf_template_dir, "yaboot_ppc.template")
                    elif arch.startswith("arm"):
                        template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_arm.template")
                    elif distro and distro.os_version.startswith("esxi"):
                        # ESXi uses a very different pxe method, using more files than
                        # a standard automatic installation file and different options -
                        # so giving it a dedicated PXE template makes more sense than
                        # shoe-horning it into the existing templates
                        template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_esxi.template")
                else:
                    # local booting on ppc requires removing the system-specific dhcpd.conf filename
                    if arch is not None and arch.startswith("ppc"):
                        # Disable yaboot network booting for all interfaces on the system
                        for (name, interface) in system.interfaces.iteritems():

                            filename = "%s" % utils.get_config_filename(system, interface=name).lower()

                            # Remove symlink to the yaboot binary
                            f3 = os.path.join(self.bootloc, "ppc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)

                            # Remove the interface-specific config file
                            f3 = os.path.join(self.bootloc, "boot/grub", "grub.cfg-" + filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)
                            f3 = os.path.join(self.bootloc, "etc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)

                        # Yaboot/OF doesn't support booting locally once you've
                        # booted off the network, so nothing left to do
                        return None
                    else:
                        template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxelocal.template")
        else:
            # not a system record, so this is a profile record or an image
            if arch.startswith("arm"):
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxeprofile_arm.template")
            elif format == "grub":
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "grubprofile.template")
            elif distro and distro.os_version.startswith("esxi"):
                # ESXi uses a very different pxe method, see comment above in the system section
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxeprofile_esxi.template")
            elif 'nexenta' == format:
                template = os.path.join(self.settings.boot_loader_conf_template_dir, 'nexenta_profile.template')
            else:
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxeprofile.template")


        if kernel_path is not None:
            metadata["kernel_path"] = kernel_path
        if initrd_path is not None:
            metadata["initrd_path"] = initrd_path

        # generate the kernel options and append line:
        kernel_options = self.build_kernel_options(system, profile, distro,
                                                   image, arch, autoinstall_path)
        metadata["kernel_options"] = kernel_options

        if distro and distro.os_version.startswith("esxi") and filename is not None:
            append_line = "BOOTIF=%s" % (os.path.basename(filename))
        elif "initrd_path" in metadata and (not arch or arch not in ["ppc", "ppc64", "arm"]):
            append_line = "append initrd=%s" % (metadata["initrd_path"])
        else:
            append_line = "append "
        append_line = "%s%s" % (append_line, kernel_options)
        if arch.startswith("ppc"):
            # remove the prefix "append"
            # TODO: this looks like it's removing more than append, really
            # not sure what's up here...
            append_line = append_line[7:]
        if distro and distro.os_version.startswith("xenserver620"):
            append_line = "%s" % (kernel_options)
        metadata["append_line"] = append_line

        # store variables for templating
        metadata["menu_label"] = ""
        if profile:
            if arch not in ["ppc", "ppc64"]:
                metadata["menu_label"] = "MENU LABEL %s" % profile.name
                metadata["profile_name"] = profile.name
        elif image:
            metadata["menu_label"] = "MENU LABEL %s" % image.name
            metadata["profile_name"] = image.name

        if system:
            metadata["system_name"] = system.name


        # get the template
        if kernel_path is not None:
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()
        else:
            # this is something we can't PXE boot
            template_data = "\n"

        # save file and/or return results, depending on how called.
        buffer = self.templar.render(template_data, metadata, None)
        if filename is not None:
            self.logger.info("generating: %s" % filename)
            fd = open(filename, "w")
            fd.write(buffer)
            fd.close()
        return buffer

    def build_kernel_options(self, system, profile, distro, image, arch,
                             autoinstall_path):
        """
        Builds the full kernel options line.
        """

        management_interface = None
        if system is not None:
            blended = utils.blender(self.api, False, system)
            # find the first management interface
            try:
                for intf in system.interfaces.keys():
                    if system.interfaces[intf]["management"]:
                        management_interface = intf
                        break
            except:
                # just skip this then
                pass
        elif profile is not None:
            blended = utils.blender(self.api, False, profile)
        else:
            blended = utils.blender(self.api, False, image)

        append_line = ""
        kopts = blended.get("kernel_options", dict())

        # since network needs to be configured again (it was already in netboot) when kernel boots
        # and we choose to do it dinamically, we need to set 'ksdevice' to one of
        # the interfaces' MAC addresses in ppc systems.
        # ksdevice=bootif is not useful in yaboot, as the "ipappend" line is a pxe feature.
        if system and arch and "ppc" in arch:
            for intf in system.interfaces.keys():
                # use first interface with defined IP and MAC, since these are required
                # fields in a DHCP entry
                mac_address = system.interfaces[intf]['mac_address']
                ip_address = system.interfaces[intf]['ip_address']
                if mac_address and ip_address:
                    kopts['BOOTIF'] = '01-' + mac_address
                    kopts['ksdevice'] = mac_address
                    break

        # support additional initrd= entries in kernel options.
        if "initrd" in kopts:
            append_line = ",%s" % kopts.pop("initrd")
        hkopts = utils.dict_to_string(kopts)
        append_line = "%s %s" % (append_line, hkopts)

        # automatic installation file path rewriting (get URLs for local files)
        if autoinstall_path is not None and autoinstall_path != "":

            # FIXME: need to make shorter rewrite rules for these URLs

            try:
                ipaddress = socket.gethostbyname_ex(blended["http_server"])[2][0]
            except socket.gaierror:
                ipaddress = blended["http_server"]
            URL_REGEX = "[a-zA-Z]*://.*"
            local_autoinstall_file = not re.match(URL_REGEX, autoinstall_path)
            if local_autoinstall_file:
                if system is not None:
                    autoinstall_path = "http://%s/cblr/svc/op/autoinstall/system/%s" % (ipaddress, system.name)
                else:
                    autoinstall_path = "http://%s/cblr/svc/op/autoinstall/profile/%s" % (ipaddress, profile.name)

            if distro.breed is None or distro.breed == "redhat":

                append_line += " kssendmac"
                append_line = "%s ks=%s" % (append_line, autoinstall_path)
                gpxe = blended["enable_gpxe"]
                if gpxe:
                    append_line = append_line.replace('ksdevice=bootif', 'ksdevice=${net0/mac}')
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, autoinstall_path)
            elif distro.breed == "debian" or distro.breed == "ubuntu":
                append_line = "%s auto-install/enable=true priority=critical netcfg/choose_interface=auto url=%s" % (append_line, autoinstall_path)
                if management_interface:
                    append_line += " netcfg/choose_interface=%s" % management_interface
            elif distro.breed == "freebsd":
                append_line = "%s ks=%s" % (append_line, autoinstall_path)

                # rework kernel options for debian distros
                translations = {'ksdevice': "interface", 'lang': "locale"}
                for k, v in translations.iteritems():
                    append_line = append_line.replace("%s=" % k, "%s=" % v)

                # interface=bootif causes a failure
                append_line = append_line.replace("interface=bootif", "")
            elif distro.breed == "vmware":
                if distro.os_version.find("esxi") != -1:
                    # ESXi is very picky, it's easier just to redo the
                    # entire append line here since
                    append_line = " ks=%s %s" % (autoinstall_path, hkopts)
                    # ESXi likes even fewer options, so we remove them too
                    append_line = append_line.replace("kssendmac", "")
                else:
                    append_line = "%s vmkopts=debugLogToSerial:1 mem=512M ks=%s" % \
                        (append_line, autoinstall_path)
                # interface=bootif causes a failure
                append_line = append_line.replace("ksdevice=bootif", "")
            elif distro.breed == "xen":
                if distro.os_version.find("xenserver620") != -1:
                    img_path = os.path.join("/images", distro.name)
                    append_line = "append %s/xen.gz dom0_max_vcpus=2 dom0_mem=752M com1=115200,8n1 console=com1,vga --- %s/vmlinuz xencons=hvc console=hvc0 console=tty0 install answerfile=%s --- %s/install.img" % (img_path, img_path, autoinstall_path, img_path)
                    return append_line
            elif distro.breed == "powerkvm":
                append_line += " kssendmac"
                append_line = "%s kvmp.inst.auto=%s" % (append_line, autoinstall_path)

        if distro is not None and (distro.breed in ["debian", "ubuntu"]):
            # Hostname is required as a parameter, the one in the preseed is
            # not respected, so calculate if we have one here.
            # We're trying: first part of FQDN in hostname field, then system
            # name, then profile name.
            # In Ubuntu, this is at least used for the volume group name when
            # using LVM.
            domain = "local.lan"
            if system is not None:
                if system.hostname is not None and system.hostname != "":
                    # If this is a FQDN, grab the first bit
                    hostname = system.hostname.split(".")[0]
                    _domain = system.hostname.split(".")[1:]
                    if _domain:
                        domain = ".".join(_domain)
                else:
                    hostname = system.name
            else:
                # ubuntu at the very least does not like having underscores
                # in the hostname.
                # FIXME: Really this should remove all characters that are
                # forbidden in hostnames
                hostname = profile.name.replace("_", "")

            # At least for debian deployments configured for DHCP networking
            # this values are not used, but specifying here avoids questions
            append_line = "%s hostname=%s" % (append_line, hostname)
            append_line = "%s domain=%s" % (append_line, domain)

            # A similar issue exists with suite name, as installer requires
            # the existence of "stable" in the dists directory
            append_line = "%s suite=%s" % (append_line, distro.os_version)
        elif distro is not None and distro.breed == 'nexenta':
            append_line = "-B iso_nfs_path=%s:/var/www/cobbler/links/%s,auto_install=1" % (blended['next_server'], distro.name)

        # append necessary kernel args for arm architectures
        if arch is not None and arch.startswith("arm"):
            append_line = "%s fixrtc vram=48M omapfb.vram=0:24M" % append_line

        # do variable substitution on the append line
        # promote all of the autoinstall_meta variables
        if "autoinstall_meta" in blended:
            blended.update(blended["autoinstall_meta"])
        append_line = self.templar.render(append_line, utils.flatten(blended), None)

        # FIXME - the append_line length limit is architecture specific
        if len(append_line) >= 255:
            self.logger.warning("warning: kernel option length exceeds 255")

        return append_line

    def write_templates(self, obj, write_file=False, path=None):
        """
        A semi-generic function that will take an object
        with a template_files dict {source:destiation}, and
        generate a rendered file.  The write_file option
        allows for generating of the rendered output without
        actually creating any files.

        The return value is a dict of the destination file
        names (after variable substitution is done) and the
        data in the file.
        """
        self.logger.info("Writing template files for %s" % obj.name)

        results = {}

        try:
            templates = obj.template_files
        except:
            return results

        blended = utils.blender(self.api, False, obj)

        if obj.COLLECTION_TYPE == "distro":
            if re.search("esxi[56]", obj.os_version) is not None:
                realbootcfg = open(os.path.join(os.path.dirname(obj.kernel), 'boot.cfg')).read()
                bootmodules = re.findall(r'modules=(.*)', realbootcfg)
                for modules in bootmodules:
                    blended['esx_modules'] = modules.replace('/', '')

        autoinstall_meta = blended.get("autoinstall_meta", {})
        try:
            del blended["autoinstall_meta"]
        except:
            pass
        blended.update(autoinstall_meta)          # make available at top level

        templates = blended.get("template_files", {})
        try:
            del blended["template_files"]
        except:
            pass
        blended.update(templates)       # make available at top level

        (success, templates) = utils.input_string_or_dict(templates)

        if not success:
            return results

        # FIXME: img_path and local_img_path should probably be moved
        #        up into the blender function to ensure they're consistently
        #        available to templates across the board
        if blended["distro_name"]:
            blended['img_path'] = os.path.join("/images", blended["distro_name"])
            blended['local_img_path'] = os.path.join(utils.tftpboot_location(), "images", blended["distro_name"])

        for template in templates.keys():
            dest = templates[template]
            if dest is None:
                continue

            # Run the source and destination files through
            # templar first to allow for variables in the path
            template = self.templar.render(template, blended, None).strip()
            dest = os.path.normpath(self.templar.render(dest, blended, None).strip())
            # Get the path for the destination output
            dest_dir = os.path.normpath(os.path.dirname(dest))

            # If we're looking for a single template, skip if this ones
            # destination is not it.
            if path is not None and path != dest:
                continue

            # If we are writing output to a file, we allow files tobe
            # written into the tftpboot directory, otherwise force all
            # templated configs into the rendered directory to ensure that
            # a user granted cobbler privileges via sudo can't overwrite
            # arbitrary system files (This also makes cleanup easier).
            if os.path.isabs(dest_dir) and write_file:
                if dest_dir.find(utils.tftpboot_location()) != 0:
                    raise CX(" warning: template destination (%s) is outside %s, skipping." % (dest_dir, utils.tftpboot_location()))
                    continue
            elif write_file:
                dest_dir = os.path.join(self.settings.webdir, "rendered", dest_dir)
                dest = os.path.join(dest_dir, os.path.basename(dest))
                if not os.path.exists(dest_dir):
                    utils.mkdir(dest_dir)

            # Check for problems
            if not os.path.exists(template):
                raise CX("template source %s does not exist" % template)
                continue
            elif write_file and not os.path.isdir(dest_dir):
                raise CX("template destination (%s) is invalid" % dest_dir)
                continue
            elif write_file and os.path.exists(dest):
                raise CX("template destination (%s) already exists" % dest)
                continue
            elif write_file and os.path.isdir(dest):
                raise CX("template destination (%s) is a directory" % dest)
                continue
            elif template == "" or dest == "":
                raise CX("either the template source or destination was blank (unknown variable used?)" % dest)
                continue

            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()

            buffer = self.templar.render(template_data, blended, None)
            results[dest] = buffer

            if write_file:
                self.logger.info("generating: %s" % dest)
                fd = open(dest, "w")
                fd.write(buffer)
                fd.close()

        return results

    def generate_gpxe(self, what, name):
        if what.lower() not in ("profile", "system"):
            return "# gpxe is only valid for profiles and systems"

        distro = None
        if what == "profile":
            obj = self.api.find_profile(name=name)
            distro = obj.get_conceptual_parent()
        else:
            obj = self.api.find_system(name=name)
            distro = obj.get_conceptual_parent().get_conceptual_parent()
            netboot_enabled = obj.netboot_enabled

        # For multi-arch distros, the distro name in distro_mirror
        # may not contain the arch string, so we need to figure out
        # the path based on where the kernel is stored. We do this
        # because some distros base future downloads on the initial
        # URL passed in, so all of the files need to be at this location
        # (which is why we can't use the images link, which just contains
        # the kernel and initrd).
        distro_mirror_name = string.join(distro.kernel.split('/')[-2:-1], '')

        blended = utils.blender(self.api, False, obj)

        autoinstall_meta = blended.get("autoinstall_meta", {})
        try:
            del blended["autoinstall_meta"]
        except:
            pass
        blended.update(autoinstall_meta)      # make available at top level

        blended['distro'] = distro.name
        blended['distro_mirror_name'] = distro_mirror_name
        blended['kernel_name'] = os.path.basename(distro.kernel)
        blended['initrd_name'] = os.path.basename(distro.initrd)

        if what == "profile":
            blended['append_line'] = self.build_kernel_options(None, obj, distro, None, None, blended['autoinstall'])
        else:
            blended['append_line'] = self.build_kernel_options(obj, None, distro, None, None, blended['autoinstall'])

        template = None
        if distro.breed in ['redhat', 'debian', 'ubuntu', 'suse']:
            # all of these use a standard kernel/initrd setup so
            # they all use the same gPXE template
            template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_linux.template" % what.lower())
        elif distro.breed == 'vmware':
            if distro.os_version == 'esx4':
                # older ESX is pretty much RHEL, so it uses the standard kernel/initrd setup
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_linux.template" % what.lower())
            elif distro.os_version == 'esxi4':
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_esxi4.template" % what.lower())
            elif distro.os_version.startswith('esxi5'):
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_esxi5.template" % what.lower())
            elif distro.os_version.startswith('esxi6'):
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_esxi6.template" % what.lower())
        elif distro.breed == 'freebsd':
            template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_freebsd.template" % what.lower())

        if what == "system":
            if not netboot_enabled:
                template = os.path.join(self.settings.boot_loader_conf_template_dir, "gpxe_%s_local.template" % what.lower())

        if not template:
            return "# unsupported breed/os version"

        if not os.path.exists(template):
            return "# gpxe template not found for the %s named %s (filename=%s)" % (what, name, template)

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None)

    def generate_bootcfg(self, what, name):
        if what.lower() not in ("profile", "system"):
            return "# bootcfg is only valid for profiles and systems"

        distro = None
        if what == "profile":
            obj = self.api.find_profile(name=name)
            distro = obj.get_conceptual_parent()
        else:
            obj = self.api.find_system(name=name)
            distro = obj.get_conceptual_parent().get_conceptual_parent()

        # For multi-arch distros, the distro name in distro_mirror
        # may not contain the arch string, so we need to figure out
        # the path based on where the kernel is stored. We do this
        # because some distros base future downloads on the initial
        # URL passed in, so all of the files need to be at this location
        # (which is why we can't use the images link, which just contains
        # the kernel and initrd).
        distro_mirror_name = string.join(distro.kernel.split('/')[-2:-1], '')

        blended = utils.blender(self.api, False, obj)

        autoinstall_meta = blended.get("autoinstall_meta", {})
        try:
            del blended["autoinstall_meta"]
        except:
            pass
        blended.update(autoinstall_meta)          # make available at top level

        blended['distro'] = distro_mirror_name

        # FIXME: img_path should probably be moved up into the
        #        blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_gpxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port, distro.name)
        else:
            blended['img_path'] = os.path.join("/images", distro.name)

        template = os.path.join(self.settings.boot_loader_conf_template_dir, "bootcfg_%s_%s.template" % (what.lower(), distro.os_version))
        if not os.path.exists(template):
            return "# boot.cfg template not found for the %s named %s (filename=%s)" % (what, name, template)

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None)

    def generate_script(self, what, objname, script_name):
        if what == "profile":
            obj = self.api.find_profile(name=objname)
        else:
            obj = self.api.find_system(name=objname)

        if not obj:
            return "# %s named %s not found" % (what, objname)

        distro = obj.get_conceptual_parent()
        while distro.get_conceptual_parent():
            distro = distro.get_conceptual_parent()

        blended = utils.blender(self.api, False, obj)

        autoinstall_meta = blended.get("autoinstall_meta", {})
        try:
            del blended["autoinstall_meta"]
        except:
            pass
        blended.update(autoinstall_meta)      # make available at top level

        # FIXME: img_path should probably be moved up into the
        #        blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_gpxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port, distro.name)
        else:
            blended['img_path'] = os.path.join("/images", distro.name)

        template = os.path.normpath(os.path.join("/var/lib/cobbler/autoinstall_scripts", script_name))
        if not os.path.exists(template):
            return "# script template %s not found" % script_name

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None, obj)
