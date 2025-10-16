"""
This module contains the specific code for generating standalone or airgapped ISOs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import itertools
import os
import pathlib
import re
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union

from cobbler import utils
from cobbler.actions import buildiso
from cobbler.actions.buildiso import (
    Autoinstall,
    BootFilesCopyset,
    LoaderCfgsParts,
    append_line,
)
from cobbler.enums import Archs
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.items.distro import Distro
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


CDREGEX = re.compile(r"^\s*url .*\n", re.IGNORECASE | re.MULTILINE)


class StandaloneBuildiso(buildiso.BuildIso):
    """
    This class contains all functionality related to building self-contained installation images.
    """

    def _write_autoinstall_cfg(
        self, data: Dict[str, Autoinstall], output_dir: pathlib.Path
    ):
        self.logger.info("Writing auto-installation config files")
        self.logger.debug(data)
        for file_name, autoinstall in data.items():
            (output_dir / f"{file_name}.cfg").write_text(
                autoinstall.config, encoding="UTF-8"
            )

    def _generate_descendant_config(
        self,
        descendant: Union["Profile", "System"],
        menu_indent: int,
        distro: "Distro",
        append_line: str,
    ) -> Tuple[str, str, BootFilesCopyset]:
        kernel_path = f"/{os.path.basename(distro.kernel)}"
        initrd_path = f"/{os.path.basename(distro.initrd)}"
        isolinux_cfg = self._render_isolinux_entry(
            append_line,
            menu_name=descendant.name,
            kernel_path=kernel_path,
            menu_indent=menu_indent,
        )
        grub_cfg = self._render_grub_entry(
            append_line,
            menu_name=distro.name,
            kernel_path=kernel_path,
            initrd_path=initrd_path,
        )
        return (
            isolinux_cfg,
            grub_cfg,
            BootFilesCopyset(distro.kernel, distro.initrd, ""),
        )

    def validate_repos(
        self, profile_name: str, repo_names: List[str], repo_mirrordir: pathlib.Path
    ):
        """Sanity checks for repos to sync.

        This function checks that repos are known to cobbler and have a local mirror directory.
        Raises ValueError if any repo fails the validation.
        """
        for repo_name in repo_names:
            repo_obj = self.api.find_repo(name=repo_name)
            if repo_obj is None or isinstance(repo_obj, list):
                raise ValueError(
                    f"Repository {repo_name}, referenced by {profile_name}, not found or ambiguous."
                )
            if not repo_obj.mirror_locally:
                raise ValueError(
                    f"Repository {repo_name} is not configured for local mirroring."
                )
            if not repo_mirrordir.joinpath(repo_name).exists():
                raise ValueError(
                    f"Local mirror directory missing for repository {repo_name}"
                )

    def _generate_item(
        self,
        descendant_obj: Union["Profile", "System"],
        distro_obj: "Distro",
        airgapped: bool,
        cfg_parts: LoaderCfgsParts,
        repo_mirrordir: pathlib.Path,
        autoinstall_data: Dict[str, Any],
    ):
        data: Dict[Any, Any] = utils.blender(self.api, False, descendant_obj)
        utils.kopts_overwrite(
            data["kernel_options"], self.api.settings().server, distro_obj.breed
        )

        name = descendant_obj.name
        config_args: Dict[str, Any] = {
            "descendant": descendant_obj,
            "distro": distro_obj,
            "append_line": append_line.AppendLineBuilder(
                self.api, "", {}
            ).generate_standalone(data, distro_obj, descendant_obj),
        }

        if descendant_obj.COLLECTION_TYPE == "profile":
            config_args.update({"menu_indent": 0})
        else:  # system
            config_args.update({"menu_indent": 4})
        isolinux, grub, to_copy = self._generate_descendant_config(**config_args)
        autoinstall_template = descendant_obj.autoinstall
        if autoinstall_template is None:
            raise ValueError(
                f"autoinstall template cannot be None for obj {descendant_obj.name}"
            )
        autoinstall = self.api.autoinstall_mgr.generate_autoinstall(
            descendant_obj, autoinstall_template
        )

        if distro_obj.breed == "redhat":
            autoinstall = CDREGEX.sub("cdrom\n", autoinstall, count=1)

        repos: List[str] = []
        if airgapped:
            repos = data.get("repos", [])
            if repos:
                self.validate_repos(name, repos, repo_mirrordir)
                autoinstall = re.sub(
                    rf"^(\s*repo --name=\S+ --baseurl=).*/cobbler/distro_mirror/{distro_obj.name}/?(.*)",
                    r"\1 file:///mnt/source/repo_mirror/\2",
                    autoinstall,
                    re.MULTILINE,
                )
            autoinstall = self._update_repos_in_autoinstall_data(autoinstall, repos)
        cfg_parts.isolinux.append(isolinux)
        cfg_parts.grub.append(grub)
        cfg_parts.bootfiles_copysets.append(to_copy)
        autoinstall_data[name] = Autoinstall(autoinstall, repos)

    def _update_repos_in_autoinstall_data(
        self, autoinstall_data: str, repos_names: List[str]
    ) -> str:
        for repo_name in repos_names:
            autoinstall_data = re.sub(
                rf"^(\s*repo --name={repo_name} --baseurl=).*",
                rf"\1 file:///mnt/source/repo_mirror/{repo_name}",
                autoinstall_data,
                re.MULTILINE,
            )
        return autoinstall_data

    def _copy_distro_files(self, filesource: str, output_dir: str):
        """Copy the distro tree in filesource to output_dir.

        :param filesource: Path to root of the distro source tree.
        :param output_dir: Path to the directory into which to copy all files.
        :raises RuntimeError: rsync command failed.
        """
        cmd = [
            "rsync",
            "-rlptgu",
            "--exclude",
            "boot.cat",
            "--exclude",
            "TRANS.TBL",
            "--exclude",
            "isolinux/",
            f"{filesource}/",
            f"{output_dir}/",
        ]
        self.logger.info("- copying distro files (%s)", cmd)
        rc = utils.subprocess_call(cmd, shell=False)
        if rc != 0:
            raise RuntimeError("rsync of distro files failed")

    def _copy_repos(
        self,
        autoinstall_data: Iterable[Autoinstall],
        source_dir: pathlib.Path,
        output_dir: pathlib.Path,
    ):
        """Copy repos for airgapped ISOs.

        The caller of this function has to check if an airgapped ISO is built.
        :param autoinstall_data: Iterable of Autoinstall records that contain the lists of repos.
        :param source_dir: Path to the directory containing the repos.
        :param output_dir: Path to the directory into which to copy all files.
        :raises RuntimeError: rsync command failed.
        """
        for repo in itertools.chain.from_iterable(ai.repos for ai in autoinstall_data):
            self.logger.info(" - copying repo '%s' for airgapped iso", repo)
            cmd = [
                "rsync",
                "-rlptgu",
                "--exclude",
                "boot.cat",
                "--exclude",
                "TRANS.TBL",
                f"{source_dir / repo}/",
                str(output_dir),
            ]
            rc = utils.subprocess_call(cmd, shell=False)
            if rc != 0:
                raise RuntimeError(f"Copying of repo {repo} failed.")

    def run(
        self,
        iso: str = "autoinst.iso",
        buildisodir: str = "",
        profiles: Optional[List[str]] = None,
        systems: Optional[List[str]] = None,
        xorrisofs_opts: str = "",
        distro_name: Optional[str] = None,
        airgapped: bool = False,
        source: str = "",
        esp: Optional[str] = None,
        exclude_systems: bool = False,
        **kwargs: Any,
    ):
        """
        Run the whole iso generation from bottom to top. Per default this builds an ISO for all available systems
        and profiles. This is the only method which should be called from non-class members. The ``profiles`` and
        ``system`` parameters can be combined.

        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles: The filter to generate the ISO only for selected profiles. None means all.
        :param systems: The filter to generate the ISO only for selected systems. None means all.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        :param distro_name: For detecting the architecture of the ISO. If not provided, taken from first profile or
            system item.
        :param airgapped: This option implies ``standalone=True``.
        :param source: If the iso should be offline available this is the path to the sources of the image.
        :param exclude_systems: Whether system entries should not be exported.
        """
        del kwargs  # just accepted for polymorphism

        distro_obj, profile_objs, system_objs = self.prepare_sources(
            distro_name, profiles, systems, exclude_systems
        )

        filesource = source
        loader_config_parts = LoaderCfgsParts([self.iso_template], [], [])
        autoinstall_data: Dict[str, Autoinstall] = {}
        buildisodir = self._prepare_buildisodir(buildisodir)
        repo_mirrordir = pathlib.Path(self.api.settings().webdir) / "repo_mirror"
        distro_mirrordir = pathlib.Path(self.api.settings().webdir) / "distro_mirror"
        esp_location = ""
        xorriso_func = None
        buildiso_dirs = None

        # generate configs, list of repos, and autoinstall data
        for profile_obj in profile_objs:
            self._generate_item(
                descendant_obj=profile_obj,
                distro_obj=distro_obj,
                airgapped=airgapped,
                cfg_parts=loader_config_parts,
                repo_mirrordir=repo_mirrordir,
                autoinstall_data=autoinstall_data,
            )
            for descendant in profile_obj.descendants:
                # handle everything below this top-level profile, but skip not selected systems
                if (
                    descendant.COLLECTION_TYPE == "system"  # type: ignore[reportUnnecessaryComparison]
                    and descendant not in system_objs
                ):
                    continue
                self._generate_item(
                    descendant_obj=descendant,  # type: ignore
                    distro_obj=distro_obj,
                    airgapped=airgapped,
                    cfg_parts=loader_config_parts,
                    repo_mirrordir=repo_mirrordir,
                    autoinstall_data=autoinstall_data,
                )
        if distro_obj.arch == Archs.X86_64:
            xorriso_func = self._xorriso_x86_64
            buildiso_dirs = self.create_buildiso_dirs_x86_64(buildisodir)

            # fill temporary directory with arch-specific binaries
            self._copy_isolinux_files()
            # create EFI system partition (ESP) if needed, uses the ESP from the
            # distro if it was copied
            if esp:
                esp_location = esp
            else:
                esp_location = self._find_esp(buildiso_dirs.root)  # type: ignore[assignment]

            if esp_location is None:
                esp_location = self._create_esp_image_file(buildisodir)
                self._copy_grub_into_esp(esp_location, distro_obj.arch)

            self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)
            self._write_isolinux_cfg(
                loader_config_parts.isolinux, buildiso_dirs.isolinux
            )

        elif distro_obj.arch in (Archs.PPC, Archs.PPC64, Archs.PPC64LE, Archs.PPC64EL):
            xorriso_func = self._xorriso_ppc64le
            buildiso_dirs = self.create_buildiso_dirs_ppc64le(buildisodir)  # type: ignore[assignment]
            grub_bin = (
                pathlib.Path(self.api.settings().bootloaders_dir)
                / "grub"
                / "grub.ppc64le"
            )
            bootinfo_txt = self._render_bootinfo_txt(distro_obj.name)
            # fill temporary directory with arch-specific binaries
            filesystem_helpers.copyfile(
                str(grub_bin), str(buildiso_dirs.grub / "grub.elf")  # type: ignore[union-attr]
            )

            self._write_bootinfo(bootinfo_txt, buildiso_dirs.ppc)  # type: ignore[union-attr]
            self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)  # type: ignore[union-attr]
        else:
            raise ValueError(
                f"cobbler buildiso does not work for arch={distro_obj.arch}"
            )

        if not filesource:
            filesource = self._find_distro_source(
                distro_obj.kernel, str(distro_mirrordir)
            )
        # copy kernels, initrds, and distro files (e.g. installer)
        self._copy_distro_files(filesource, str(buildiso_dirs.root))  # type: ignore[union-attr]
        for copyset in loader_config_parts.bootfiles_copysets:
            self._copy_boot_files(
                copyset.src_kernel,
                copyset.src_initrd,
                str(buildiso_dirs.root),  # type: ignore[union-attr]
                copyset.new_filename,
            )

        # sync repos
        if airgapped:
            buildiso_dirs.repo.mkdir(exist_ok=True)  # type: ignore[union-attr]
            self._copy_repos(
                autoinstall_data.values(), repo_mirrordir, buildiso_dirs.repo  # type: ignore[union-attr]
            )

        self._write_autoinstall_cfg(autoinstall_data, buildiso_dirs.autoinstall)  # type: ignore[union-attr]
        xorriso_func(xorrisofs_opts, iso, buildisodir, buildisodir + "/efi")
