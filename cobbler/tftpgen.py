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
import logging
import os
import os.path
import re
import socket
from typing import Dict, List, Optional

from cobbler import enums, templar, utils
from cobbler.cexceptions import CX
from cobbler.enums import Archs
from cobbler.validate import validate_autoinstall_script_name


class TFTPGen:
    """
    Generate files provided by TFTP server
    """

    def __init__(self, api):
        """
        Constructor
        """
        self.logger = logging.getLogger()
        self.api = api
        self.distros = api.distros()
        self.profiles = api.profiles()
        self.systems = api.systems()
        self.settings = api.settings()
        self.repos = api.repos()
        self.images = api.images()
        self.menus = api.menus()
        self.templar = templar.Templar(self.api)
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
            ["rsync", "-rpt", "--copy-links", "--exclude=.cobbler_postun_cleanup", "{src}/".format(src=src), dest],
            shell=False
        )
        src = self.settings.grubconfig_dir
        utils.subprocess_call(
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

    def copy_single_distro_file(self, d_file: str, distro_dir: str, symlink_ok: bool):
        """
        Copy a single file (kernel/initrd) to distro's images directory

        :param d_file:     distro's kernel/initrd absolut or remote file path value
        :param distro_dir: directory (typically in {www,tftp}/images) where to copy the file
        :param symlink_ok: whethere it is ok to symlink the file. Typically false in case the file is used by daemons
                            run in chroot environments (tftpd,..)
        :raises FileNotFoundError: Raised in case no kernel was found.
        """
        full_path = utils.find_kernel(d_file)

        if not full_path:
            full_path = utils.find_initrd(d_file)

        if full_path is None or not full_path:
            # Will raise if None or an empty str
            raise FileNotFoundError("No kernel found at \"%s\", tried to copy to: \"%s\"" % (d_file, distro_dir))

        # Koan manages remote kernel/initrd itself, but for consistent PXE
        # configurations the synchronization is still necessary
        if not utils.file_is_remote(full_path):
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            utils.linkfile(full_path, dst, symlink_ok=symlink_ok, api=self.api)
        else:
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            utils.copyremotefile(full_path, dst, api=None)

    def copy_single_distro_files(self, d, dirtree, symlink_ok: bool):
        """
        Copy the files needed for a single distro.

        :param d: The distro to copy.
        :param dirtree: This is the root where the images are located. The folder "images" gets automatically appended.
        :param symlink_ok: If it is okay to use a symlink to link the destination to the source.
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
        utils.linkfile(filename, newfile, api=self.api)

    def write_all_system_files(self, system, menu_items):
        """
        Writes all files for tftp for a given system with the menu items handed to this method. The system must have a
        profile attached. Otherwise this method throws an error.

        :param system: The system to generate files for.
        :param menu_items: TODO
        """
        profile = system.get_conceptual_parent()
        if profile is None:
            raise CX("system %(system)s references a missing profile %(profile)s" % {"system": system.name,
                                                                                     "profile": system.profile})

        distro = profile.get_conceptual_parent()
        image_based = False
        image = None
        if distro is None:
            if profile.COLLECTION_TYPE == "profile":
                raise CX("profile %(profile)s references a missing distro %(distro)s" % {"profile": system.profile,
                                                                                         "distro": profile.distro})
            else:
                image_based = True
                image = profile

        pxe_metadata = {'menu_items': menu_items}

        # hack: s390 generates files per system not per interface
        if not image_based and distro.arch in (enums.Archs.S390, enums.Archs.S390X):
            short_name = system.name.split('.')[0]
            s390_name = 'linux' + short_name[7:10]
            self.logger.info("Writing s390x pxe config for %s", short_name)
            # Always write a system specific _conf and _parm file
            pxe_f = os.path.join(self.bootloc, enums.Archs.S390X, "s_%s" % s390_name)
            conf_f = "%s_conf" % pxe_f
            parm_f = "%s_parm" % pxe_f

            self.logger.info("Files: (conf,param) - (%s,%s)", conf_f, parm_f)
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
            self.logger.info("S390x: pxe: [%s], conf: [%s], parm: [%s]", pxe_f, conf_f, parm_f)

            return

        # generate one record for each described NIC ..
        for (name, _) in list(system.interfaces.items()):

            # Passing "pxe" here is a hack, but we need to make sure that
            # get_config_filename() will return a filename in the pxelinux
            # format.
            pxe_name = system.get_config_filename(interface=name, loader="pxe")
            grub_name = system.get_config_filename(interface=name, loader="grub")

            if pxe_name is not None:
                pxe_path = os.path.join(self.bootloc, "pxelinux.cfg", pxe_name)
            else:
                pxe_path = ""

            if grub_name is not None:
                grub_path = os.path.join(self.bootloc, "grub", "system", grub_name)
            else:
                grub_path = ""

            if grub_path == "" and pxe_path == "":
                self.logger.warning("invalid interface recorded for system (%s,%s)", system.name, name)
                continue

            if image_based:
                working_arch = image.arch
            else:
                working_arch = distro.arch

            if working_arch is None:
                raise CX("internal error, invalid arch supplied")

            # for tftp only ...
            if working_arch in [Archs.I386, Archs.X86_64, Archs.ARM, Archs.AARCH64,
                                Archs.PPC, Archs.PPC64, Archs.PPC64LE, Archs.PPC64EL]:
                # ToDo: This is old, move this logic into item_system.get_config_filename()
                pass
            else:
                continue

            if system.is_management_supported():
                if not image_based:
                    if pxe_path:
                        self.write_pxe_file(pxe_path, system, profile, distro,
                                            working_arch, metadata=pxe_metadata)
                    if grub_path:
                        self.write_pxe_file(grub_path, system, profile, distro,
                                            working_arch, format="grub")
                        # Generate a link named after system to the mac file for easier lookup
                        link_path = os.path.join(self.bootloc, "grub", "system_link", system.name)
                        utils.rmfile(link_path)
                        utils.mkdir(os.path.dirname(link_path))
                        os.symlink(os.path.join("..", "system", grub_name), link_path)
                else:
                    self.write_pxe_file(pxe_path, system, None, None, working_arch, image=profile,
                                        metadata=pxe_metadata)
            else:
                # ensure the file doesn't exist
                utils.rmfile(pxe_path)
                if grub_path:
                    utils.rmfile(grub_path)

    def make_pxe_menu(self) -> Dict[str, str]:
        """
        Generates pxe, ipxe and grub boot menus.
        """
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")

        if default is None:
            timeout_action = "local"
        else:
            timeout_action = default.profile

        boot_menu = {}
        metadata = self.get_menu_items()
        loader_metadata = metadata
        menu_items = metadata["menu_items"]
        menu_labels = metadata["menu_labels"]
        loader_metadata["pxe_timeout_profile"] = timeout_action

        # Write the PXE menu:
        if 'pxe' in menu_items:
            loader_metadata["menu_items"] = menu_items['pxe']
            loader_metadata["menu_labels"] = {}
            outfile = os.path.join(self.bootloc, "pxelinux.cfg", "default")
            template_src = open(os.path.join(self.settings.boot_loader_conf_template_dir, "pxe_menu.template"))
            template_data = template_src.read()
            boot_menu['pxe'] = self.templar.render(template_data, loader_metadata, outfile)
            template_src.close()

        # Write the iPXE menu:
        if 'ipxe' in menu_items:
            loader_metadata["menu_items"] = menu_items['ipxe']
            loader_metadata["menu_labels"] = menu_labels['ipxe']
            outfile = os.path.join(self.bootloc, "ipxe", "default.ipxe")
            template_src = open(os.path.join(self.settings.boot_loader_conf_template_dir, "ipxe_menu.template"))
            template_data = template_src.read()
            boot_menu['ipxe'] = self.templar.render(template_data, loader_metadata, outfile)
            template_src.close()

        # Write the grub menu:
        for arch in enums.Archs:
            arch_metadata = self.get_menu_items(arch)
            arch_menu_items = arch_metadata["menu_items"]

            if 'grub' in arch_menu_items:
                boot_menu["grub"] = arch_menu_items
                outfile = os.path.join(self.bootloc, "grub", "{0}_menu_items.cfg".format(arch.value))
                with open(outfile, "w+") as fd:
                    fd.write(arch_menu_items["grub"])
        return boot_menu

    def get_menu_items(self, arch: Optional[enums.Archs] = None) -> dict:
        """
        Generates menu items for pxe, ipxe and grub. Grub menu items are grouped into submenus by profile.

        :param arch: The processor architecture to generate the menu items for. (Optional)
        :returns: A dictionary with the pxe, ipxe and grub menu items. It has the keys from
                  utils.get_supported_system_boot_loaders().
        """
        return self.get_menu_level(None, arch)

    def get_submenus(self, menu, metadata: dict, arch: enums.Archs):
        """
        Generates submenus metatdata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        if menu:
            child_names = menu.get_children(sort_list=True)
            childs = []
            for child in child_names:
                child = self.api.find_menu(name=child)
                if child is not None:
                    childs.append(child)
        else:
            childs = [child for child in self.menus if child.parent is None]

        nested_menu_items = {}
        menu_labels = {}
        boot_loaders = utils.get_supported_system_boot_loaders()

        for child in childs:
            temp_metadata = self.get_menu_level(child, arch)
            temp_items = temp_metadata["menu_items"]

            for boot_loader in boot_loaders:
                if boot_loader in temp_items:
                    if boot_loader in nested_menu_items:
                        nested_menu_items[boot_loader] += temp_items[boot_loader]
                    else:
                        nested_menu_items[boot_loader] = temp_items[boot_loader]

            if "ipxe" in temp_items:
                if "ipxe" not in menu_labels:
                    menu_labels["ipxe"] = []
                display_name = child.display_name if child.display_name and child.display_name != "" else child.name
                menu_labels["ipxe"].append({"name": child.name, "display_name": display_name})

        for boot_loader in boot_loaders:
            if boot_loader in nested_menu_items and nested_menu_items[boot_loader] != "":
                nested_menu_items[boot_loader] = nested_menu_items[boot_loader][:-1]

        metadata["menu_items"] = nested_menu_items
        metadata["menu_labels"] = menu_labels

    def get_profiles_menu(self, menu, metadata, arch: enums.Archs):
        """
        Generates profiles metadata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        if menu:
            profile_list = [profile for profile in self.profiles if profile.menu == menu.name]
        else:
            profile_list = [profile for profile in self.profiles if profile.menu is None or profile.menu == ""]
        profile_list = sorted(profile_list, key=lambda profile: profile.name)
        if arch:
            profile_list = [profile for profile in profile_list if profile.arch == arch]

        current_menu_items = {}
        menu_labels = metadata["menu_labels"]

        for profile in profile_list:
            if not profile.enable_menu:
                # This profile has been excluded from the menu
                continue
            arch = None
            distro = profile.get_conceptual_parent()
            boot_loaders = profile.boot_loaders

            if distro:
                arch = distro.arch

            for boot_loader in boot_loaders:
                if boot_loader not in profile.boot_loaders:
                    continue
                contents = self.write_pxe_file(filename=None, system=None, profile=profile, distro=distro, arch=arch,
                                               image=None, format=boot_loader)
                if contents and contents != "":
                    if boot_loader not in current_menu_items:
                        current_menu_items[boot_loader] = ""
                    current_menu_items[boot_loader] += contents

                    # iPXE Level menu
                    if boot_loader == "ipxe":
                        current_menu_items[boot_loader] += "\n"
                        if "ipxe" not in menu_labels:
                            menu_labels["ipxe"] = []
                        menu_labels["ipxe"].append({"name": profile.name, "display_name": profile.name})

        metadata["menu_items"] = current_menu_items
        metadata["menu_labels"] = menu_labels

    def get_images_menu(self, menu, metadata, arch: enums.Archs):
        """
        Generates profiles metadata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        if menu:
            image_list = [image for image in self.images if image.menu == menu.name]
        else:
            image_list = [image for image in self.images if image.menu is None or image.menu == ""]
        image_list = sorted(image_list, key=lambda image: image.name)

        current_menu_items = metadata["menu_items"]
        menu_labels = metadata["menu_labels"]

        # image names towards the bottom
        for image in image_list:
            if os.path.exists(image.file):
                arch = image.arch
                boot_loaders = image.boot_loaders

                for boot_loader in boot_loaders:
                    if boot_loader not in image.boot_loaders:
                        continue
                    contents = self.write_pxe_file(filename=None, system=None, profile=None, distro=None, arch=arch,
                                                   image=image, format=boot_loader)
                    if contents and contents != "":
                        if boot_loader not in current_menu_items:
                            current_menu_items[boot_loader] = ""
                        current_menu_items[boot_loader] += contents

                        # iPXE Level menu
                        if boot_loader == "ipxe":
                            current_menu_items[boot_loader] += "\n"
                            if "ipxe" not in menu_labels:
                                menu_labels["ipxe"] = []
                            menu_labels["ipxe"].append({"name": image.name, "display_name": image.name})

        boot_loaders = utils.get_supported_system_boot_loaders()
        for boot_loader in boot_loaders:
            if boot_loader in current_menu_items and current_menu_items[boot_loader] != "":
                current_menu_items[boot_loader] = current_menu_items[boot_loader][:-1]

        metadata["menu_items"] = current_menu_items
        metadata["menu_labels"] = menu_labels

    def get_menu_level(self, menu=None, arch: enums.Archs = None) -> dict:
        """
        Generates menu items for submenus, pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param arch: The processor architecture to generate the menu items for. (Optional)
        :returns: A dictionary with the pxe and grub menu items. It has the keys from
                  utils.get_supported_system_boot_loaders().
        """
        metadata = {}
        template_data = {}
        boot_loaders = utils.get_supported_system_boot_loaders()

        for boot_loader in boot_loaders:
            template = os.path.join(self.settings.boot_loader_conf_template_dir, "%s_submenu.template" % boot_loader)
            if os.path.exists(template):
                with open(template) as template_fh:
                    template_data[boot_loader] = template_fh.read()
                if menu:
                    parent_menu = menu.parent
                    metadata["menu_name"] = menu.name
                    metadata["menu_label"] = \
                        menu.display_name if menu.display_name and menu.display_name != "" else menu.name
                    if parent_menu:
                        metadata["parent_menu_name"] = parent_menu.name
                        if parent_menu.display_name and parent_menu.display_name != "":
                            metadata["parent_menu_label"] = parent_menu.display_name
                        else:
                            metadata["parent_menu_label"] = parent_menu.name
                    else:
                        metadata["parent_menu_name"] = "Cobbler"
                        metadata["parent menu_label"] = "Cobbler"
            else:
                self.logger.warning("Template for building a submenu not found for bootloader \"%s\"! Submenu "
                                    "structure thus missing for this bootloader.", boot_loader)

        self.get_submenus(menu, metadata, arch)
        nested_menu_items = metadata["menu_items"]
        self.get_profiles_menu(menu, metadata, arch)
        current_menu_items = metadata["menu_items"]
        self.get_images_menu(menu, metadata, arch)
        current_menu_items = metadata["menu_items"]

        menu_items = {}
        menu_labels = metadata["menu_labels"]
        line_pat = re.compile(r"^(.+)$", re.MULTILINE)
        line_sub = "\t\\g<1>"

        for boot_loader in boot_loaders:
            if boot_loader not in nested_menu_items and boot_loader not in current_menu_items:
                continue

            menu_items[boot_loader] = ""
            if boot_loader == "ipxe":
                if menu:
                    if boot_loader in current_menu_items:
                        menu_items[boot_loader] = current_menu_items[boot_loader]
                    if boot_loader in nested_menu_items:
                        menu_items[boot_loader] += nested_menu_items[boot_loader]
                else:
                    if boot_loader in nested_menu_items:
                        menu_items[boot_loader] = nested_menu_items[boot_loader]
                    if boot_loader in current_menu_items:
                        menu_items[boot_loader] += '\n' + current_menu_items[boot_loader]
            else:
                if boot_loader in nested_menu_items:
                    menu_items[boot_loader] = nested_menu_items[boot_loader]
                if boot_loader in current_menu_items:
                    if menu is None:
                        menu_items[boot_loader] += '\n'
                    menu_items[boot_loader] += current_menu_items[boot_loader]
                # Indentation for nested pxe and grub menu items.
                if menu:
                    menu_items[boot_loader] = line_pat.sub(line_sub, menu_items[boot_loader])

            if menu and boot_loader in template_data:
                metadata["menu_items"] = menu_items[boot_loader]
                if boot_loader in menu_labels:
                    metadata["menu_labels"] = menu_labels[boot_loader]
                menu_items[boot_loader] = self.templar.render(template_data[boot_loader], metadata, None)
                if boot_loader == "ipxe":
                    menu_items[boot_loader] += '\n'
        metadata["menu_items"] = menu_items
        metadata["menu_labels"] = menu_labels
        return metadata

    def write_pxe_file(self, filename, system, profile, distro, arch: Archs, image=None, metadata=None,
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
        :param format: Can be any of those returned by utils.get_supported_system_boot_loaders().
        :return: The generated filecontent for the required item.
        """

        if arch is None:
            raise CX("missing arch")

        if image and not os.path.exists(image.file):
            return None  # nfs:// URLs or something, can't use for TFTP

        if metadata is None:
            metadata = {}

        boot_loaders = None
        if system:
            boot_loaders = system.boot_loaders
            metadata["menu_label"] = system.name
            metadata["menu_name"] = system.name
        elif profile:
            boot_loaders = profile.boot_loaders
            metadata["menu_label"] = profile.name
            metadata["menu_name"] = profile.name
        elif image:
            boot_loaders = image.boot_loaders
            metadata["menu_label"] = image.name
            metadata["menu_name"] = image.name
        if boot_loaders is None or format not in boot_loaders:
            return None

        settings = utils.input_string_or_dict(self.settings.to_dict())
        metadata.update(settings)
        # ---
        # just some random variables
        buffer = ""

        template = os.path.join(self.settings.boot_loader_conf_template_dir, format + ".template")
        self.build_kernel(metadata, system, profile, distro, image, format)

        # generate the kernel options and append line:
        kernel_options = self.build_kernel_options(system, profile, distro,
                                                   image, arch, metadata["autoinstall"])
        metadata["kernel_options"] = kernel_options

        if distro and distro.os_version.startswith("esxi") and filename is not None:
            append_line = "BOOTIF=%s" % (os.path.basename(filename))
        elif "initrd_path" in metadata:
            append_line = "append initrd=%s" % (metadata["initrd_path"])
        else:
            append_line = "append "
        append_line = "%s%s" % (append_line, kernel_options)
        if distro and distro.os_version.startswith("xenserver620"):
            append_line = "%s" % (kernel_options)
        metadata["append_line"] = append_line

        # store variables for templating
        if system:
            if system.serial_device > -1 or system.serial_baud_rate != enums.BaudRates.DISABLED:
                if system.serial_device == -1:
                    serial_device = 0
                else:
                    serial_device = system.serial_device
                if system.serial_baud_rate == enums.BaudRates.DISABLED:
                    serial_baud_rate = 115200
                else:
                    serial_baud_rate = system.serial_baud_rate.value

                if format == "pxe":
                    buffer += "serial %d %d\n" % (serial_device, serial_baud_rate)
                elif format == "grub":
                    buffer += "set serial_console=true\nset serial_baud={baud}\nset serial_line={device}\n" \
                        .format(baud=serial_baud_rate, device=serial_device)

        # get the template
        if metadata["kernel_path"] is not None:
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()
        else:
            # this is something we can't PXE boot
            template_data = "\n"

        # save file and/or return results, depending on how called.
        buffer += self.templar.render(template_data, metadata, None)

        if filename is not None:
            self.logger.info("generating: %s", filename)
            # Ensure destination path exists to avoid race condition
            if not os.path.exists(os.path.dirname(filename)):
                utils.mkdir(os.path.dirname(filename))
            with open(filename, "w") as fd:
                fd.write(buffer)
        return buffer

    def build_kernel(self, metadata, system, profile, distro, image=None, boot_loader: str = "pxe"):
        """
        Generates kernel and initrd metadata.

        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param profile: The profile to generate the pxe-file for.
        :param distro: If you don't ship an image, this is needed. Otherwise this just supplies information needed for
                       the templates.
        :param image: If you want to be able to deploy an image, supply this parameter.
        :param boot_loader: Can be any of those returned by utils.get_supported_system_boot_loaders().
        """
        kernel_path = None
        initrd_path = None
        img_path = None

        # ---

        if system:
            blended = utils.blender(self.api, True, system)
            meta_blended = utils.blender(self.api, False, system)
        elif profile:
            blended = utils.blender(self.api, True, profile)
            meta_blended = utils.blender(self.api, False, profile)
        elif image:
            blended = utils.blender(self.api, True, image)
            meta_blended = utils.blender(self.api, False, image)
        else:
            blended = {}
            meta_blended = {}

        autoinstall_meta = meta_blended.get("autoinstall_meta", {})
        metadata.update(blended)

        if image is None:
            # not image based, it's something normalish
            img_path = os.path.join("/images", distro.name)
            if boot_loader in ["grub", "ipxe"]:
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
                kernel_path = os.path.join(img_path, os.path.basename(distro.kernel))
            if not initrd_path:
                initrd_path = os.path.join(img_path, os.path.basename(distro.initrd))
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

        if "img_path" not in metadata:
            metadata["img_path"] = img_path
        if "kernel_path" not in metadata:
            metadata["kernel_path"] = kernel_path
        if "initrd_path" not in metadata:
            metadata["initrd_path"] = initrd_path

        if "kernel" in autoinstall_meta:
            kernel_path = autoinstall_meta["kernel"]

            if not utils.file_is_remote(kernel_path):
                kernel_path = os.path.join(img_path, os.path.basename(kernel_path))
            metadata["kernel_path"] = kernel_path

        metadata["initrd"] = self._generate_initrd(autoinstall_meta, kernel_path, initrd_path, boot_loader)

    def build_kernel_options(self, system, profile, distro, image, arch: enums.Archs, autoinstall_path) -> str:
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

        # SUSE and other distro specific kernel additions or modifications
        if distro is not None:
            if system is None:
                utils.kopts_overwrite(kopts, self.settings.server, distro.breed)
            else:
                utils.kopts_overwrite(kopts, self.settings.server, distro.breed, system.name)

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
                ipxe = blended["enable_ipxe"]
                if ipxe:
                    append_line = append_line.replace('ksdevice=bootif', 'ksdevice=${net0/mac}')
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, autoinstall_path)
                if management_mac and distro.arch not in (enums.Archs.S390, enums.Archs.S390X):
                    append_line += " netdevice=%s" % management_mac
            elif distro.breed == "debian" or distro.breed == "ubuntu":
                append_line = "%s auto-install/enable=true priority=critical netcfg/choose_interface=auto url=%s" \
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
                                  "vga --- %s/vmlinuz xencons=hvc console=hvc0 console=tty0 install answerfile=%s ---" \
                                  " %s/install.img" % (img_path, img_path, autoinstall_path, img_path)
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
        if arch is enums.Archs.ARM:
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
        if system and arch == Archs.X86_64:
            if system.serial_device > -1 or system.serial_baud_rate != enums.BaudRates.DISABLED:
                if system.serial_device == -1:
                    serial_device = 0
                else:
                    serial_device = system.serial_device
                if system.serial_baud_rate == enums.BaudRates.DISABLED:
                    serial_baud_rate = 115200
                else:
                    serial_baud_rate = system.serial_baud_rate.value

                append_line = "%s console=ttyS%s,%s" % (append_line, serial_device, serial_baud_rate)

        # FIXME - the append_line length limit is architecture specific
        if len(append_line) >= 1023:
            self.logger.warning("warning: kernel option length exceeds 1023")

        return append_line

    def write_templates(self, obj, write_file: bool = False, path=None) -> Dict[str, str]:
        """
        A semi-generic function that will take an object with a template_files dict {source:destiation}, and generate a
        rendered file. The write_file option allows for generating of the rendered output without actually creating any
        files.

        :param obj: The object to write the template files for.
        :param write_file: If the generated template should be written to the disk.
        :param path: TODO: A useless parameter?
        :return: A dict of the destination file names (after variable substitution is done) and the data in the file.
        """
        self.logger.info("Writing template files for %s", obj.name)

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
        blended.update(autoinstall_meta)  # make available at top level

        templates = blended.get("template_files", {})
        try:
            del blended["template_files"]
        except:
            pass
        blended.update(templates)  # make available at top level

        templates = utils.input_string_or_dict(templates)

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
                raise CX("either the template source or destination was blank (unknown variable used?)")

            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()

            buffer = self.templar.render(template_data, blended, None)
            results[dest] = buffer

            if write_file:
                self.logger.info("generating: %s", dest)
                fd = open(dest, "w")
                fd.write(buffer)
                fd.close()

        return results

    def generate_ipxe(self, what: str, name: str) -> str:
        """
        Generate the ipxe files.

        :param what: Either "profile" or "system". All other item types not valid.
        :param name: The name of the profile or system.
        :return: The rendered template.
        """
        if what.lower() not in ("profile", "image", "system"):
            return "# ipxe is only valid for profiles, images and systems"

        distro = None
        image = None
        profile = None
        system = None
        if what == "profile":
            profile = self.api.find_profile(name=name)
            if profile:
                distro = profile.get_conceptual_parent()
        elif what == "image":
            image = self.api.find_image(name=name)
        else:
            system = self.api.find_system(name=name)
            if system:
                profile = system.get_conceptual_parent()
            if profile and profile.COLLECTION_TYPE == "profile":
                distro = profile.get_conceptual_parent()
            else:
                image = profile
                profile = None

        if distro:
            arch = distro.arch
        elif image:
            arch = image.arch
        else:
            return ""

        result = self.write_pxe_file(None, system, profile, distro, arch, image, format='ipxe')
        return "" if not result else result

    def generate_bootcfg(self, what: str, name: str) -> str:
        """
        Generate a bootcfg for a system of profile.

        :param what: The type for what the bootcfg is generated for. Must be "profile" or "system".
        :param name: The name of the item which the bootcfg should be generated for.
        :return: The fully rendered bootcfg as a string.
        """
        if what.lower() not in ("profile", "system"):
            return "# bootcfg is only valid for profiles and systems"

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
        blended.update(autoinstall_meta)  # make available at top level

        blended['distro'] = distro_mirror_name

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_ipxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port,
                                                                     distro.name)
        else:
            blended['img_path'] = os.path.join("/images", distro.name)

        template = os.path.join(self.settings.boot_loader_conf_template_dir, "bootcfg.template")
        if not os.path.exists(template):
            return "# boot.cfg template not found for the %s named %s (filename=%s)" % (what, name, template)

        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        return self.templar.render(template_data, blended, None)

    def generate_script(self, what: str, objname: str, script_name: str) -> str:
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
        blended.update(autoinstall_meta)  # make available at top level

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_ipxe:
            blended['img_path'] = 'http://%s:%s/cobbler/links/%s' % (self.settings.server, self.settings.http_port,
                                                                     distro.name)
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

    def _build_windows_initrd(self, loader_name: str, custom_loader_name: str, format: str) -> str:
        """
        Generate a initrd metadata for Windows.

        :param loader_name: The loader name.
        :param custom_loader_name: The loader name in profile or system.
        :param format: Can be any of those returned by get_supported_system_boot_loaders.
        :return: The fully generated initrd string for the boot loader.
        """
        initrd_line = custom_loader_name

        if format == "ipxe":
            initrd_line = "--name " + loader_name + " " + custom_loader_name + " " + loader_name

        return initrd_line

    def _generate_initrd(self, autoinstall_meta: dict, kernel_path, initrd_path, format: str) -> List[str]:
        """
        Generate a initrd metadata.

        :param autoinstall_meta: The kernel options.
        :param kernel_path: Path to the kernel.
        :param initrd_path: Path to the initrd.
        :param format: Can be any of those returned by get_supported_system_boot_loaders.
        :return: The array of additional boot load files.
        """
        initrd = []
        if "initrd" in autoinstall_meta:
            initrd = autoinstall_meta["initrd"]

        if kernel_path and "wimboot" in kernel_path:
            remote_boot_files = utils.file_is_remote(kernel_path)

            if remote_boot_files:
                loaders_path = 'http://@@http_server@@/cobbler/images/@@distro_name@@/'
                initrd_path = loaders_path + os.path.basename(initrd_path)
            else:
                (loaders_path, kernel_name) = os.path.split(kernel_path)
                loaders_path += '/'

            bootmgr_path = bcd_path = wim_path = loaders_path

            if initrd_path:
                initrd.append(self._build_windows_initrd("boot.sdi", initrd_path, format))
            if "bootmgr" in autoinstall_meta:
                initrd.append(self._build_windows_initrd("bootmgr.exe", bootmgr_path + autoinstall_meta["bootmgr"],
                                                         format))
            if "bcd" in autoinstall_meta:
                initrd.append(self._build_windows_initrd("bcd", bcd_path + autoinstall_meta["bcd"], format))
            if "winpe" in autoinstall_meta:
                initrd.append(self._build_windows_initrd("winpe.wim", wim_path + autoinstall_meta["winpe"], format))
        else:
            if initrd_path:
                initrd.append(initrd_path)

        return initrd
