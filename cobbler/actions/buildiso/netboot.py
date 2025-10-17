"""
This module contains the specific code to generate a network bootable ISO.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import pathlib
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from cobbler import utils
from cobbler.actions import buildiso
from cobbler.actions.buildiso import (
    BootFilesCopyset,
    BuildisoDirsPPC64LE,
    BuildisoDirsX86_64,
    LoaderCfgsParts,
    append_line,
)
from cobbler.enums import Archs
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.items.distro import Distro
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


class NetbootBuildiso(buildiso.BuildIso):
    """
    This class contains all functionality related to building network installation images.
    """

    def make_shorter(self, distname: str) -> str:
        """
        Return a short distro identifier which is basically an internal counter which is mapped via the real distro
        name.

        :param distname: The distro name to return an identifier for.
        :return: A short distro identifier
        """
        if distname in self.distmap:
            return self.distmap[distname]

        self.distctr += 1
        self.distmap[distname] = str(self.distctr)
        return str(self.distctr)

    def _generate_boot_loader_configs(
        self, profiles: List["Profile"], systems: List["System"], exclude_dns: bool
    ) -> LoaderCfgsParts:
        """Generate boot loader configuration.

        The configuration is placed as parts into a list. The elements expect to
        be joined by newlines for writing.

        :param profiles: List of profiles to prepare.
        :param systems: List of systems to prepare.
        :param exclude_dns: Used for system kernel cmdline.
        """
        loader_config_parts = LoaderCfgsParts([self.iso_template], [], [])
        loader_config_parts.isolinux.append("MENU SEPARATOR")

        self._generate_profiles_loader_configs(profiles, loader_config_parts)
        self._generate_systems_loader_configs(systems, exclude_dns, loader_config_parts)

        return loader_config_parts

    def _generate_profiles_loader_configs(
        self, profiles: List["Profile"], loader_cfg_parts: LoaderCfgsParts
    ) -> None:
        """Generate isolinux configuration for profiles.

        The passed in isolinux_cfg_parts list is changed in-place.

        :param profiles: List of profiles to prepare.
        :param isolinux_cfg_parts: Output parameter for isolinux configuration.
        :param bootfiles_copyset: Output parameter for bootfiles copyset.
        """
        for profile in profiles:
            isolinux, grub, to_copy = self._generate_profile_config(profile)
            loader_cfg_parts.isolinux.append(isolinux)
            loader_cfg_parts.grub.append(grub)
            loader_cfg_parts.bootfiles_copysets.append(to_copy)

    def _generate_profile_config(
        self, profile: "Profile"
    ) -> Tuple[str, str, BootFilesCopyset]:
        """Generate isolinux configuration for a single profile.

        :param profile: Profile object to generate the configuration for.
        """
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore[reportGeneralTypeIssues,assignment]
        if distro is None:
            raise ValueError("Distro of a Profile must not be None!")
        distroname = self.make_shorter(distro.name)
        data = utils.blender(self.api, False, profile)
        # SUSE uses 'textmode' instead of 'text'
        utils.kopts_overwrite(
            data["kernel_options"], self.api.settings().server, distro.breed
        )

        autoinstall_scheme = self.api.settings().autoinstall_scheme
        data["autoinstall"] = (
            f"{autoinstall_scheme}://{data['server']}:{data['http_port']}/cblr/svc/op/autoinstall/"
            f"profile/{profile.name}"
        )

        kernel_command_line = append_line.AppendLineBuilder(
            api=self.api, distro_name=distroname, data=data
        ).generate_profile(distro.breed, distro.os_version)
        kernel_path = f"/{distroname}.krn"
        initrd_path = f"/{distroname}.img"

        isolinux_cfg = self._render_isolinux_entry(
            kernel_command_line, menu_name=distro.name, kernel_path=kernel_path
        )
        grub_cfg = self._render_grub_entry(
            kernel_command_line,
            menu_name=distro.name,
            kernel_path=kernel_path,
            initrd_path=initrd_path,
        )
        return (
            isolinux_cfg,
            grub_cfg,
            BootFilesCopyset(distro.kernel, distro.initrd, distroname),
        )

    def _generate_systems_loader_configs(
        self,
        systems: List["System"],
        exclude_dns: bool,
        loader_cfg_parts: LoaderCfgsParts,
    ) -> None:
        """Generate isolinux configuration for systems.

        The passed in isolinux_cfg_parts list is changed in-place.

        :param systems: List of systems to prepare
        :param isolinux_cfg_parts: Output parameter for isolinux configuration.
        :param bootfiles_copyset: Output parameter for bootfiles copyset.
        """
        for system in systems:
            isolinux, grub, to_copy = self._generate_system_config(
                system, exclude_dns=exclude_dns
            )
            loader_cfg_parts.isolinux.append(isolinux)
            loader_cfg_parts.grub.append(grub)
            loader_cfg_parts.bootfiles_copysets.append(to_copy)

    def _generate_system_config(
        self, system: "System", exclude_dns: bool
    ) -> Tuple[str, str, BootFilesCopyset]:
        """Generate isolinux configuration for a single system.

        :param system: System object to generate the configuration for.
        :exclude_dns: Control if DNS configuration is part of the kernel cmdline.
        """
        profile = system.get_conceptual_parent()
        # FIXME: pass distro, it's known from CLI
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        if distro is None:
            raise ValueError("Distro of Profile may never be None!")
        distroname = self.make_shorter(distro.name)  # type: ignore

        data = utils.blender(self.api, False, system)
        autoinstall_scheme = self.api.settings().autoinstall_scheme
        data["autoinstall"] = (
            f"{autoinstall_scheme}://{data['server']}:{data['http_port']}/cblr/svc/op/autoinstall/"
            f"system/{system.name}"
        )

        kernel_command_line = append_line.AppendLineBuilder(
            api=self.api, distro_name=distroname, data=data
        ).generate_system(
            distro, system, exclude_dns  # type: ignore
        )
        kernel_path = f"/{distroname}.krn"
        initrd_path = f"/{distroname}.img"

        isolinux_cfg = self._render_isolinux_entry(
            kernel_command_line, menu_name=system.name, kernel_path=kernel_path
        )
        grub_cfg = self._render_grub_entry(
            kernel_command_line,
            menu_name=distro.name,  # type: ignore
            kernel_path=kernel_path,
            initrd_path=initrd_path,
        )

        return (
            isolinux_cfg,
            grub_cfg,
            BootFilesCopyset(distro.kernel, distro.initrd, distroname),  # type: ignore
        )

    def _copy_esp(self, esp_source: str, buildisodir: str):
        """Copy existing EFI System Partition into the buildisodir."""
        filesystem_helpers.copyfile(esp_source, buildisodir + "/efi")

    def run(
        self,
        iso: str = "autoinst.iso",
        buildisodir: str = "",
        profiles: Optional[List[str]] = None,
        xorrisofs_opts: str = "",
        distro_name: Optional[str] = None,
        systems: Optional[List[str]] = None,
        exclude_dns: bool = False,
        esp: Optional[str] = None,
        exclude_systems: bool = False,
        **kwargs: Any,
    ):
        """
        Generate a net-installer for a distribution.

        By default, the ISO includes all available systems and profiles. Specify
        ``profiles`` and ``systems`` to only include the selected systems and
        profiles. Both parameters can be provided at the same time.

        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles: The filter to generate the ISO only for selected profiles.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        :param distro_name: For detecting the architecture of the ISO.
                            If not provided, taken from first profile or system item
        :param systems: The filter to generate the ISO only for selected systems.
        :param exclude_dns: Whether the repositories have to be locally available or the internet is reachable.
        :param exclude_systems: Whether system entries should not be exported.
        """
        del kwargs  # just accepted for polymorphism

        distro_obj, profile_list, system_list = self.prepare_sources(
            distro_name, profiles, systems, exclude_systems
        )

        loader_config_parts = self._generate_boot_loader_configs(
            profile_list, system_list, exclude_dns
        )
        buildisodir = self._prepare_buildisodir(buildisodir)
        buildiso_dirs: Optional[Union[BuildisoDirsX86_64, BuildisoDirsPPC64LE]] = None
        distro_mirrordir = pathlib.Path(self.api.settings().webdir) / "distro_mirror"
        xorriso_func = None
        esp_location = ""

        if distro_obj.arch == Archs.X86_64:
            xorriso_func = self._xorriso_x86_64
            buildiso_dirs = self.create_buildiso_dirs_x86_64(buildisodir)

            # fill temporary directory with arch-specific binaries
            self._copy_isolinux_files()
            if esp:
                self.logger.info("esp=%s", esp)
                distro_esp: Optional[str] = esp
            else:
                try:
                    filesource = self._find_distro_source(
                        distro_obj.kernel, str(distro_mirrordir)
                    )
                    self.logger.info("filesource=%s", filesource)
                    distro_esp = self._find_esp(pathlib.Path(filesource))
                    self.logger.info("esp=%s", distro_esp)
                except ValueError:
                    distro_esp = None

            if distro_esp is not None:
                self._copy_esp(distro_esp, buildisodir)
            else:
                esp_location = self._create_esp_image_file(buildisodir)
                self._copy_grub_into_esp(esp_location, distro_obj.arch)

            self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)
            self._write_isolinux_cfg(
                loader_config_parts.isolinux, buildiso_dirs.isolinux
            )

        elif distro_obj.arch in (Archs.PPC, Archs.PPC64, Archs.PPC64LE, Archs.PPC64EL):
            xorriso_func = self._xorriso_ppc64le
            buildiso_dirs = self.create_buildiso_dirs_ppc64le(buildisodir)
            grub_bin = (
                pathlib.Path(self.api.settings().bootloaders_dir)
                / "grub"
                / "grub.ppc64le"
            )
            bootinfo_txt = self._render_bootinfo_txt(distro_obj.name)
            # fill temporary directory with arch-specific binaries
            filesystem_helpers.copyfile(
                str(grub_bin), str(buildiso_dirs.grub / "grub.elf")
            )

            self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)
            self._write_bootinfo(bootinfo_txt, buildiso_dirs.ppc)
        else:
            raise ValueError(
                "cobbler buildiso does not work for arch={distro_obj.arch}"
            )

        for copyset in loader_config_parts.bootfiles_copysets:
            self._copy_boot_files(
                copyset.src_kernel,
                copyset.src_initrd,
                str(buildiso_dirs.root),
                copyset.new_filename,
            )

        xorriso_func(xorrisofs_opts, iso, buildisodir, buildisodir + "/efi")
