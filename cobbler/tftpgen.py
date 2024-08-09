"""
Generate files provided by TFTP server based on Cobbler object tree.
This is the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
import os
import os.path
import pathlib
import re
import socket
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from cobbler import enums, grub, templar, utils
from cobbler.cexceptions import CX
from cobbler.enums import Archs, ImageTypes
from cobbler.utils import filesystem_helpers, input_converters
from cobbler.validate import validate_autoinstall_script_name

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image
    from cobbler.items.menu import Menu
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


class TFTPGen:
    """
    Generate files provided by TFTP server
    """

    def __init__(self, api: "CobblerAPI"):
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

    def copy_bootloaders(self, dest: str) -> None:
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in our settings file.
        """
        src = self.settings.bootloaders_dir
        dest = self.bootloc
        # Unfortunately using shutils copy_tree the dest directory must not exist, but we must not delete an already
        # partly synced /srv/tftp dir here. rsync is very convenient here, being very fast on an already copied folder.
        utils.subprocess_call(
            [
                "rsync",
                "-rpt",
                "--copy-links",
                "--exclude=.cobbler_postun_cleanup",
                f"{src}/",
                dest,
            ],
            shell=False,
        )
        src = self.settings.grubconfig_dir
        utils.subprocess_call(
            [
                "rsync",
                "-rpt",
                "--copy-links",
                "--exclude=README.grubconfig",
                f"{src}/",
                dest,
            ],
            shell=False,
        )

    def copy_images(self) -> None:
        """
        Like copy_distros except for images.
        """
        errors: List[CX] = []
        for i in self.images:
            try:
                self.copy_single_image_files(i)
            except CX as cobbler_exception:
                errors.append(cobbler_exception)
                self.logger.error(cobbler_exception.value)

    def copy_single_distro_file(
        self, d_file: str, distro_dir: str, symlink_ok: bool
    ) -> None:
        """
        Copy a single file (kernel/initrd) to distro's images directory

        :param d_file:     distro's kernel/initrd absolut or remote file path value
        :param distro_dir: directory (typically in {www,tftp}/images) where to copy the file
        :param symlink_ok: whethere it is ok to symlink the file. Typically false in case the file is used by daemons
                            run in chroot environments (tftpd,..)
        :raises FileNotFoundError: Raised in case no kernel was found.
        """
        full_path: Optional[str] = utils.find_kernel(d_file)

        if not full_path:
            full_path = utils.find_initrd(d_file)

        if full_path is None or not full_path:
            # Will raise if None or an empty str
            raise FileNotFoundError(
                f'No kernel found at "{d_file}", tried to copy to: "{distro_dir}"'
            )

        # Koan manages remote kernel/initrd itself, but for consistent PXE
        # configurations the synchronization is still necessary
        if not utils.file_is_remote(full_path):
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            filesystem_helpers.linkfile(self.api, full_path, dst, symlink_ok=symlink_ok)
        else:
            b_file = os.path.basename(full_path)
            dst = os.path.join(distro_dir, b_file)
            filesystem_helpers.copyremotefile(full_path, dst, api=None)

    def copy_single_distro_files(
        self, distro: "Distro", dirtree: str, symlink_ok: bool
    ):
        """
        Copy the files needed for a single distro.

        :param distro: The distro to copy.
        :param dirtree: This is the root where the images are located. The folder "images" gets automatically appended.
        :param symlink_ok: If it is okay to use a symlink to link the destination to the source.
        """
        distro_dir = os.path.join(dirtree, "images", distro.name)
        filesystem_helpers.mkdir(distro_dir)
        if distro.kernel:
            self.copy_single_distro_file(distro.kernel, distro_dir, symlink_ok)
        else:
            self.copy_single_distro_file(
                distro.remote_boot_kernel, distro_dir, symlink_ok
            )
        if distro.initrd:
            self.copy_single_distro_file(distro.initrd, distro_dir, symlink_ok)
        else:
            self.copy_single_distro_file(
                distro.remote_boot_initrd, distro_dir, symlink_ok
            )

    def copy_single_image_files(self, img: "Image"):
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
        filesystem_helpers.linkfile(self.api, filename, newfile)

    def _format_s390x_kernel_options(
        self,
        distro: Optional["Distro"],
        profile: Optional["Profile"],
        image: Optional["Image"],
        system: "System",
    ) -> str:
        blended = utils.blender(self.api, True, system)
        # FIXME: profiles also need this data!
        # gather default kernel_options and default kernel_options_s390x
        kernel_options = self.build_kernel_options(
            system,
            profile,
            distro,
            image,
            enums.Archs.S390X,
            blended.get("autoinstall", ""),
        )

        # parm file format is fixed to 80 chars per line.
        # All the lines are concatenated without spaces when being passed to the kernel.
        #
        # Recommendation: one parameter per line (ending with whitespace)
        #
        # NOTE: If a parameter is too long to fit into the 80 characters limit it can simply
        # be continued in the first column of the next line.
        #
        # https://www.debian.org/releases/stable/s390x/ch05s01.en.html
        # https://documentation.suse.com/sles/15-SP1/html/SLES-all/cha-zseries.html#sec-appdendix-parm-examples
        # https://wiki.ubuntu.com/S390X/InstallationGuide
        _parmfile_fixed_line_len = 79
        kopts_aligned = ""
        kopts = kernel_options.strip()
        # Only in case we have kernel options
        if kopts:
            for option in [
                kopts[i : i + _parmfile_fixed_line_len]
                for i in range(0, len(kopts), _parmfile_fixed_line_len)
            ]:
                # If chunk contains multiple parameters (separated by whitespaces)
                # then we put them in separated lines followed by whitespace
                kopts_aligned += option.replace(" ", " \n") + "\n"
        return kopts_aligned

    def _write_all_system_files_s390(
        self, distro: "Distro", profile: "Profile", image: "Image", system: "System"
    ) -> None:
        """
        Write all files for a given system to TFTP that is of the architecture of s390[x].

        Directory structure for netboot enabled systems:

        .. code-block::

           TFTP Directory/
               S390X/
                   s_<system_name>
                   s_<system_name>_conf
                   s_<system_name>_parm

        Directory structure for netboot disabled systems:

        .. code-block::

           TFTP Directory/
               S390X/
                   s_<system_name>_conf


        :param distro: The distro to generate the files for.
        :param profile: The profile to generate the files for.
        :param image: The image to generate the files for.
        :param system: The system to generate the files for.
        """
        short_name = system.name.split(".")[0]
        s390_name = "linux" + short_name[7:10]
        self.logger.info("Writing s390x pxe config for %s", short_name)
        # Always write a system specific _conf and _parm file
        pxe_f = os.path.join(self.bootloc, enums.Archs.S390X.value, f"s_{s390_name}")
        conf_f = f"{pxe_f}_conf"
        parm_f = f"{pxe_f}_parm"

        self.logger.info("Files: (conf,param) - (%s,%s)", conf_f, parm_f)

        # Write system specific zPXE file
        if system.is_management_supported():
            if system.netboot_enabled:
                self.logger.info("S390x: netboot_enabled")
                kernel_path = os.path.join(
                    "/images", distro.name, os.path.basename(distro.kernel)
                )
                initrd_path = os.path.join(
                    "/images", distro.name, os.path.basename(distro.initrd)
                )
                kopts = self._format_s390x_kernel_options(
                    distro, profile, image, system
                )
                with open(pxe_f, "w", encoding="UTF-8") as out:
                    out.write(kernel_path + "\n" + initrd_path + "\n")
                with open(parm_f, "w", encoding="UTF-8") as out:
                    out.write(kopts)
                # Write conf file with one newline in it if netboot is enabled
                with open(conf_f, "w", encoding="UTF-8") as out:
                    out.write("\n")
            else:
                self.logger.info("S390x: netboot_disabled")
                # Write empty conf file if netboot is disabled
                pathlib.Path(conf_f).touch()
        else:
            # ensure the files do exist
            self.logger.info("S390x: management not supported")
            filesystem_helpers.rmfile(pxe_f)
            filesystem_helpers.rmfile(conf_f)
            filesystem_helpers.rmfile(parm_f)
        self.logger.info(
            "S390x: pxe: [%s], conf: [%s], parm: [%s]", pxe_f, conf_f, parm_f
        )

    def write_all_system_files(
        self, system: "System", menu_items: Dict[str, Union[str, Dict[str, str]]]
    ) -> None:
        """
        Writes all files for tftp for a given system with the menu items handed to this method. The system must have a
        profile attached. Otherwise this method throws an error.

        Directory structure:

        .. code-block::

           TFTP Directory/
               pxelinux.cfg/
                   01-aa-bb-cc-dd-ee-ff
               grub/
                   system/
                       aa:bb:cc:dd:ee:ff
                   system_link/
                       <system_name>

        :param system: The system to generate files for.
        :param menu_items: The list of labels that are used for displaying the menu entry.
        """
        system_parent: Optional[
            Union["Profile", "Image"]
        ] = system.get_conceptual_parent()  # type: ignore
        if system_parent is None:
            raise CX(
                f"system {system.name} references a missing profile {system.profile}"
            )

        distro: Optional["Distro"] = system_parent.get_conceptual_parent()  # type: ignore
        # TODO: Check if we can do this with isinstance and without a circular import.
        if distro is None:
            if system_parent.COLLECTION_TYPE == "profile":
                raise CX(f"profile {system.profile} references a missing distro!")
            image: Optional["Image"] = system_parent  # type: ignore
            profile = None
        else:
            profile: Optional["Profile"] = system_parent  # type: ignore
            image = None

        pxe_metadata = {"menu_items": menu_items}

        # hack: s390 generates files per system not per interface
        if distro is not None and distro.arch in (enums.Archs.S390, enums.Archs.S390X):
            self._write_all_system_files_s390(distro, profile, image, system)  # type: ignore
            return

        # generate one record for each described NIC ..
        for (name, _) in system.interfaces.items():

            # Passing "pxe" here is a hack, but we need to make sure that
            # get_config_filename() will return a filename in the pxelinux
            # bootloader_format.
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
                self.logger.warning(
                    "invalid interface recorded for system (%s,%s)", system.name, name
                )
                continue

            if profile is None and image is not None:
                working_arch = image.arch
            elif distro is not None:
                working_arch = distro.arch
            else:
                raise ValueError("Arch could not be fetched!")

            # for tftp only ...
            if working_arch in [
                Archs.I386,
                Archs.X86_64,
                Archs.ARM,
                Archs.AARCH64,
                Archs.PPC,
                Archs.PPC64,
                Archs.PPC64LE,
                Archs.PPC64EL,
            ]:
                # ToDo: This is old, move this logic into item_system.get_config_filename()
                pass
            else:
                continue

            if system.is_management_supported():
                if image is None:
                    if pxe_path:
                        self.write_pxe_file(
                            pxe_path,
                            system,
                            profile,
                            distro,
                            working_arch,
                            metadata=pxe_metadata,  # type: ignore
                        )
                    if grub_path:
                        self.write_pxe_file(
                            grub_path,
                            system,
                            profile,
                            distro,
                            working_arch,
                            bootloader_format="grub",
                        )
                        # Generate a link named after system to the mac file for easier lookup
                        link_path = os.path.join(
                            self.bootloc, "grub", "system_link", system.name
                        )
                        filesystem_helpers.rmfile(link_path)
                        filesystem_helpers.mkdir(os.path.dirname(link_path))
                        os.symlink(os.path.join("..", "system", grub_name), link_path)  # type: ignore
                else:
                    self.write_pxe_file(
                        pxe_path,
                        system,
                        profile,
                        distro,
                        working_arch,
                        image=image,
                        metadata=pxe_metadata,  # type: ignore
                    )
            else:
                # ensure the file doesn't exist
                filesystem_helpers.rmfile(pxe_path)
                if grub_path:
                    filesystem_helpers.rmfile(grub_path)

    def _generate_system_file_s390x(
        self,
        distro: "Distro",
        profile: Optional["Profile"],
        image: Optional["Image"],
        system: "System",
        path: pathlib.Path,
    ) -> Optional[str]:
        short_name = system.name.split(".")[0]
        s390_name = "linux" + short_name[7:10]
        if path == pathlib.Path(f"/s390x/s_{s390_name}_conf"):
            return "\n" if system.netboot_enabled else ""
        if system.netboot_enabled:
            if path == pathlib.Path(f"/s390x/s_{s390_name}"):
                kernel_path = os.path.join(
                    "/images", distro.name, os.path.basename(distro.kernel)
                )
                initrd_path = os.path.join(
                    "/images", distro.name, os.path.basename(distro.initrd)
                )
                return kernel_path + "\n" + initrd_path + "\n"
            if path == pathlib.Path(f"/s390x/s_{s390_name}_parm"):
                return self._format_s390x_kernel_options(distro, profile, image, system)
        return None

    def generate_system_file(
        self,
        system: "System",
        path: pathlib.Path,
        metadata: Dict[str, Union[str, Dict[str, str]]],
    ) -> Optional[str]:
        """
        Generate a single file for a system if the file is related to the system.

        :param system: The system to generate the file for.
        :param path: The path to the file.
        :param metadata: Menu items and other metadata for the generator.
        :returns: The contents of the file or None if the system does not provide this file.
        """
        system_parent: Optional[
            Union["Profile", "Image"]
        ] = system.get_conceptual_parent()  # type: ignore
        if system_parent is None:
            raise CX(
                f"system {system.name} references a missing profile {system.profile}"
            )

        distro: Optional["Distro"] = system_parent.get_conceptual_parent()  # type: ignore
        # TODO: Check if we can do this with isinstance and without a circular import.
        if distro is None:
            if system_parent.COLLECTION_TYPE == "profile":
                raise CX(f"profile {system.profile} references a missing distro!")
            image: Optional["Image"] = system_parent  # type: ignore
            profile = None
        else:
            profile: Optional["Profile"] = system_parent  # type: ignore
            image = None

        if distro is not None and distro.arch in (Archs.S390, Archs.S390X):
            return self._generate_system_file_s390x(
                distro, profile, image, system, path
            )

        if profile is None and image is not None:
            working_arch = image.arch
        elif distro is not None:
            working_arch = distro.arch
        else:
            raise ValueError("Arch could not be fetched!")

        for (name, _) in system.interfaces.items():
            pxe_name = system.get_config_filename(interface=name, loader="pxe")
            if pxe_name and (
                path == pathlib.Path("/pxelinux.cfg", pxe_name)
                or path == pathlib.Path("/esxi/pxelinux.cfg", pxe_name)
            ):
                return self.write_pxe_file(
                    None,
                    system,
                    profile,
                    distro,
                    working_arch,
                    metadata=metadata,
                )
            grub_name = system.get_config_filename(interface=name, loader="grub")
            if grub_name and path == pathlib.Path("/grub/system", grub_name):
                return self.write_pxe_file(
                    None,
                    system,
                    profile,
                    distro,
                    working_arch,
                    bootloader_format="grub",
                )
            if path == pathlib.Path("/esxi/system", system.name, "boot.cfg"):
                # FIXME: generate_bootcfg shouldn't waste time searching for the system again
                return self.generate_bootcfg("system", system.name)

        return None

    def make_pxe_menu(self) -> Dict[str, Union[str, Dict[str, str]]]:
        """
        Generates pxe, ipxe and grub boot menus.
        """
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")

        timeout_action = "local"
        if default is not None and not isinstance(default, list):
            timeout_action = default.profile

        boot_menu: Dict[str, Union[Dict[str, str], str]] = {}
        metadata = self.get_menu_items()
        menu_items = metadata["menu_items"]
        menu_labels = metadata["menu_labels"]
        metadata["pxe_timeout_profile"] = timeout_action

        self._make_pxe_menu_pxe(metadata, menu_items, menu_labels, boot_menu)  # type: ignore
        self._make_pxe_menu_ipxe(metadata, menu_items, menu_labels, boot_menu)  # type: ignore
        self._make_pxe_menu_grub(boot_menu)
        return boot_menu

    def _make_pxe_menu_pxe(
        self,
        metadata: Dict[str, Union[str, Dict[str, str]]],
        menu_items: Dict[str, Any],
        menu_labels: Dict[str, Any],
        boot_menu: Dict[str, Union[Dict[str, str], str]],
    ) -> None:
        """
        Write the PXE menu

        :param metadata: The metadata dictionary that contains the metdata for the template.
        :param menu_items: The dictionary with the data for the menu.
        :param menu_labels: The dictionary with the labels that are shown in the menu.
        :param boot_menu: The dictionary which contains the PXE menu and its data.
        """
        metadata["menu_items"] = menu_items.get("pxe", "")
        metadata["menu_labels"] = menu_labels.get("pxe", "")
        outfile = os.path.join(self.bootloc, "pxelinux.cfg", "default")
        with open(
            os.path.join(
                self.settings.boot_loader_conf_template_dir, "pxe_menu.template"
            ),
            encoding="UTF-8",
        ) as template_src:
            template_data = template_src.read()
            boot_menu["pxe"] = self.templar.render(template_data, metadata, outfile)

    def _make_pxe_menu_ipxe(
        self,
        metadata: Dict[str, Union[str, Dict[str, str]]],
        menu_items: Dict[str, Any],
        menu_labels: Dict[str, Any],
        boot_menu: Dict[str, Union[Dict[str, str], str]],
    ) -> None:
        """
        Write the iPXE menu

        :param metadata: The metadata dictionary that contains the metdata for the template.
        :param menu_items: The dictionary with the data for the menu.
        :param menu_labels: The dictionary with the labels that are shown in the menu.
        :param boot_menu: The dictionary which contains the iPXE menu and its data.
        """
        if self.settings.enable_ipxe:
            metadata["menu_items"] = menu_items.get("ipxe", "")
            metadata["menu_labels"] = menu_labels.get("ipxe", "")
            outfile = os.path.join(self.bootloc, "ipxe", "default.ipxe")
            with open(
                os.path.join(
                    self.settings.boot_loader_conf_template_dir, "ipxe_menu.template"
                ),
                encoding="UTF-8",
            ) as template_src:
                template_data = template_src.read()
                boot_menu["ipxe"] = self.templar.render(
                    template_data, metadata, outfile
                )

    def _make_pxe_menu_grub(
        self, boot_menu: Dict[str, Union[Dict[str, str], str]]
    ) -> None:
        """
        Write the grub menu

        :param boot_menu: The dictionary which contains the GRUB menu and its data.
        """
        for arch in enums.Archs:
            arch_metadata = self.get_menu_items(arch)
            arch_menu_items = arch_metadata["menu_items"]

            boot_menu["grub"] = arch_menu_items
            outfile = (
                pathlib.Path(self.bootloc) / "grub" / f"{arch.value}_menu_items.cfg"
            )
            outfile.write_text(arch_menu_items.get("grub", ""), encoding="UTF-8")  # type: ignore

    def generate_pxe_menu(
        self, path: pathlib.Path, metadata: Dict[str, Union[str, Dict[str, str]]]
    ) -> Optional[str]:
        """
        Generate the requested menu file.

        :param path: Path to the menu file.
        :param metadata: Menu items and other metadata for the generator.
        """
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")

        timeout_action = "local"
        if default is not None and not isinstance(default, list):
            timeout_action = default.profile

        metadata["pxe_timeout_profile"] = timeout_action

        if path == pathlib.Path("/pxelinux.cfg/default") or path == pathlib.Path(
            "/esxi/pxelinux.cfg/default"
        ):
            return self._generate_pxe_menu_pxe(metadata)
        if self.settings.enable_ipxe and path == pathlib.Path("/ipxe/default.ipxe"):
            return self._generate_pxe_menu_ipxe(metadata)
        for arch in enums.Archs:
            arch_menu_path = pathlib.Path("/grub", f"{arch.value}_menu_items.cfg")
            if path == arch_menu_path:
                return self.get_menu_items(arch)["menu_items"].get("grub", "")  # type: ignore
        return None

    def _generate_pxe_menu_pxe(
        self,
        metadata: Dict[str, Union[str, Dict[str, str]]],
    ) -> str:
        """
        Generate the PXE menu

        :param metadata: The metadata dictionary that contains the metdata for the template.
        """
        metadata["menu_items"] = metadata["menu_items"].get("pxe", "")  # type: ignore
        metadata["menu_labels"] = metadata["menu_labels"].get("pxe", "")  # type: ignore
        with open(
            os.path.join(
                self.settings.boot_loader_conf_template_dir, "pxe_menu.template"
            ),
            encoding="UTF-8",
        ) as template_src:
            template_data = template_src.read()
            return self.templar.render(template_data, metadata, None)

    def _generate_pxe_menu_ipxe(
        self,
        metadata: Dict[str, Union[str, Dict[str, str]]],
    ) -> str:
        """
        Generate the IPXE menu

        :param metadata: The metadata dictionary that contains the metdata for the template.
        """
        metadata["menu_items"] = metadata["menu_items"].get("ipxe", "")  # type: ignore
        metadata["menu_labels"] = metadata["menu_labels"].get("ipxe", "")  # type: ignore
        with open(
            os.path.join(
                self.settings.boot_loader_conf_template_dir, "ipxe_menu.template"
            ),
            encoding="UTF-8",
        ) as template_src:
            template_data = template_src.read()
            return self.templar.render(template_data, metadata, None)

    def get_menu_items(
        self, arch: Optional[enums.Archs] = None
    ) -> Dict[str, Union[str, Dict[str, str]]]:
        """
        Generates menu items for pxe, ipxe and grub. Grub menu items are grouped into submenus by profile.

        :param arch: The processor architecture to generate the menu items for. (Optional)
        :returns: A dictionary with the pxe, ipxe and grub menu items. It has the keys from
                  utils.get_supported_system_boot_loaders().
        """
        return self.get_menu_level(None, arch)

    def _get_submenu_child(
        self,
        child: "Menu",
        arch: Optional[enums.Archs],
        boot_loaders: List[str],
        nested_menu_items: Dict[str, Any],
        menu_labels: Dict[str, Any],
    ) -> None:
        """
        Generate a single entry for a submenu.

        :param child: The child item to generate the entry for.
        :param arch: The architecture to generate the entry for.
        :param boot_loaders: The list of boot loaders to generate the entry for.
        :param nested_menu_items: The nested menu items.
        :param menu_labels: The list of labels that are used for displaying the menu entry.
        """
        temp_metadata = self.get_menu_level(child, arch)
        temp_items = temp_metadata["menu_items"]

        for boot_loader in boot_loaders:
            if boot_loader in temp_items:
                if boot_loader in nested_menu_items:
                    nested_menu_items[boot_loader] += temp_items[boot_loader]  # type: ignore
                else:
                    nested_menu_items[boot_loader] = temp_items[boot_loader]  # type: ignore

            if boot_loader not in menu_labels:
                menu_labels[boot_loader] = []

            if "ipxe" in temp_items:
                display_name = (
                    child.display_name
                    if child.display_name and child.display_name != ""
                    else child.name
                )
                menu_labels[boot_loader].append(
                    {
                        "name": child.name,
                        "display_name": display_name + " -> [submenu]",
                    }
                )

    def get_submenus(
        self,
        menu: Optional["Menu"],
        metadata: Dict[Any, Any],
        arch: Optional[enums.Archs],
    ):
        """
        Generates submenus metatdata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        if menu:
            childs = menu.children
        else:
            childs = self.api.find_menu(return_list=True, parent="")
        if childs is None:
            childs = []
        if not isinstance(childs, list):
            raise ValueError("children was expected to be a list!")
        childs.sort(key=lambda child: child.name)

        nested_menu_items: Dict[str, List[Dict[str, str]]] = {}
        menu_labels: Dict[str, List[Dict[str, str]]] = {}
        boot_loaders = utils.get_supported_system_boot_loaders()

        for child in childs:
            self._get_submenu_child(
                child, arch, boot_loaders, nested_menu_items, menu_labels  # type: ignore
            )

        metadata["menu_items"] = nested_menu_items
        metadata["menu_labels"] = menu_labels

    def _get_item_menu(
        self,
        arch: Optional[enums.Archs],
        boot_loader: str,
        current_menu_items: Dict[str, Any],
        menu_labels: Dict[str, Any],
        distro: Optional["Distro"] = None,
        profile: Optional["Profile"] = None,
        image: Optional["Image"] = None,
    ) -> None:
        """
        Common logic for generating both profile and image based menu entries.

        :param arch: The architecture to generate the entries for.
        :param boot_loader: The bootloader that the item menu is generated for.
        :param current_menu_items: The already generated menu items.
        :param menu_labels: The list of labels that are used for displaying the menu entry.
        :param distro: The distro to generate the entries for.
        :param profile: The profile to generate the entries for.
        :param image: The image to generate the entries for.
        """
        target_item = None
        if image is None:
            target_item = profile
        elif profile is None:
            target_item = image
        if target_item is None:
            raise ValueError(
                '"image" and "profile" are mutually exclusive arguments! At least one of both must be given!'
            )

        contents = self.write_pxe_file(
            filename=None,
            system=None,
            profile=profile,
            distro=distro,
            arch=arch,
            image=image,
            bootloader_format=boot_loader,
        )
        if contents and contents != "":
            if boot_loader not in current_menu_items:
                current_menu_items[boot_loader] = ""
            current_menu_items[boot_loader] += contents

            if boot_loader not in menu_labels:
                menu_labels[boot_loader] = []

            # iPXE Level menu
            if boot_loader == "ipxe":
                display_name = target_item.name
                if target_item.display_name and target_item.display_name != "":
                    display_name = target_item.display_name
                menu_labels["ipxe"].append(
                    {"name": target_item.name, "display_name": display_name}
                )

    def get_profiles_menu(
        self,
        menu: Optional["Menu"],
        metadata: Dict[str, Any],
        arch: Optional[enums.Archs],
    ):
        """
        Generates profiles metadata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        menu_name = ""
        if menu is not None:
            menu_name = menu.name
        profile_filter = {"menu": menu_name}
        if arch:
            profile_filter["arch"] = arch.value
        profile_list = self.api.find_profile(return_list=True, **profile_filter)  # type: ignore[reportArgumentType]
        if profile_list is None:
            profile_list = []
        if not isinstance(profile_list, list):
            raise ValueError("find_profile was expexted to return a list!")
        profile_list.sort(key=lambda profile: profile.name)

        current_menu_items: Dict[str, Any] = {}
        menu_labels = metadata["menu_labels"]

        for profile in profile_list:
            if not profile.enable_menu:
                # This profile has been excluded from the menu
                continue
            arch = None
            distro = profile.get_conceptual_parent()
            boot_loaders = profile.boot_loaders

            if distro:
                arch = distro.arch  # type: ignore

            for boot_loader in boot_loaders:
                if boot_loader not in profile.boot_loaders:
                    continue
                self._get_item_menu(
                    arch,  # type: ignore
                    boot_loader,
                    current_menu_items,
                    menu_labels,
                    distro=distro,  # type: ignore
                    profile=profile,
                    image=None,
                )

        metadata["menu_items"] = current_menu_items
        metadata["menu_labels"] = menu_labels

    def get_images_menu(
        self,
        menu: Optional["Menu"],
        metadata: Dict[str, Any],
        arch: Optional[enums.Archs],
    ) -> None:
        """
        Generates profiles metadata for pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param arch: The processor architecture to generate the menu items for. (Optional)
        """
        menu_name = ""
        if menu is not None:
            menu_name = menu.name
        image_filter = {"menu": menu_name}
        if arch:
            image_filter["arch"] = arch.value
        image_list = self.api.find_image(return_list=True, **image_filter)  # type: ignore[reportArgumentType]
        if image_list is None:
            image_list = []
        if not isinstance(image_list, list):
            raise ValueError("find_image was expexted to return a list!")
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
                    self._get_item_menu(
                        arch, boot_loader, current_menu_items, menu_labels, image=image
                    )

        metadata["menu_items"] = current_menu_items
        metadata["menu_labels"] = menu_labels

    def get_menu_level(
        self, menu: Optional["Menu"] = None, arch: Optional[enums.Archs] = None
    ) -> Dict[str, Union[str, Dict[str, str]]]:
        """
        Generates menu items for submenus, pxe, ipxe and grub.

        :param menu: The menu for which boot files are generated. (Optional)
        :param arch: The processor architecture to generate the menu items for. (Optional)
        :returns: A dictionary with the pxe and grub menu items. It has the keys from
                  utils.get_supported_system_boot_loaders().
        """
        metadata: Dict[str, Any] = {}
        metadata["parent_menu_name"] = "Cobbler"
        metadata["parent_menu_label"] = "Cobbler"
        template_data: Dict[str, Any] = {}
        boot_loaders = utils.get_supported_system_boot_loaders()

        if menu:
            parent_menu = menu.parent
            metadata["menu_name"] = menu.name
            metadata["menu_label"] = (
                menu.display_name
                if menu.display_name and menu.display_name != ""
                else menu.name
            )
            if parent_menu and parent_menu != "":
                metadata["parent_menu_name"] = parent_menu.name
                metadata["parent_menu_label"] = parent_menu.name
                if parent_menu.display_name and parent_menu.display_name != "":
                    metadata["parent_menu_label"] = parent_menu.display_name

        for boot_loader in boot_loaders:
            template = (
                pathlib.Path(self.settings.boot_loader_conf_template_dir)
                / f"{boot_loader}_submenu.template"
            )
            if template.exists():
                with open(template, encoding="UTF-8") as template_fh:
                    template_data[boot_loader] = template_fh.read()
            else:
                self.logger.warning(
                    'Template for building a submenu not found for bootloader "%s"! Submenu '
                    "structure thus missing for this bootloader.",
                    boot_loader,
                )

        self.get_submenus(menu, metadata, arch)
        nested_menu_items = metadata["menu_items"]
        self.get_profiles_menu(menu, metadata, arch)
        current_menu_items = metadata["menu_items"]
        self.get_images_menu(menu, metadata, arch)
        current_menu_items = metadata["menu_items"]

        menu_items: Dict[str, Any] = {}
        menu_labels = metadata["menu_labels"]
        line_pat = re.compile(r"^(.+)$", re.MULTILINE)
        line_sub = "\t\\g<1>"

        for boot_loader in boot_loaders:
            if (
                boot_loader not in nested_menu_items
                and boot_loader not in current_menu_items
            ):
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
                        menu_items[boot_loader] += (
                            "\n" + current_menu_items[boot_loader]
                        )
            else:
                if boot_loader in nested_menu_items:
                    menu_items[boot_loader] = nested_menu_items[boot_loader]
                if boot_loader in current_menu_items:
                    menu_items[boot_loader] += current_menu_items[boot_loader]
                # Indentation for nested pxe and grub menu items.
                if menu:
                    menu_items[boot_loader] = line_pat.sub(
                        line_sub, menu_items[boot_loader]
                    )

            if menu and boot_loader in template_data:
                metadata["menu_items"] = menu_items[boot_loader]
                if boot_loader in menu_labels:
                    metadata["menu_labels"] = menu_labels[boot_loader]
                menu_items[boot_loader] = self.templar.render(
                    template_data[boot_loader], metadata, None
                )
                if boot_loader == "ipxe":
                    menu_items[boot_loader] += "\n"
        metadata["menu_items"] = menu_items
        metadata["menu_labels"] = menu_labels
        return metadata

    def write_pxe_file(
        self,
        filename: Optional[str],
        system: Optional["System"],
        profile: Optional["Profile"],
        distro: Optional["Distro"],
        arch: Optional[Archs],
        image: Optional["Image"] = None,
        metadata: Optional[Dict[str, Union[str, Dict[str, str]]]] = None,
        bootloader_format: str = "pxe",
    ) -> str:
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
        :param bootloader_format: Can be any of those returned by utils.get_supported_system_boot_loaders().
        :return: The generated filecontent for the required item.
        """

        if arch is None:
            raise CX("missing arch")

        if image and not os.path.exists(image.file):
            # nfs:// URLs or something, can't use for TFTP
            return None  # type: ignore

        if metadata is None:
            metadata = {}

        boot_loaders = None
        if system:
            boot_loaders = system.boot_loaders
            metadata["menu_label"] = system.name
            metadata["menu_name"] = system.name
            if system.display_name and system.display_name != "":
                metadata["menu_label"] = system.display_name
        elif profile:
            boot_loaders = profile.boot_loaders
            metadata["menu_label"] = profile.name
            metadata["menu_name"] = profile.name
            if profile.display_name and profile.display_name != "":
                metadata["menu_label"] = profile.display_name
        elif image:
            boot_loaders = image.boot_loaders
            metadata["menu_label"] = image.name
            metadata["menu_name"] = image.name
            if image.display_name and image.display_name != "":
                metadata["menu_label"] = image.display_name
        if boot_loaders is None or bootloader_format not in boot_loaders:
            return None  # type: ignore

        settings = input_converters.input_string_or_dict(self.settings.to_dict())
        metadata.update(settings)  # type: ignore
        # ---
        # just some random variables
        buffer = ""

        template = os.path.join(
            self.settings.boot_loader_conf_template_dir, bootloader_format + ".template"
        )
        self.build_kernel(metadata, system, profile, distro, image, bootloader_format)  # type: ignore

        # generate the kernel options and append line:
        kernel_options = self.build_kernel_options(
            system, profile, distro, image, arch, metadata["autoinstall"]  # type: ignore
        )
        metadata["kernel_options"] = kernel_options

        if "initrd_path" in metadata:
            append_line = f"append initrd={metadata['initrd_path']}"
        else:
            append_line = "append "
        append_line = f"{append_line}{kernel_options}"
        if distro and distro.os_version.startswith("xenserver620"):
            append_line = f"{kernel_options}"
        metadata["append_line"] = append_line

        # store variables for templating
        if system:
            if (
                system.serial_device > -1
                or system.serial_baud_rate != enums.BaudRates.DISABLED
            ):
                if system.serial_device == -1:
                    serial_device = 0
                else:
                    serial_device = system.serial_device
                if system.serial_baud_rate == enums.BaudRates.DISABLED:
                    serial_baud_rate = 115200
                else:
                    serial_baud_rate = system.serial_baud_rate.value

                if bootloader_format == "pxe":
                    buffer += f"serial {serial_device:d} {serial_baud_rate:d}\n"
                elif bootloader_format == "grub":
                    buffer += "set serial_console=true\n"
                    buffer += f"set serial_baud={serial_baud_rate}\n"
                    buffer += f"set serial_line={serial_device}\n"

        # for esxi, generate bootcfg_path metadata
        # and write boot.cfg files for systems and pxe
        if distro and distro.os_version.startswith("esxi"):
            if system:
                if filename:
                    bootcfg_path = os.path.join(
                        "system", os.path.basename(filename), "boot.cfg"
                    )
                else:
                    bootcfg_path = os.path.join("system", system.name, "boot.cfg")
                # write the boot.cfg file in the bootcfg_path
                if bootloader_format == "pxe":
                    self._write_bootcfg_file("system", system.name, bootcfg_path)
                # make bootcfg_path available for templating
                metadata["bootcfg_path"] = bootcfg_path
            else:
                # menus do not work for esxi profiles. So we exit here
                return ""

        # get the template
        if metadata["kernel_path"] is not None:  # type: ignore
            with open(template, encoding="UTF-8") as template_fh:
                template_data = template_fh.read()
        else:
            # this is something we can't PXE boot
            template_data = "\n"

        # save file and/or return results, depending on how called.
        buffer += self.templar.render(template_data, metadata, None)

        if filename is not None:
            self.logger.info("generating: %s", filename)
            # Ensure destination path exists to avoid race condition
            if not os.path.exists(os.path.dirname(filename)):
                filesystem_helpers.mkdir(os.path.dirname(filename))
            with open(filename, "w", encoding="UTF-8") as pxe_file_fd:
                pxe_file_fd.write(buffer)
        return buffer

    def build_kernel(
        self,
        metadata: Dict[str, Any],
        system: "System",
        profile: "Profile",
        distro: "Distro",
        image: Optional["Image"] = None,
        boot_loader: str = "pxe",
    ):
        """
        Generates kernel and initrd metadata.

        :param metadata: Pass additional parameters to the ones being collected during the method.
        :param system: The system to generate the pxe-file for.
        :param profile: The profile to generate the pxe-file for.
        :param distro: If you don't ship an image, this is needed. Otherwise this just supplies information needed for
                       the templates.
        :param image: If you want to be able to deploy an image, supply this parameter.
        :param boot_loader: Can be any of those returned by utils.get_supported_system_boot_loaders().
        """
        kernel_path: Optional[str] = None
        initrd_path: Optional[str] = None
        img_path: Optional[str] = None

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

            if "http" in distro.kernel and "http" in distro.initrd:
                if not kernel_path:
                    kernel_path = distro.kernel
                if not initrd_path:
                    initrd_path = distro.initrd

            # ESXi: for templating pxe/ipxe, kernel_path is bootloader mboot.c32
            if distro.breed == "vmware" and distro.os_version.startswith("esxi"):
                kernel_path = os.path.join(img_path, "mboot.c32")

            if not kernel_path:
                kernel_path = os.path.join(img_path, os.path.basename(distro.kernel))
            if not initrd_path:
                initrd_path = os.path.join(img_path, os.path.basename(distro.initrd))
        else:
            # this is an image we are making available, not kernel+initrd
            if image.image_type == ImageTypes.DIRECT:
                kernel_path = os.path.join("/images2", image.name)
            elif image.image_type == ImageTypes.MEMDISK:
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

            if not utils.file_is_remote(kernel_path):  # type: ignore
                kernel_path = os.path.join(img_path, os.path.basename(kernel_path))  # type: ignore
            metadata["kernel_path"] = kernel_path

        metadata["initrd"] = self._generate_initrd(
            autoinstall_meta, kernel_path, initrd_path, boot_loader  # type: ignore
        )

        if boot_loader == "grub" and utils.file_is_remote(kernel_path):  # type: ignore
            metadata["kernel_path"] = grub.parse_grub_remote_file(kernel_path)  # type: ignore

    def build_kernel_options(
        self,
        system: Optional["System"],
        profile: Optional["Profile"],
        distro: Optional["Distro"],
        image: Optional["Image"],
        arch: enums.Archs,
        autoinstall_path: str,
    ) -> str:
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
                for intf in system.interfaces.keys():
                    if system.interfaces[intf].management:
                        management_interface = intf
                        if system.interfaces[intf].mac_address:
                            management_mac = system.interfaces[intf].mac_address
                        break
            except Exception:
                # just skip this then
                pass
        elif profile is not None:
            blended = utils.blender(self.api, False, profile)
        elif image is not None:
            blended = utils.blender(self.api, False, image)
        else:
            raise ValueError("Impossible to find object for kernel options")

        append_line = ""
        kopts: Dict[str, Any] = blended.get("kernel_options", {})
        kopts = utils.revert_strip_none(kopts)  # type: ignore

        # SUSE and other distro specific kernel additions or modifications
        if distro is not None:
            if system is None:
                utils.kopts_overwrite(kopts, self.settings.server, distro.breed)
            else:
                utils.kopts_overwrite(
                    kopts, self.settings.server, distro.breed, system.name
                )

        # support additional initrd= entries in kernel options.
        if "initrd" in kopts:
            append_line = f",{kopts.pop('initrd')}"
        hkopts = utils.dict_to_string(kopts)
        append_line = f"{append_line} {hkopts}"

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
                    httpserveraddress = socket.gethostbyname_ex(blended["http_server"])[
                        2
                    ][0]
                except socket.gaierror:
                    httpserveraddress = blended["http_server"]
            else:
                httpserveraddress = blended["http_server"]

            local_autoinstall_file = not re.match(r"[a-zA-Z]*://.*", autoinstall_path)
            protocol = self.settings.autoinstall_scheme
            if local_autoinstall_file:
                if system is not None:
                    autoinstall_path = f"{protocol}://{httpserveraddress}/cblr/svc/op/autoinstall/system/{system.name}"
                elif profile is not None:
                    autoinstall_path = (
                        f"{protocol}://{httpserveraddress}/"
                        f"cblr/svc/op/autoinstall/profile/{profile.name}"
                    )
                else:
                    raise ValueError("Neither profile nor system based!")

            if distro is None:
                raise ValueError("Distro for kernel command line not found!")

            if distro.breed == "redhat":

                if distro.os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
                    append_line += f" kssendmac ks={autoinstall_path}"
                    if blended["autoinstall_meta"].get("tree"):
                        append_line += f" repo={blended['autoinstall_meta']['tree']}"
                else:
                    append_line += f" inst.ks.sendmac inst.ks={autoinstall_path}"
                    if blended["autoinstall_meta"].get("tree"):
                        append_line += (
                            f" inst.repo={blended['autoinstall_meta']['tree']}"
                        )
                ipxe = blended["enable_ipxe"]
                if ipxe:
                    append_line = append_line.replace(
                        "ksdevice=bootif", "ksdevice=${net0/mac}"
                    )
            elif distro.breed == "suse":
                append_line = f"{append_line} autoyast={autoinstall_path}"
                if management_mac and distro.arch not in (
                    enums.Archs.S390,
                    enums.Archs.S390X,
                ):
                    append_line += f" netdevice={management_mac}"
            elif distro.breed in ("debian", "ubuntu"):
                append_line = (
                    f"{append_line}auto-install/enable=true priority=critical "
                    f"netcfg/choose_interface=auto url={autoinstall_path}"
                )
                if management_interface:
                    append_line += f" netcfg/choose_interface={management_interface}"
            elif distro.breed == "freebsd":
                append_line = f"{append_line} ks={autoinstall_path}"

                # rework kernel options for debian distros
                translations = {"ksdevice": "interface", "lang": "locale"}
                for key, value in translations.items():
                    append_line = append_line.replace(f"{key}=", f"{value}=")

                # interface=bootif causes a failure
                append_line = append_line.replace("interface=bootif", "")
            elif distro.breed == "vmware":
                if distro.os_version.find("esxi") != -1:
                    # ESXi is very picky, it's easier just to redo the
                    # entire append line here since
                    hkopts = utils.dict_to_string(kopts)
                    append_line = f"{hkopts} ks={autoinstall_path}"
                else:
                    append_line = f"{append_line} vmkopts=debugLogToSerial:1 mem=512M ks={autoinstall_path}"
                # interface=bootif causes a failure
                append_line = append_line.replace("ksdevice=bootif", "")
            elif distro.breed == "xen":
                if distro.os_version.find("xenserver620") != -1:
                    img_path = os.path.join("/images", distro.name)
                    append_line = (
                        f"append {img_path}/xen.gz dom0_max_vcpus=2 dom0_mem=752M com1=115200,8n1 console=com1,"
                        f"vga --- {img_path}/vmlinuz xencons=hvc console=hvc0 console=tty0 install"
                        f" answerfile={autoinstall_path} --- {img_path}/install.img"
                    )
                    return append_line
            elif distro.breed == "powerkvm":
                append_line += " kssendmac"
                append_line = f"{append_line} kvmp.inst.auto={autoinstall_path}"

        if distro is not None and (distro.breed in ["debian", "ubuntu"]):
            # Hostname is required as a parameter, the one in the preseed is not respected, so calculate if we have one
            # here.
            # We're trying: first part of FQDN in hostname field, then system name, then profile name.
            # In Ubuntu, this is at least used for the volume group name when using LVM.
            domain = "local.lan"
            if system is not None:
                if system.hostname != "":
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
                hostname = profile.name.replace("_", "")  # type: ignore

            # At least for debian deployments configured for DHCP networking this values are not used, but specifying
            # here avoids questions
            append_line = f"{append_line} hostname={hostname}"
            append_line = f"{append_line} domain={domain}"

            # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
            # directory
            append_line = f"{append_line} suite={distro.os_version}"

        # append necessary kernel args for arm architectures
        if arch is enums.Archs.ARM:
            append_line = f"{append_line} fixrtc vram=48M omapfb.vram=0:24M"

        # do variable substitution on the append line
        # promote all of the autoinstall_meta variables
        if "autoinstall_meta" in blended:
            blended.update(blended["autoinstall_meta"])
        append_line = self.templar.render(append_line, utils.flatten(blended), None)  # type: ignore

        # For now console=ttySx,BAUDRATE are only set for systems
        # This could get enhanced for profile/distro via utils.blender (inheritance)
        # This also is architecture specific. E.g: Some ARM consoles need: console=ttyAMAx,BAUDRATE
        # I guess we need a serial_kernel_dev = param, that can be set to "ttyAMA" if needed.
        if system and arch == Archs.X86_64:
            if (
                system.serial_device > -1
                or system.serial_baud_rate != enums.BaudRates.DISABLED
            ):
                if system.serial_device == -1:
                    serial_device = 0
                else:
                    serial_device = system.serial_device
                if system.serial_baud_rate == enums.BaudRates.DISABLED:
                    serial_baud_rate = 115200
                else:
                    serial_baud_rate = system.serial_baud_rate.value

                append_line = (
                    f"{append_line} console=ttyS{serial_device},{serial_baud_rate}"
                )

        # FIXME - the append_line length limit is architecture specific
        if len(append_line) >= 1023:
            self.logger.warning("warning: kernel option length exceeds 1023")

        return append_line

    def write_templates(
        self,
        obj: "BootableItem",
        write_file: bool = False,
        path: Optional[str] = None,
    ) -> Dict[str, str]:
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

        results: Dict[str, str] = {}

        try:
            templates = obj.template_files
        except Exception:
            return results

        blended = utils.blender(self.api, False, obj)

        if obj.COLLECTION_TYPE == "distro":  # type: ignore
            if re.search("esxi[567]", obj.os_version) is not None:  # type: ignore
                with open(
                    os.path.join(os.path.dirname(obj.kernel), "boot.cfg"),  # type: ignore
                    encoding="UTF-8",
                ) as realbootcfg_fd:
                    realbootcfg = realbootcfg_fd.read()
                bootmodules = re.findall(r"modules=(.*)", realbootcfg)
                for modules in bootmodules:
                    blended["esx_modules"] = modules.replace("/", "")

        # Make "autoinstall_meta" available at top level
        autoinstall_meta = blended.pop("autoinstall_meta", {})
        blended.update(autoinstall_meta)

        # Make "template_files" available at top level
        templates = blended.pop("template_files", {})
        blended.update(templates)

        templates = input_converters.input_string_or_dict_no_inherit(templates)

        # FIXME: img_path and local_img_path should probably be moved up into the blender function to ensure they're
        #  consistently available to templates across the board.
        if blended.get("distro_name", False):
            blended["img_path"] = os.path.join("/images", blended["distro_name"])
            blended["local_img_path"] = os.path.join(
                self.bootloc, "images", blended["distro_name"]
            )

        for template in templates.keys():
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

            # If we are writing output to a file, we allow files to be written into the tftpboot directory, otherwise
            # force all templated configs into the rendered directory to ensure that a user granted cobbler privileges
            # via sudo can't overwrite arbitrary system files (This also makes cleanup easier).
            if write_file and os.path.isabs(dest_dir):
                if not (
                    dest_dir.startswith(self.bootloc)
                    or dest.startswith(self.settings.webdir)
                ):
                    # Allow both the TFTP and web directory since template_files and boot_files were merged
                    raise CX(
                        f"warning: template destination ({dest_dir}) is outside {self.bootloc} or"
                        f" {self.settings.webdir}, skipping."
                    )
            elif write_file:
                dest_dir = os.path.join(self.settings.webdir, "rendered", dest_dir)
                dest = os.path.join(dest_dir, os.path.basename(dest))
                if not os.path.exists(dest_dir):
                    filesystem_helpers.mkdir(dest_dir)

            # Check for problems
            if not os.path.exists(template):
                self.logger.warning("template source %s does not exist", template)
                continue
            if write_file and not os.path.isdir(dest_dir):
                self.logger.warning("template destination (%s) is invalid", dest_dir)
                continue
            if write_file and os.path.exists(dest):
                self.logger.warning("template destination (%s) already exists", dest)
                continue
            if write_file and os.path.isdir(dest):
                self.logger.warning("template destination (%s) is a directory", dest)
                continue
            if template == "" or dest == "":
                self.logger.warning(
                    "either the template source or destination was blank (unknown variable used?)"
                )
                continue

            with open(template, encoding="UTF-8") as template_fh:
                template_data = template_fh.read()

            buffer = self.templar.render(template_data, blended, None)
            results[dest] = buffer

            if write_file:
                self.logger.info("generating: %s", dest)
                with open(dest, "w", encoding="UTF-8") as template_fd:
                    template_fd.write(buffer)

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

        distro: Optional["Distro"] = None
        image: Optional["Image"] = None
        profile: Optional["Profile"] = None
        system: Optional["System"] = None
        if what == "profile":
            profile = self.api.find_profile(name=name)  # type: ignore
            if profile:
                distro = profile.get_conceptual_parent()  # type: ignore
        elif what == "image":
            image = self.api.find_image(name=name)  # type: ignore
        else:
            system = self.api.find_system(name=name)  # type: ignore
            if system:
                profile = system.get_conceptual_parent()  # type: ignore
            if profile and profile.COLLECTION_TYPE == "profile":
                distro = profile.get_conceptual_parent()  # type: ignore
            else:
                image = profile  # type: ignore
                profile = None

        if distro:
            arch = distro.arch
        elif image:
            arch = image.arch
        else:
            return ""

        result = self.write_pxe_file(
            None, system, profile, distro, arch, image, bootloader_format="ipxe"
        )
        if not result:
            return ""
        result_split = result.splitlines(True)
        result_split[0] = "#!ipxe\n"
        return "".join(result_split)

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
            distro = obj.get_conceptual_parent()  # type: ignore
        else:
            obj = self.api.find_system(name=name)
            profile = obj.get_conceptual_parent()  # type: ignore
            distro = profile.get_conceptual_parent()  # type: ignore

        blended = utils.blender(self.api, False, obj)  # type: ignore

        if distro.os_version.startswith("esxi"):  # type: ignore
            with open(
                os.path.join(os.path.dirname(distro.kernel), "boot.cfg"),  # type: ignore
                encoding="UTF-8",
            ) as bootcfg_fd:
                bootmodules = re.findall(r"modules=(.*)", bootcfg_fd.read())
                for modules in bootmodules:
                    blended["esx_modules"] = modules.replace("/", "")

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_ipxe:  # type: ignore
            protocol = self.api.settings().autoinstall_scheme
            blended["img_path"] = (
                f"{protocol}://{self.settings.server}:{self.settings.http_port}/"
                f"cobbler/links/{distro.name}"  # type: ignore
            )
        else:
            blended["img_path"] = os.path.join("/images", distro.name)  # type: ignore

        # generate the kernel options:
        if what == "system":
            kopts = self.build_kernel_options(
                obj,  # type: ignore
                profile,  # type: ignore
                distro,  # type: ignore
                None,
                distro.arch,  # type: ignore
                blended.get("autoinstall", None),
            )
        elif what == "profile":
            kopts = self.build_kernel_options(
                None, obj, distro, None, distro.arch, blended.get("autoinstall", None)  # type: ignore
            )
        blended["kopts"] = kopts  # type: ignore
        blended["kernel_file"] = os.path.basename(distro.kernel)  # type: ignore

        template = os.path.join(
            self.settings.boot_loader_conf_template_dir, "bootcfg.template"
        )
        if not os.path.exists(template):
            return f"# boot.cfg template not found for the {what} named {name} (filename={template})"

        with open(template, encoding="UTF-8") as template_fh:
            template_data = template_fh.read()

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
            raise ValueError('"what" needs to be either "profile" or "system"!')

        if not validate_autoinstall_script_name(script_name):
            raise ValueError('"script_name" handed to generate_script was not valid!')

        if not obj or isinstance(obj, list):
            return f'# "{what}" named "{objname}" not found'

        distro: Optional["Distro"] = obj.get_conceptual_parent()  # type: ignore
        if distro is None or isinstance(distro, list):
            raise ValueError("Something is wrong!")
        while distro.get_conceptual_parent():  # type: ignore
            distro = distro.get_conceptual_parent()  # type: ignore

        blended = utils.blender(self.api, False, obj)

        # Promote autoinstall_meta to top-level
        autoinstall_meta = blended.pop("autoinstall_meta", {})
        blended.update(autoinstall_meta)

        # FIXME: img_path should probably be moved up into the blender function to ensure they're consistently
        #        available to templates across the board
        if obj.enable_ipxe:
            protocol = self.api.settings().autoinstall_scheme
            blended["img_path"] = (
                f"{protocol}://{self.settings.server}:{self.settings.http_port}/"
                f"cobbler/links/{distro.name}"  # type: ignore
            )
        else:
            blended["img_path"] = os.path.join("/images", distro.name)  # type: ignore

        scripts_root = "/var/lib/cobbler/scripts"
        template = os.path.normpath(os.path.join(scripts_root, script_name))
        if not template.startswith(scripts_root):
            return f'# script template "{script_name}" could not be found in the script root'
        if not os.path.exists(template):
            return f'# script template "{script_name}" not found'

        with open(template, encoding="UTF-8") as template_fh:
            template_data = template_fh.read()

        return self.templar.render(template_data, blended, None)

    def _build_windows_initrd(
        self, loader_name: str, custom_loader_name: str, bootloader_format: str
    ) -> str:
        """
        Generate a initrd metadata for Windows.

        :param loader_name: The loader name.
        :param custom_loader_name: The loader name in profile or system.
        :param bootloader_format: Can be any of those returned by get_supported_system_boot_loaders.
        :return: The fully generated initrd string for the bootloader.
        """
        initrd_line = custom_loader_name

        if bootloader_format == "ipxe":
            initrd_line = f"--name {loader_name} {custom_loader_name} {loader_name}"
        elif bootloader_format == "pxe":
            initrd_line = f"{custom_loader_name}@{loader_name}"
        elif bootloader_format == "grub":
            loader_path = custom_loader_name
            if utils.file_is_remote(loader_path):
                loader_path = grub.parse_grub_remote_file(custom_loader_name)  # type: ignore
            initrd_line = f"newc:{loader_name}:{loader_path}"

        return initrd_line

    def _generate_initrd(
        self,
        autoinstall_meta: Dict[Any, Any],
        kernel_path: str,
        initrd_path: str,
        bootloader_format: str,
    ) -> List[str]:
        """
        Generate a initrd metadata.

        :param autoinstall_meta: The kernel options.
        :param kernel_path: Path to the kernel.
        :param initrd_path: Path to the initrd.
        :param bootloader_format: Can be any of those returned by get_supported_system_boot_loaders.
        :return: The array of additional boot load files.
        """
        initrd: List[str] = []
        if "initrd" in autoinstall_meta:
            initrd = autoinstall_meta["initrd"]

        if kernel_path and "wimboot" in kernel_path:
            remote_boot_files = utils.file_is_remote(kernel_path)

            if remote_boot_files:
                protocol = self.api.settings().autoinstall_scheme
                loaders_path = (
                    f"{protocol}://@@http_server@@/cobbler/images/@@distro_name@@/"
                )
                initrd_path = f"{loaders_path}{os.path.basename(initrd_path)}"
            else:
                (loaders_path, _) = os.path.split(kernel_path)
                loaders_path += "/"

            bootmgr_path = bcd_path = wim_path = loaders_path

            if initrd_path:
                initrd.append(
                    self._build_windows_initrd(
                        "boot.sdi", initrd_path, bootloader_format
                    )
                )
            if "bootmgr" in autoinstall_meta:
                initrd.append(
                    self._build_windows_initrd(
                        "bootmgr.exe",
                        f'{bootmgr_path}{autoinstall_meta["bootmgr"]}',
                        bootloader_format,
                    )
                )
            if "bcd" in autoinstall_meta:
                initrd.append(
                    self._build_windows_initrd(
                        "bcd", f'{bcd_path}{autoinstall_meta["bcd"]}', bootloader_format
                    )
                )
            if "winpe" in autoinstall_meta:
                initrd.append(
                    self._build_windows_initrd(
                        autoinstall_meta["winpe"],
                        f'{wim_path}{autoinstall_meta["winpe"]}',
                        bootloader_format,
                    )
                )
        else:
            if initrd_path:
                initrd.append(initrd_path)

        return initrd

    def _write_bootcfg_file(self, what: str, name: str, filename: str) -> str:
        """
        Write a boot.cfg file for the ESXi boot loader(s), and create a symlink to
        esxi UEFI bootloaders (mboot.efi)

        Directory structure:

        .. code-block::

           TFTP Directory/
               esxi/
                   mboot.efi
                   system/
                       <system_name>/
                          boot.cfg
                          mboot.efi

        :param what: Either "profile" or "system". Profiles are not currently used.
        :param name: The name of the item which the file should be generated for.
        :param filename: relative boot.cfg path from tftp.
        :return: The generated filecontent for the required item.
        """

        if what.lower() not in ("profile", "system"):
            return "# only valid for profiles and systems"

        buffer = self.generate_bootcfg(what, name)
        bootloc_esxi = os.path.join(self.bootloc, "esxi")
        bootcfg_path = os.path.join(bootloc_esxi, filename)

        # write the boot.cfg file in tftp location
        self.logger.info("generating: %s", bootcfg_path)
        if not os.path.exists(os.path.dirname(bootcfg_path)):
            filesystem_helpers.mkdir(os.path.dirname(bootcfg_path))
        with open(bootcfg_path, "w", encoding="UTF-8") as bootcfg_path_fd:
            bootcfg_path_fd.write(buffer)

        # symlink to esxi UEFI bootloader in same dir as boot.cfg
        # based on https://stackoverflow.com/a/55741590
        if os.path.isfile(os.path.join(bootloc_esxi, "mboot.efi")):
            link_file = os.path.join(
                bootloc_esxi, os.path.dirname(filename), "mboot.efi"
            )
            while True:
                temp_link_file = os.path.join(
                    bootloc_esxi, os.path.dirname(filename), "mboot.efi.tmp"
                )
                try:
                    os.symlink("../../mboot.efi", temp_link_file)
                    break
                except FileExistsError:
                    pass
            try:
                os.replace(temp_link_file, link_file)
            except OSError as os_error:
                os.remove(temp_link_file)
                raise OSError(f"Error creating symlink {link_file}") from os_error

        return buffer

    def _read_chunk(
        self, path: Union[str, pathlib.Path], offset: int, size: int
    ) -> Tuple[bytes, int]:
        with open(path, "rb") as fd:
            fd.seek(offset)
            data = fd.read(size)
            file_size = fd.seek(0, os.SEEK_END)
            return data, file_size

    def _get_static_tftp_file(
        self, path: pathlib.Path, offset: int, size: int
    ) -> Optional[Tuple[bytes, int]]:
        relative_path = str(path).strip("/")
        try:
            return self._read_chunk(
                pathlib.Path(self.settings.bootloaders_dir, relative_path), offset, size
            )
        except FileNotFoundError:
            try:
                return self._read_chunk(
                    pathlib.Path(self.settings.grubconfig_dir, relative_path),
                    offset,
                    size,
                )
            except FileNotFoundError:
                return None

    def _get_distro_tftp_file(
        self, path: pathlib.Path, offset: int, size: int
    ) -> Optional[Tuple[bytes, int]]:
        if path.parts[1] != "images":
            distro_name = path.parts[3]
        else:
            distro_name = path.parts[2]
        distro = self.api.find_distro(distro_name, return_list=False)
        if isinstance(distro, list):
            raise ValueError("Expected a single distro, found a list")
        if distro is not None:
            kernel_path = pathlib.Path(distro.kernel)
            if path.name == kernel_path.name:
                return self._read_chunk(kernel_path, offset, size)
            initrd_path = pathlib.Path(distro.initrd)
            if path.name == initrd_path.name:
                return self._read_chunk(initrd_path, offset, size)
        return None

    def _generate_tftp_config_file(
        self, path: pathlib.Path, offset: int, size: int
    ) -> Optional[Tuple[bytes, int]]:
        metadata = self.get_menu_items()
        # TODO: This iterates through all systems for each request. Can this be optimized?
        contents = None
        for system in self.api.systems():
            if not system.is_management_supported():
                continue
            contents = self.generate_system_file(system, path, metadata)
            if contents is not None:
                break
        if contents is None:
            contents = self.generate_pxe_menu(path, metadata)
        if contents is not None:
            enc = contents.encode("UTF-8")
            return enc[offset : offset + size], len(enc)
        return None

    def generate_tftp_file(
        self, path: pathlib.Path, offset: int, size: int
    ) -> Tuple[bytes, int]:
        """
        Generate and return a file for a TFTP client.

        :param path: Normalized absolute path to the file
        :param offset: Offset of the requested chunk in the file
        :param size: Size of the requested chunk in the file
        :return: The requested chunk and the length of the whole file
        """
        static_file = self._get_static_tftp_file(path, offset, size)
        if static_file is not None:
            return static_file

        if (
            path.match("/images/*/*")
            or path.match("/grub/images/*/*")
            or path.match("/esxi/images/*/*")
        ):
            distro_file = self._get_distro_tftp_file(path, offset, size)
            if distro_file is not None:
                return distro_file
        elif path.match("/images2/*"):
            image = self.api.find_image(path.parts[2], return_list=False)
            if isinstance(image, list):
                raise ValueError("Expected a single image, found a list")
            if image is not None:
                return self._read_chunk(image.file, offset, size)
        elif path.match("/esxi/system/*/mboot.efi"):
            return self._read_chunk(
                pathlib.Path(self.settings.bootloaders_dir, "esxi/mboot.efi"),
                offset,
                size,
            )
        else:
            config_file = self._generate_tftp_config_file(path, offset, size)
            if config_file is not None:
                return config_file

        raise FileNotFoundError(path)
