"""
Builds bootable CD images that have PXE-equivalent behavior for all Cobbler distros/profiles/systems currently in
memory.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
import os
import pathlib
import shutil
from typing import Dict, List, NamedTuple, Optional

from cobbler import templar, utils
from cobbler.enums import Archs


def add_remaining_kopts(kopts: dict) -> str:
    """Add remaining kernel_options to append_line
    :param kopts: The kernel options which are not present in append_line.
    :return: A single line with all kernel options from the dictionary in the string. Starts with a space.
    """
    append_line = [""]  # empty str to ensure the returned str starts with a space
    for option, args in kopts.items():
        if args is None:
            append_line.append(f"{option}")
            continue

        if not isinstance(args, list):
            args = [args]

        for arg in args:
            arg_str = format(arg)
            if " " in arg_str:
                arg_str = f'"{arg_str}"'
            append_line.append(f"{option}={arg_str}")

    return " ".join(append_line)


class BootFilesCopyset(NamedTuple):
    src_kernel: str
    src_initrd: str
    new_filename: str


class LoaderCfgsParts(NamedTuple):
    isolinux: List[str]
    bootfiles_copysets: List[BootFilesCopyset]


class BuildisoDirs(NamedTuple):
    root: pathlib.Path
    isolinux: pathlib.Path
    autoinstall: pathlib.Path
    repo: pathlib.Path


class Autoinstall(NamedTuple):
    config: str
    repos: List[str]


class BuildIso:
    """
    Handles conversion of internal state to the isolinux tree layout
    """

    def __init__(self, api):
        """Constructor which initializes things here. The collection manager pulls all other dependencies in.
        :param api: The API instance which holds all information about objects in Cobbler.
        """
        self.api = api
        self.distmap = {}
        self.distctr = 0
        self.logger = logging.getLogger()
        self.templar = templar.Templar(api)
        self.isolinuxdir = ""

        # grab the header from buildiso.header file
        self.iso_template = (
            pathlib.Path(self.api.settings().iso_template_dir)
            .joinpath("buildiso.template")
            .read_text()
        )
        self.isolinux_menuentry_template = (
            pathlib.Path(api.settings().iso_template_dir)
            .joinpath("isolinux_menuentry.template")
            .read_text(encoding="UTF-8")
        )

    def _copy_boot_files(
        self, kernel_path, initrd_path, destdir: str, new_filename: str = ""
    ):
        """Copy kernel/initrd to destdir with (optional) newfile prefix
        :param kernel_path: Path to a a distro's kernel.
        :param initrd_path: Path to a a distro's initrd.
        :param destdir: The destination directory.
        :param new_filename: The file new filename. Kernel and Initrd have different extensions to seperate them from
                             each another.
        """
        kernel_source = pathlib.Path(kernel_path)
        initrd_source = pathlib.Path(initrd_path)
        path_destdir = pathlib.Path(destdir)

        if new_filename:
            kernel_dest = str(path_destdir / f"{new_filename}.krn")
            initrd_dest = str(path_destdir / f"{new_filename}.img")
        else:
            kernel_dest = str(path_destdir / kernel_source.name)
            initrd_dest = str(path_destdir / initrd_source.name)

        utils.copyfile(str(kernel_source), kernel_dest)
        utils.copyfile(str(initrd_source), initrd_dest)

    def filter_profiles(self, selected_items: List[str] = None) -> list:
        """
        Return a list of valid profile objects selected from all profiles by name, or everything if ``selected_items``
        is empty.
        :param selected_items: A list of names to include in the returned list.
        :return: A list of valid profiles. If an error occurred this is logged and an empty list is returned.
        """
        if selected_items is None:
            selected_items = []
        return self.filter_items(self.api.profiles(), selected_items)

    def filter_items(self, all_objs, selected_items: List[str]) -> list:
        """Return a list of valid profile or system objects selected from all profiles or systems by name, or everything
        if selected_items is empty.
        :param all_objs: The collection of items to filter.
        :param selected_items: The list of names
        :raises ValueError: Second option that this error is raised
                            when the list of filtered systems or profiles is empty.
        :return: A list of valid profiles OR systems. If an error occurred this is logged and an empty list is returned.
        """
        # No profiles/systems selection is made, let's return everything.
        if len(selected_items) == 0:
            return all_objs

        filtered_objects = []
        for name in selected_items:
            item_object = all_objs.find(name=name)
            if item_object is not None:
                filtered_objects.append(item_object)
                selected_items.remove(name)

        for bad_name in selected_items:
            self.logger.warning('"%s" is not a valid profile or system', bad_name)

        if len(filtered_objects) == 0:
            raise ValueError("No valid systems or profiles were specified.")

        return filtered_objects

    def parse_distro(self, distro_name):
        """Find and return distro object.

        Raises ValueError if the distro is not found.
        """
        distro_obj = self.api.find_distro(name=distro_name)
        if distro_obj is None:
            raise ValueError(f"Distribution {distro_name} not found.")
        return distro_obj

    def parse_profiles(self, profiles, distro_obj):
        profile_names = utils.input_string_or_list_no_inherit(profiles)
        if profile_names:
            self.logger.debug("Checking that %s belong to distro %s", profiles, distro_obj.name)
            orphans = set(profile_names) - set(distro_obj.children)
            if len(orphans) > 0:
                raise ValueError(
                    "When building a standalone ISO, all --profiles must be"
                    " under --distro. Extra --profiles: {}".format(
                        ",".join(sorted(str(o for o in orphans)))
                    )
                )
            return self.filter_profiles(profile_names)
        else:
            return self.filter_profiles(distro_obj.children)

    def _copy_isolinux_files(self):
        """
        This method copies the required and optional files from syslinux into the directories we use for building the
        ISO.
        :param iso_distro: The distro (and thus architecture) to build the ISO for.
        :param buildisodir: The directory where the ISO is being built in.
        """
        self.logger.info("copying syslinux files")

        files_to_copy = [
            "isolinux.bin",
            "menu.c32",
            "chain.c32",
            "ldlinux.c32",
            "libcom32.c32",
            "libutil.c32",
        ]
        optional_files = ["ldlinux.c32", "libcom32.c32", "libutil.c32"]
        syslinux_folders = [
            pathlib.Path(self.api.settings().syslinux_dir),
            pathlib.Path(self.api.settings().syslinux_dir).joinpath("modules/bios/"),
            pathlib.Path("/usr/lib/syslinux/"),
            pathlib.Path("/usr/lib/ISOLINUX/"),
        ]

        # file_copy_success will be used to check for missing files
        file_copy_success: Dict[str, bool] = {
            f: False for f in files_to_copy if f not in optional_files
        }
        for syslinux_folder in syslinux_folders:
            if syslinux_folder.exists():
                for file_to_copy in files_to_copy:
                    source_file = syslinux_folder.joinpath(file_to_copy)
                    if source_file.exists():
                        utils.copyfile(
                            str(source_file),
                            os.path.join(self.isolinuxdir, file_to_copy),
                        )
                        file_copy_success[file_to_copy] = True

        unsuccessful_copied_files = [k for k, v in file_copy_success.items() if not v]
        if len(unsuccessful_copied_files) > 0:
            self.logger.error(
                'The following files were not found: "%s"',
                '", "'.join(unsuccessful_copied_files),
            )
            raise FileNotFoundError(
                "Required file(s) not found. Please check your syslinux installation"
            )

    def _render_isolinux_entry(
        self, append_line: str, menu_name: str, kernel_path: str, menu_indent: int = 0
    ) -> str:
        """Render a single isolinux.cfg menu entry."""
        return self.templar.render(
            self.isolinux_menuentry_template,
            out_path=None,
            search_table={
                "menu_name": menu_name,
                "kernel_path": kernel_path,
                "append_line": append_line.lstrip(),
                "menu_indent": menu_indent,
            },
            template_type="jinja2",
        )

    def calculate_grub_name(self, distro) -> str:
        """
        This function checks the bootloaders_formats in our settings and then checks if there is a match between the
        architectures and the distribution architecture.
        :param distro: The distribution to get the GRUB2 loader name for.
        """
        loader_formats = self.api.settings().bootloaders_formats
        grub_binary_names: Dict[str, str] = {}
        desired_arch = distro.arch

        for (loader_format, values) in loader_formats.items():
            name = values.get("binary_name", None)
            if name is not None:
                grub_binary_names[loader_format.lower()] = name

        if desired_arch in (Archs.PPC, Archs.PPC64, Archs.PPC64LE, Archs.PPC64EL):
            # GRUB can boot all Power architectures it supports via the following modules directory.
            return grub_binary_names["powerpc-ieee1275"]
        elif desired_arch == Archs.AARCH64:
            # GRUB has only one 64-bit variant it can boot, the name is different how we have named it in Cobbler.
            return grub_binary_names["arm64-efi"]
        elif desired_arch == Archs.ARM:
            # GRUB has only one 32-bit variant it can boot, the name is different how we have named it in Cobbler.
            return grub_binary_names["arm"]

        # Now we do the regular stuff: We map the beginning of the Cobbler arch and try to find suitable loaders.
        # We do want to drop "grub.0" always as it is not efi bootable.
        matches = {
            k: v
            for (k, v) in grub_binary_names.items()
            if k.startswith(desired_arch.value) and v != "grub.0"
        }

        if len(matches) == 0:
            raise ValueError(
                'No matches found for requested Cobbler Arch: "%s"'
                % str(desired_arch.value)
            )
        elif len(matches) == 1:
            return next(iter(matches.values()))
        raise ValueError(
            'Ambiguous matches for GRUB to Cobbler Arch mapping! Requested: "%s" Found: "%s"'
            % (str(desired_arch.value), str(matches.values()))
        )

    def _write_isolinux_cfg(
        self, cfg_parts: List[str], output_dir: pathlib.Path
    ) -> None:
        """Write isolinux.cfg.

        :param cfg_parts: List of str that is written to the config, joined by newlines.
        :param output_dir: pathlib.Path that the isolinux.cfg file is written into.
        """
        output_file = output_dir / "isolinux.cfg"
        self.logger.info("Writing %s", output_file)
        with open(output_file, "w") as f:
            f.write("\n".join(cfg_parts))

    def _prepare_buildisodir(self, buildisodir: str = "") -> str:
        """
        This validated the path and type of the buildiso directory and then (re-)creates the apropiate directories.
        :param buildisodir: The directory in which the build of the ISO takes place. If an empty string then the default
                            directory is used.
        :raises ValueError: In case the specified directory does not exist.
        :raises TypeError: In case the specified argument is not of type str.
        :return: The validated and normalized directory with appropriate subfolders provisioned.
        """
        if not isinstance(buildisodir, str):
            raise TypeError("buildisodir needs to be of type str!")
        if not buildisodir:
            buildisodir = self.api.settings().buildisodir
        else:
            if not os.path.isdir(buildisodir):
                raise ValueError("The --tempdir specified is not a directory")

            (_, buildisodir_tail) = os.path.split(os.path.normpath(buildisodir))
            if buildisodir_tail != "buildiso":
                buildisodir = os.path.join(buildisodir, "buildiso")

        self.logger.info('Deleting and recreating the buildisodir at "%s"', buildisodir)
        if os.path.exists(buildisodir):
            shutil.rmtree(buildisodir)
        os.makedirs(buildisodir)

        self.isolinuxdir = os.path.join(buildisodir, "isolinux")
        return buildisodir

    def create_buildiso_dirs(self, buildiso_root: str) -> BuildisoDirs:
        """Create directories in the buildiso root."""
        root = pathlib.Path(buildiso_root)
        isolinuxdir = root / "isolinux"
        autoinstalldir = root / "autoinstall"
        repodir = root / "repo_mirror"
        for d in [isolinuxdir, autoinstalldir, repodir]:
            d.mkdir(parents=True)

        return BuildisoDirs(
            root=root,
            isolinux=isolinuxdir,
            autoinstall=autoinstalldir,
            repo=repodir,
        )

    def _generate_iso(self, xorrisofs_opts: str, iso: str, buildisodir: str):
        """
        Build the final xorrisofs command which is then executed on the disk.
        :param xorrisofs_opts: The additional options for xorrisofs.
        :param iso: The name of the output iso.
        :param buildisodir: The directory in which we build the ISO.
        """
        running_on, _ = utils.os_release()
        if running_on in ("suse", "centos", "virtuozzo", "redhat"):
            isohdpfx_location = pathlib.Path(self.api.settings().syslinux_dir).joinpath(
                "isohdpfx.bin"
            )
        else:
            isohdpfx_location = pathlib.Path(self.api.settings().syslinux_dir).joinpath(
                "mbr/isohdpfx.bin"
            )
        efi_img_location = "grub/grub.efi"
        cmd_list = [
            "xorriso",
            "-as",
            "mkisofs",
            xorrisofs_opts,
            "-isohybrid-mbr",
            str(isohdpfx_location),
            "-c",
            "isolinux/boot.cat",
            "-b",
            "isolinux/isolinux.bin",
            "-no-emul-boot",
            "-boot-load-size",
            "4",
            "-boot-info-table",
            "-eltorito-alt-boot",
            "-e",
            efi_img_location,
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
            "-V",
            '"COBBLER_INSTALL"',
            "-o",
            iso,
            buildisodir,
        ]
        cmd = " ".join(cmd_list)

        xorrisofs_return_code = utils.subprocess_call(cmd, shell=True)
        if xorrisofs_return_code != 0:
            self.logger.error("xorrisofs failed with non zero exit code!")
            return

        self.logger.info("ISO build complete")
        self.logger.info("You may wish to delete: %s", buildisodir)
        self.logger.info("The output file is: %s", iso)
