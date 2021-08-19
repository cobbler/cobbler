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
import socket
from time import sleep
from typing import Optional

from cobbler import templar
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.validate import validate_autoinstall_script_name


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
        self.bootloc = self.settings.tftpboot_location

    def copy_bootloaders(self, dest):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in our settings file.
        """
        src = self.settings.bootloaders_dir
        dest = self.bootloc
        # Unfortunately using shutils copy_tree the dest directory must not exist, but we must not delete an already
        # partly synced /srv/tftp dir here. rsync is very convenient here, being very fast on an already copied folder.
        utils.subprocess_call(
            self.logger,
            ["rsync", "-rpt", "--copy-links", "--exclude=.cobbler_postun_cleanup", "{src}/".format(src=src), dest],
            shell=False
        )
        src = self.settings.grubconfig_dir
        utils.subprocess_call(
            self.logger,
            ["rsync", "-rpt", "--copy-links", "--exclude=README.grubconfig", "{src}/".format(src=src), dest],
            shell=False
        )

    def copy_images(self):
        """
        Like copy_distros except for images.
        """
        errors = list()
        for i in self.images:
            try:
                self.copy_single_image_files(i)
            except CX as e:
                errors.append(e)
                self.logger.error(e.value)

    def copy_single_distro_file(self, d_file, distro_dir, symlink_ok):
        """
        Copy a single file (kernel/initrd) to distro's images directory

        :param  d_file:     distro's kernel/initrd absolut or remote file path value
        :type   d_file:     str
        :param  distro_dir: directory (typically in {www,tftp}/images) where to copy the file
        :type   distro_dir: str
        :param  symlink_ok: whethere it is ok to symlink the file. Typically false in case the file
                            is used by daemons run in chroot environments (tftpd,..)
        :type   symlink_ok: bool

        :raises CX:         Cobbler Exception is raised in case file IO errors or of the remote file
                            could not be retrieved
        :return:            None
        """
        full_path = utils.find_kernel(d_file)

        if full_path is None:
            raise CX("File not found: %s, tried to copy to: %s" % (full_path, distro_dir))

        # Koan manages remote kernel/initrd itself, but for consistent PXE
        # configurations the synchronization is still necessary
        if not utils.file_is_remote(full_path):
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            utils.linkfile(full_path, dst, symlink_ok=symlink_ok, api=self.api, logger=self.logger)
        else:
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            utils.copyremotefile(full_path, dst, api=None, logger=self.logger)

    def copy_single_distro_files(self, d, dirtree, symlink_ok):
        """
        Copy the files needed for a single distro.

        :param d: The distro to copy.
        :param dirtree: This is the root where the images are located. The folder "images" gets automatically appended.
        :param symlink_ok: If it is okay to use a symlink to link the destination to the source.
        :type symlink_ok: bool
        """

        distros = os.path.join(dirtree, "images")
        distro_dir = os.path.join(distros, d.name)
        utils.mkdir(distro_dir)
        self.copy_single_distro_file(d.kernel, distro_dir, symlink_ok)
        self.copy_single_distro_file(d.initrd, distro_dir, symlink_ok)

    def copy_single_image_files(self, img):
        """
        Copies an image to the images directory of Cobbler.

        :param img: The image to copy.
        """
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
        """
        Writes all files for tftp for a given system with the menu items handed to this method. The system must have a
        profile attached. Otherwise this method throws an error.

        :param system: The system to generate files for.
        :param menu_items:
        """
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

        # hack: s390 generates files per system not per interface
        if not image_based and distro.arch.startswith("s390"):
            short_name = system.name.split('.')[0]
            s390_name = 'linux' + short_name[7:10]
            self.logger.info("Writing s390x pxe config for %s" % short_name)
            # Always write a system specific _conf and _parm file
            pxe_f = os.path.join(self.bootloc, "s390x", "s_%s" % s390_name)
            conf_f = "%s_conf" % pxe_f
            parm_f = "%s_parm" % pxe_f

            self.logger.info("Files: (conf,param) - (%s,%s)" % (conf_f, parm_f))
            blended = utils.blender(self.api, True, system)
            # FIXME: profiles also need this data!
            # gather default kernel_options and default kernel_options_s390x
            kernel_options = self.build_kernel_options(system, profile, distro,
                                                       image, "s390x", blended.get("autoinstall", ""))
            kopts_aligned = ""
            column = 0
            for option in kernel_options.split():
                opt_len = len(option)
                if opt_len > 78:
                    kopts_aligned += '\n' + option + ' '
                    column = opt_len + 1
                    self.logger.error("Kernel paramer [%s] too long %s" % (option, opt_len))
                    continue
                if column + opt_len > 78:
                    kopts_aligned += '\n' + option + ' '
                    column = opt_len + 1
                else:
                    kopts_aligned += option + ' '
                    column += opt_len + 1

            # Write system specific zPXE file
            if system.is_management_supported():
                if system.netboot_enabled:
                    self.logger.info("S390x: netboot_enabled")
                    kernel_path = os.path.join("/images", distro.name, os.path.basename(distro.kernel))
                    initrd_path = os.path.join("/images", distro.name, os.path.basename(distro.initrd))
                    with open(pxe_f, 'w') as out:
                        out.write(kernel_path + '\n' + initrd_path + '\n')
                    with open(parm_f, 'w') as out:
                        out.write(kopts_aligned)
                    # Write conf file with one newline in it if netboot is enabled
                    with open(conf_f, 'w') as out:
                        out.write('\n')
                else:
                    self.logger.info("S390x: netboot_disabled")
                    # Write empty conf file if netboot is disabled
                    open(conf_f, 'w').close()
            else:
                # ensure the files do exist
                self.logger.info("S390x: management not supported")
                utils.rmfile(pxe_f)
                utils.rmfile(conf_f)
                utils.rmfile(parm_f)
            self.logger.info("S390x: pxe: [%s], conf: [%s], parm: [%s]" % (pxe_f, conf_f, parm_f))

            return

        # generate one record for each described NIC ..
        for (name, interface) in list(system.interfaces.items()):

            pxe_name = system.get_config_filename(interface=name)
            grub_name = system.get_config_filename(interface=name, loader="grub")

            if pxe_name is not None:
                pxe_path = os.path.join(self.bootloc, "pxelinux.cfg", pxe_name)

            if grub_name is not None:
                grub_path = os.path.join(self.bootloc, "grub", "system", grub_name)

            if grub_path is None and pxe_path is None:
                self.logger.warning("invalid interface recorded for system (%s,%s)" % (system.name, name))
                continue

            if image_based:
                working_arch = image.arch
            else:
                working_arch = distro.arch

            if working_arch is None:
                raise CX("internal error, invalid arch supplied")

            # for tftp only ...
            if working_arch in ["i386", "x86", "x86_64", "arm", "aarch64", "ppc64le", "ppc64el", "standard"]:
                # ToDo: This is old, move this logic into item_system.get_config_filename()
                pass

            elif working_arch == "ppc" or working_arch == "ppc64":
                # Determine filename for system-specific bootloader config
                filename = "%s" % system.get_config_filename(interface=name).lower()
                # to inherit the distro and system's boot_loader values correctly
                blended_system = utils.blender(self.api, False, system)
                if blended_system["boot_loader"] == "pxelinux":
                    pass
                else:
                    pxe_path = os.path.join(self.bootloc, "etc", filename)
                    # Link to the yaboot binary
                    f3 = os.path.join(self.bootloc, "ppc", filename)
                    if os.path.lexists(f3):
                        utils.rmfile(f3)
                    os.symlink("../yaboot", f3)
            else:
                continue

            if system.is_management_supported():
                if not image_based:
                    if pxe_path:
                        self.write_pxe_file(pxe_path, system, profile, distro, working_arch, metadata=pxe_metadata)
                    if grub_path:
                        self.write_pxe_file(grub_path, system, profile, distro, working_arch, format="grub")
                        # Generate a link named after system to the mac file for easier lookup
                        link_path = os.path.join(self.bootloc, "grub", "system_link", system.name)
                        if os.path.exists(link_path):
                            utils.rmfile(link_path)
                        os.symlink(os.path.join("..", "system", grub_name), link_path)
                else:
                    self.write_pxe_file(pxe_path, system, None, None, working_arch, image=profile, metadata=pxe_metadata)
            else:
                # ensure the file doesn't exist
                utils.rmfile(pxe_path)
                if grub_path:
                    utils.rmfile(grub_path)

    def make_pxe_menu(self):
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
        self.templar.render(template_data, metadata, outfile)
        template_src.close()

        # Write the grub menu:
        for arch in utils.get_valid_archs():
            arch_menu_items = self.get_menu_items(arch)
            if(arch_menu_items['grub']):
                outfile = os.path.join(self.bootloc, "grub", "{0}_menu_items.cfg".format(arch))
                fd = open(outfile, "w+")
                fd.write(arch_menu_items['grub'])
                fd.close()

    def get_menu_items(self, arch: Optional[str] = None) -> dict:
        """
        Generates menu items for pxe and grub. Grub menu items are grouped into submenus by profile.

        :param arch: The processor architecture to generate the menu items for. (Optional)
        :returns: A dictionary with the pxe and grub menu items. It has the keys "pxe" and "grub".
        """
        # sort the profiles
        profile_list = [profile for profile in self.profiles]
        profile_list = sorted(profile_list, key=lambda profile: profile.name)
        if arch:
            profile_list = [profile for profile in profile_list if profile.get_arch() == arch]

        # sort the images
        image_list = [image for image in self.images]
        image_list = sorted(image_list, key=lambda image: image.name)

        # Build out menu items and append each to this master list, used for
        # the default menus:
        pxe_menu_items = ""
        grub_menu_items = ""

        # create a dict of menuentries : submenuentries for grub during the creation of the pxe menu
        submenus = {}
        for profile in profile_list:
            if not profile.enable_menu:
                # This profile has been excluded from the menu
                continue
            distro = profile.get_conceptual_parent()
            if distro not in submenus:
                submenus[distro] = []
            submenus[distro].append(profile)

            contents = self.write_pxe_file(
                filename=None,
                system=None, profile=profile, distro=distro, arch=distro.arch)
            if contents is not None:
                pxe_menu_items += contents + "\n"

        for distro in submenus:
            grub_menu_items += "submenu '{0}' --class gnu-linux --class gnu --class os {{\n".format(distro.name)
            for profile in submenus[distro]:
                grub_contents = self.write_pxe_file(
                    filename=None,
                    system=None, profile=profile, distro=distro, arch=distro.arch,
                    format="grub")
                if grub_contents is not None:
                    grub_menu_items += grub_contents + "\n"
            grub_menu_items += "}\n"

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

    def write_pxe_file(self, filename, system, profile, distro, arch: str, image=None, metadata=None,
                       format: str = "pxe") -> str:
        """
        Write a configuration file for the boot loader(s).

        More system-specific configuration may come in later, if so that would appear inside the system object in api.py
        Can be used for different formats, "pxe" (default) and "grub".

        :param filename: If present this writes the output into the giving filename. If not present this method just
                         returns the generated configuration.
        :param system: If you supply a system there are other templates used then when using only a profile/image/
                       distro.
        :param profile: The profile to generate the pxe-file for.
        :param distro: If you don't ship an image, this is needed. Otherwise this just supplies information needed for
                       the templates.
        :param arch: The processor architecture to generate the pxefile for.
        :param image: If you want to be able to deploy an image, supply this parameter.
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param format: May be "grub" or "pxe".
        :return: The generated filecontent for the required item.
        """

        if arch is None:
            raise CX("missing arch")

        if image and not os.path.exists(image.file):
            return None     # nfs:// URLs or something, can't use for TFTP

        if metadata is None:
            metadata = {}

        (rval, settings) = utils.input_string_or_dict(self.settings.to_dict())
        if rval:
            for key in list(settings.keys()):
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
            if format == "grub":
                if distro.remote_grub_kernel:
                    kernel_path = distro.remote_grub_kernel
                if distro.remote_grub_initrd:
                    initrd_path = distro.remote_grub_initrd

            if 'http' in distro.kernel and 'http' in distro.initrd:
                if not kernel_path:
                    kernel_path = distro.kernel
                if not initrd_path:
                    initrd_path = distro.initrd

            if not kernel_path:
                kernel_path = os.path.join("/images", distro.name, os.path.basename(distro.kernel))
            if not initrd_path:
                initrd_path = os.path.join("/images", distro.name, os.path.basename(distro.initrd))

            # Find the automatic installation file if we inherit from another profile
            if system:
                blended = utils.blender(self.api, True, system)
            else:
                blended = utils.blender(self.api, True, profile)
            autoinstall_path = blended.get("autoinstall", "")

            # update metadata with all known information this allows for more powerful templating
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
                    buffer += 'set system="{system}"\n'.format(system=system.name)
                else:
                    local = os.path.join(self.settings.boot_loader_conf_template_dir, "grublocal.template")
                    if os.path.exists(local):
                        template = local
            else:   # pxe
                if system.netboot_enabled:
                    template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem.template")

                    if arch == "ppc" or arch == "ppc64":
                        # to inherit the distro and system's boot_loader values correctly
                        blended_system = utils.blender(self.api, False, system)
                        if blended_system["boot_loader"] == "pxelinux":
                            template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_ppc.template")
                        else:
                            template = os.path.join(self.settings.boot_loader_conf_template_dir, "yaboot_ppc.template")
                    elif arch.startswith("arm"):
                        template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_arm.template")
                    elif distro and distro.os_version.startswith("esxi"):
                        # ESXi uses a very different pxe method, using more files than a standard automatic installation
                        # file and different options - so giving it a dedicated PXE template makes more sense than
                        # shoe-horning it into the existing templates
                        template = os.path.join(self.settings.boot_loader_conf_template_dir, "pxesystem_esxi.template")
                else:
                    # local booting on ppc requires removing the system-specific dhcpd.conf filename
                    if arch is not None and (arch == "ppc" or arch == "ppc64"):
                        # Disable yaboot network booting for all interfaces on the system
                        for (name, interface) in list(system.interfaces.items()):

                            filename = "%s" % system.get_config_filename(interface=name).lower()

                            # Remove symlink to the yaboot binary
                            f3 = os.path.join(self.bootloc, "ppc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)
                            f3 = os.path.join(self.bootloc, "etc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)

                        # Yaboot/OF doesn't support booting locally once you've booted off the network, so nothing left
                        # to do
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
        if arch == "ppc" or arch == "ppc64":
            # remove the prefix "append"
            # TODO: this looks like it's removing more than append, really not sure what's up here...
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
            if system.serial_device or system.serial_baud_rate:
                if system.serial_device:
                    serial_device = system.serial_device
                else:
                    serial_device = 0
                if system.serial_baud_rate:
                    serial_baud_rate = system.serial_baud_rate
                else:
                    serial_baud_rate = 115200

                if format == "pxe":
                    buffer += "serial %d %d\n" % (serial_device, serial_baud_rate)
                elif format == "grub":
                    buffer += "set serial_console=true\nset serial_baud={baud}\nset serial_line={device}\n".format(baud=serial_baud_rate, device=serial_device)

        # get the template
        if kernel_path is not None:
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()
        else:
            # this is something we can't PXE boot
            template_data = "\n"

        # save file and/or return results, depending on how called.
        buffer += self.templar.render(template_data, metadata, None)

        if filename is not None:
            self.logger.info("generating: %s" % filename)
            # This try-except is a work-around for the cases where 'open' throws
            # the FileNotFoundError for not apparent reason.
            try:
                with open(filename, "w") as fd:
                    fd.write(buffer)
            except FileNotFoundError as e:
                self.logger.error("Got \"{}\" while trying to write {}".format(e, filename))
                self.logger.error("Trying to write {} again after some delay.".format(filename))
                sleep(1)
                with open(filename, "w") as fd:
                    fd.write(buffer)
        return buffer

    def build_kernel_options(self, system, profile, distro, image, arch: str, autoinstall_path) -> str:
        """
        Builds the full kernel options line.

        :param system: The system to generate the kernel options for.
        :param profile: Although the system contains the profile please specify it explicitly here.
        :param distro: Although the profile contains the distribution please specify it explicitly here.
        :param image: The image to generate the kernel options for.
        :param arch: The processor architecture to generate the kernel options for.
        :param autoinstall_path: The autoinstallation path. Normally this will be a URL because you want to pass a link
                                 to an autoyast, preseed or kickstart file.
        :return: The generated kernel line options.
        """

        management_interface = None
        management_mac = None
        if system is not None:
            blended = utils.blender(self.api, False, system)
            # find the first management interface
            try:
                for intf in list(system.interfaces.keys()):
                    if system.interfaces[intf]["management"]:
                        management_interface = intf
                        if system.interfaces[intf]["mac_address"]:
                            management_mac = system.interfaces[intf]["mac_address"]
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
        kopts = utils.revert_strip_none(kopts)

        # SUSE and other distro specific kernel additions or modificatins
        utils.kopts_overwrite(system, distro, kopts, self.settings)

        # since network needs to be configured again (it was already in netboot) when kernel boots
        # and we choose to do it dinamically, we need to set 'ksdevice' to one of
        # the interfaces' MAC addresses in ppc systems.
        # ksdevice=bootif is not useful in yaboot, as the "ipappend" line is a pxe feature.
        if system and arch and (arch == "ppc" or arch == "ppc64"):
            for intf in list(system.interfaces.keys()):
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
        if autoinstall_path:

            # FIXME: need to make shorter rewrite rules for these URLs

            # changing http_server's server component to its IP address was intruduced with
            # https://github.com/cobbler/cobbler/commit/588756aa7aefc122310847d007becf3112647944
            # to shorten the message length for S390 systems.
            # On multi-homed cobbler servers, this can lead to serious problems when installing
            # systems in a dedicated isolated installation subnet:
            # - typically, $server is reachable by name (DNS resolution assumed) both during PXE
            #   install and during production, but via different IP addresses
            # - $http_server is explicitly constructed from $server
            # - the IP address for $server may resolv differently between cobbler server (production)
            #   and installing system
            # - using IP($http_server) below may need to set $server in a way that matches the installation
            #   network
            # - using $server for later repository access then will fail, because the installation address
            #   isn't reachable for production systems
            #
            # In order to make the revert less intrusive, it'll depend on a configuration setting
            if self.settings and self.settings.convert_server_to_ip:
                try:
                    httpserveraddress = socket.gethostbyname_ex(blended["http_server"])[2][0]
                except socket.gaierror:
                    httpserveraddress = blended["http_server"]
            else:
                httpserveraddress = blended["http_server"]

            URL_REGEX = "[a-zA-Z]*://.*"
            local_autoinstall_file = not re.match(URL_REGEX, autoinstall_path)
            if local_autoinstall_file:
                if system is not None:
                    autoinstall_path = "http://%s/cblr/svc/op/autoinstall/system/%s" % (httpserveraddress, system.name)
                else:
                    autoinstall_path = "http://%s/cblr/svc/op/autoinstall/profile/%s" \
                                       % (httpserveraddress, profile.name)

            if distro.breed is None or distro.breed == "redhat":

                append_line += " kssendmac"
                append_line = "%s inst.ks=%s" % (append_line, autoinstall_path)
                gpxe = blended["enable_gpxe"]
                if gpxe:
                    append_line = append_line.replace('ksdevice=bootif', 'ksdevice=${net0/mac}')
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, autoinstall_path)
                if management_mac and not distro.arch.startswith("s390"):
                    append_line += " netdevice=%s" % management_mac
            elif distro.breed == "debian" or distro.breed == "ubuntu":
                append_line = "%s auto-install/enable=true priority=critical netcfg/choose_interface=auto url=%s"\
                              % (append_line, autoinstall_path)
                if management_interface:
                    append_line += " netcfg/choose_interface=%s" % management_interface
            elif distro.breed == "freebsd":
                append_line = "%s ks=%s" % (append_line, autoinstall_path)

                # rework kernel options for debian distros
                translations = {'ksdevice': "interface", 'lang': "locale"}
                for k, v in list(translations.items()):
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
                    append_line = "append %s/xen.gz dom0_max_vcpus=2 dom0_mem=752M com1=115200,8n1 console=com1," \
                                  "vga --- %s/vmlinuz xencons=hvc console=hvc0 console=tty0 install answerfile=%s --- " \
                                  "%s/install.img" % (img_path, img_path, autoinstall_path, img_path)
                    return append_line
            elif distro.breed == "powerkvm":
                append_line += " kssendmac"
                append_line = "%s kvmp.inst.auto=%s" % (append_line, autoinstall_path)

        if distro is not None and (distro.breed in ["debian", "ubuntu"]):
            # Hostname is required as a parameter, the one in the preseed is not respected, so calculate if we have one
            # here.
            # We're trying: first part of FQDN in hostname field, then system name, then profile name.
            # In Ubuntu, this is at least used for the volume group name when using LVM.
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

            # At least for debian deployments configured for DHCP networking this values are not used, but specifying
            # here avoids questions
            append_line = "%s hostname=%s" % (append_line, hostname)
            append_line = "%s domain=%s" % (append_line, domain)

            # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
            # directory
            append_line = "%s suite=%s" % (append_line, distro.os_version)

        # append necessary kernel args for arm architectures
        if arch is not None and arch.startswith("arm"):
            append_line = "%s fixrtc vram=48M omapfb.vram=0:24M" % append_line

        # do variable substitution on the append line
        # promote all of the autoinstall_meta variables
        if "autoinstall_meta" in blended:
            blended.update(blended["autoinstall_meta"])
        append_line = self.templar.render(append_line, utils.flatten(blended), None)

        # For now console=ttySx,BAUDRATE are only set for systems
        # This could get enhanced for profile/distro via utils.blender (inheritance)
        # This also is architecture specific. E.g: Some ARM consoles need: console=ttyAMAx,BAUDRATE
        # I guess we need a serial_kernel_dev = param, that can be set to "ttyAMA" if needed.
        if system and arch == "x86_64":
            if system.serial_device or system.serial_baud_rate:
                if system.serial_device:
                    serial_device = system.serial_device
                else:
                    serial_device = 0
                if system.serial_baud_rate:
                    serial_baud_rate = system.serial_baud_rate
                else:
                    serial_baud_rate = 115200

                append_line = "%s console=ttyS%s,%s" % (append_line, serial_device, serial_baud_rate)

        # FIXME - the append_line length limit is architecture specific
        if len(append_line) >= 1023:
            self.logger.warning("warning: kernel option length exceeds 1023")

        return append_line

    def write_templates(self, obj, write_file: bool = False, path=None):
        """
        A semi-generic function that will take an object with a template_files dict {source:destiation}, and generate a
        rendered file. The write_file option allows for generating of the rendered output without actually creating any
        files.

        :param obj: The object to write the template files for.
        :param write_file: If the generated template should be written to the disk.
        :param path: TODO: A useless parameter?
        :return: A dict of the destination file names (after variable substitution is done) and the data in the file.
        """
        self.logger.info("Writing template files for %s" % obj.name)

        results = {}

        try:
            templates = obj.template_files
        except:
            return results

        blended = utils.blender(self.api, False, obj)

        if obj.COLLECTION_TYPE == "distro":
            if re.search("esxi[567]", obj.os_version) is not None:
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

        # FIXME: img_path and local_img_path should probably be moved up into the blender function to ensure they're
        #  consistently available to templates across the board.
        if blended["distro_name"]:
            blended['img_path'] = os.path.join("/images", blended["distro_name"])
            blended['local_img_path'] = os.path.join(self.bootloc, "images", blended["distro_name"])

        for template in list(templates.keys()):
            dest = templates[template]
            if dest is None:
                continue

            # Run the source and destination files through templar first to allow for variables in the path
            template = self.templar.render(template, blended, None).strip()
            dest = os.path.normpath(self.templar.render(dest, blended, None).strip())
            # Get the path for the destination output
            dest_dir = os.path.normpath(os.path.dirname(dest))

            # If we're looking for a single template, skip if this ones destination is not it.
            if path is not None and path != dest:
                continue

            # If we are writing output to a file, we allow files tobe written into the tftpboot directory, otherwise
            # force all templated configs into the rendered directory to ensure that a user granted cobbler privileges
            # via sudo can't overwrite arbitrary system files (This also makes cleanup easier).
            if os.path.isabs(dest_dir) and write_file:
                if dest_dir.find(self.bootloc) != 0:
                    raise CX(" warning: template destination (%s) is outside %s, skipping." % (dest_dir, self.bootloc))
            elif write_file:
                dest_dir = os.path.join(self.settings.webdir, "rendered", dest_dir)
                dest = os.path.join(dest_dir, os.path.basename(dest))
                if not os.path.exists(dest_dir):
                    utils.mkdir(dest_dir)

            # Check for problems
            if not os.path.exists(template):
                raise CX("template source %s does not exist" % template)
            elif write_file and not os.path.isdir(dest_dir):
                raise CX("template destination (%s) is invalid" % dest_dir)
            elif write_file and os.path.exists(dest):
                raise CX("template destination (%s) already exists" % dest)
            elif write_file and os.path.isdir(dest):
                raise CX("template destination (%s) is a directory" % dest)
            elif template == "" or dest == "":
                raise CX("either the template source or destination was blank (unknown variable used?)" % dest)

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

    def generate_gpxe(self, what: str, name: str) -> str:
        """
        Generate the gpxe files.

        :param what: either "profile" or "system". All other item types not valdi.
        :param name: The name of the profile or system.
        :return: The rendered template.
        """
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

        # For multi-arch distros, the distro name in distro_mirror may not contain the arch string, so we need to figure
        # out the path based on where the kernel is stored. We do this because some distros base future downloads on the
        # initial URL passed in, so all of the files need to be at this location (which is why we can't use the images
        # link, which just contains the kernel and initrd).
        distro_mirror_name = ''.join(distro.kernel.split('/')[-2:-1])

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
            # all of these use a standard kernel/initrd setup so they all use the same gPXE template
            template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                    "gpxe_%s_linux.template" % what.lower())
        elif distro.breed == 'vmware':
            if distro.os_version == 'esx4':
                # older ESX is pretty much RHEL, so it uses the standard kernel/initrd setup
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_linux.template" % what.lower())
            elif distro.os_version == 'esxi4':
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_esxi4.template" % what.lower())
            elif distro.os_version.startswith('esxi5'):
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_esxi5.template" % what.lower())
            elif distro.os_version.startswith('esxi6'):
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_esxi6.template" % what.lower())
            elif distro.os_version.startswith('esxi7'):
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_esxi7.template" % what.lower())
        elif distro.breed == 'freebsd':
            template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                    "gpxe_%s_freebsd.template" % what.lower())
        elif distro.breed == 'windows':
            template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                    "gpxe_%s_windows.template" % what.lower())

        if what == "system":
            if not netboot_enabled:
                template = os.path.join(self.settings.boot_loader_conf_template_dir,
                                        "gpxe_%s_local.template" % what.lower())

        if not template:
            return "# unsupported breed/os version"

        if not os.path.exists(template):
            return "# gpxe template not found for the %s named %s (filename=%s)" % (what, name, template)

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None)

    def generate_bootcfg(self, what: str, name: str) -> str:
        """
        Generate a bootcfg for a system of profile.

        :param what: The type for what the bootcfg is generated for. Must be "profile" or "system".
        :param name: The name of the item which the bootcfg should be generated for.
        :return: The fully rendered bootcfg as a string.
        """
        if what.lower() not in ("profile", "system"):
            return "# bootcfg is only valid for profiles and systems"

        distro = None
        if what == "profile":
            obj = self.api.find_profile(name=name)
            distro = obj.get_conceptual_parent()
        else:
            obj = self.api.find_system(name=name)
            distro = obj.get_conceptual_parent().get_conceptual_parent()

        # For multi-arch distros, the distro name in distro_mirror may not contain the arch string, so we need to figure
        # out the path based on where the kernel is stored. We do this because some distros base future downloads on the
        # initial URL passed in, so all of the files need to be at this location (which is why we can't use the images
        # link, which just contains the kernel and initrd).
        distro_mirror_name = ''.join(distro.kernel.split('/')[-2:-1])

        blended = utils.blender(self.api, False, obj)

        if distro.os_version.startswith("esxi"):
            with open(os.path.join(os.path.dirname(distro.kernel), 'boot.cfg')) as f:
                bootmodules = re.findall(r'modules=(.*)', f.read())
                for modules in bootmodules:
                    blended['esx_modules'] = modules.replace('/', '')

        autoinstall_meta = blended.get("autoinstall_meta", {})
        try:
            del blended["autoinstall_meta"]
        except:
            pass
        blended.update(autoinstall_meta)          # make available at top level

        blended['distro'] = distro_mirror_name

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_gpxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port, distro.name)
        else:
            blended['img_path'] = os.path.join("/images", distro.name)

        template = os.path.join(self.settings.boot_loader_conf_template_dir, "bootcfg_%s.template" % distro.os_version)
        if not os.path.exists(template):
            return "# boot.cfg template not found for the %s named %s (filename=%s)" % (what, name, template)

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None)

    def generate_script(self, what: str, objname: str, script_name) -> str:
        """
        Generate a script from a autoinstall script template for a given profile or system.

        :param what: The type for what the bootcfg is generated for. Must be "profile" or "system".
        :param objname: The name of the item which the bootcfg should be generated for.
        :param script_name: The name of the template which should be rendered for the system or profile.
        :return: The fully rendered script as a string.
        """
        if what == "profile":
            obj = self.api.find_profile(name=objname)
        elif what == "system":
            obj = self.api.find_system(name=objname)
        else:
            raise ValueError("\"what\" needs to be either \"profile\" or \"system\"!")

        if not validate_autoinstall_script_name(script_name):
            raise ValueError("\"script_name\" handed to generate_script was not valid!")

        if not obj:
            return "# \"%s\" named \"%s\" not found" % (what, objname)

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

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_gpxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port, distro.name)
        else:
            blended['img_path'] = os.path.join("/images", distro.name)

        scripts_root = "/var/lib/cobbler/scripts"
        template = os.path.normpath(os.path.join(scripts_root, script_name))
        if not template.startswith(scripts_root):
            return "# script template \"%s\" could not be found in the script root" % script_name
        if not os.path.exists(template):
            return "# script template \"%s\" not found" % script_name

        with open(template) as template_fh:
            template_data = template_fh.read()

        return self.templar.render(template_data, blended, None)
