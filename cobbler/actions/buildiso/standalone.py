"""
This module contains the specific code for generating standalone or airgapped ISOs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import itertools
import os
import pathlib
import re
from typing import Dict, List, Iterable, Tuple

from cobbler import utils
from cobbler.actions import buildiso
from cobbler.actions.buildiso import BootFilesCopyset, LoaderCfgsParts, Autoinstall

CDREGEX = re.compile(r"^\s*url .*\n", re.IGNORECASE | re.MULTILINE)


def _generate_append_line_standalone(data: dict, distro, descendant) -> str:
    """
    Generates the append line for the kernel so the installation can be done unattended.
    :param data: The values for the append line. The key "kernel_options" must be present.
    :param distro: The distro object to generate the append line from.
    :param descendant: The profile or system which is underneath the distro.
    :return: The base append_line which we need for booting the built ISO. Contains initrd and autoinstall parameter.
    """
    append_line = f"  APPEND initrd=/{os.path.basename(distro.initrd)}"
    if distro.breed == "redhat":
        if distro.os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
            append_line += f" ks=cdrom:/autoinstall/{descendant.name}.cfg  repo=cdrom"
        else:
            append_line += (
                f" inst.ks=cdrom:/autoinstall/{descendant.name}.cfg inst.repo=cdrom"
            )
    elif distro.breed == "suse":
        append_line += (
            f" autoyast=file:///autoinstall/{descendant.name}.cfg install=cdrom:///"
        )
        if "install" in data["kernel_options"]:
            del data["kernel_options"]["install"]
    elif distro.breed in ["ubuntu", "debian"]:
        append_line += f" auto-install/enable=true preseed/file=/cdrom/autoinstall/{descendant.name}.cfg"

    # add remaining kernel_options to append_line
    append_line += buildiso.add_remaining_kopts(data["kernel_options"])
    return append_line


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
            with open(output_dir / f"{file_name}.cfg", "w") as f:
                f.write(autoinstall.config)

    def _generate_descendant_config(
        self, descendant, menu_indent: int, distro, append_line: str
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
            if repo_obj is None:
                raise ValueError(
                    f"Repository {repo_name}, referenced by {profile_name}, not found."
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
        descendant_obj,
        distro_obj,
        airgapped,
        cfg_parts,
        repo_mirrordir,
        autoinstall_data,
    ):
        self.logger.debug("Generating buildiso data for %s:%s", descendant_obj.TYPE_NAME, descendant_obj.name)
        data: dict = utils.blender(self.api, False, descendant_obj)
        utils.kopts_overwrite(
            data["kernel_options"], self.api.settings().server, distro_obj.breed
        )
        append_line = _generate_append_line_standalone(data, distro_obj, descendant_obj)
        name = descendant_obj.name
        config_args = {
            "descendant": descendant_obj,
            "distro": distro_obj,
            "append_line": append_line,
        }
        if descendant_obj.COLLECTION_TYPE == "profile":
            config_args.update({"menu_indent": 0})
            autoinstall_args = {"profile": descendant_obj}
        else:  # system
            config_args.update({"menu_indent": 4})
            autoinstall_args = {"system": descendant_obj}
        isolinux, grub, to_copy = self._generate_descendant_config(**config_args)
        autoinstall = self.api.autoinstallgen.generate_autoinstall(**autoinstall_args)

        if distro_obj.breed == "redhat":
            autoinstall = CDREGEX.sub("cdrom\n", autoinstall, count=1)

        repos = []
        if airgapped:
            repos = data.get("repos", [])
            if repos:
                self.validate_repos(name, repos, repo_mirrordir)
                autoinstall = re.sub(
                    rf"^(\s*repo --name=\S+ --baseurl=).*/cobbler/distro_mirror/{distro_obj.name}/?(.*)",
                    rf"\1 file:///mnt/source/repo_mirror/\2",
                    autoinstall,
                    re.MULTILINE,
                )
            autoinstall = self._update_repos_in_autoinstall_data(autoinstall, repos)
        cfg_parts.isolinux.append(isolinux)
        cfg_parts.grub.append(grub)
        cfg_parts.bootfiles_copysets.append(to_copy)
        autoinstall_data[name] = Autoinstall(autoinstall, repos)

    def _update_repos_in_autoinstall_data(self, autoinstall_data, repos_names) -> str:
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
        self.logger.info('- copying distro files (%s)', cmd)
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
        profiles: List[str] = None,
        xorrisofs_opts: str = "",
        distro_name: str = "",
        airgapped: bool = False,
        source="",
        **kwargs,
    ):
        """
        Run the whole iso generation from bottom to top. Per default this builds an ISO for all available systems
        and profiles.
        This is the only method which should be called from non-class members. The ``profiles`` and ``system``
        parameters can be combined.
        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles: The filter to generate the ISO only for selected profiles.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        :param distro_name: For detecting the architecture of the ISO.
        :param airgapped: This option implies ``standalone=True``.
        :param source: If the iso should be offline available this is the path to the sources of the image.
        """
        del kwargs  # just accepted for polymorphism

        self.logger.info("Generating standalone ISO for distro %s", distro_name)
        distro_obj = self.parse_distro(distro_name)
        profile_objs = self.parse_profiles(profiles, distro_obj)
        filesource = source
        loader_config_parts = LoaderCfgsParts([self.iso_template], [], [])
        autoinstall_data: Dict[str, Autoinstall] = {}
        buildisodir = self._prepare_buildisodir(buildisodir)
        buildiso_dirs = self.create_buildiso_dirs(buildisodir)
        repo_mirrordir = pathlib.Path(self.api.settings().webdir) / "repo_mirror"
        distro_mirrordir = pathlib.Path(self.api.settings().webdir) / "distro_mirror"

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
                # handle everything below this top-level profile
                self._generate_item(
                    descendant_obj=descendant,
                    distro_obj=distro_obj,
                    airgapped=airgapped,
                    cfg_parts=loader_config_parts,
                    repo_mirrordir=repo_mirrordir,
                    autoinstall_data=autoinstall_data,
                )

        # copy isolinux, kernels, initrds, and distro files (e.g. installer)
        self._copy_isolinux_files()
        for copyset in loader_config_parts.bootfiles_copysets:
            self._copy_boot_files(
                copyset.src_kernel,
                copyset.src_initrd,
                str(buildiso_dirs.root),
                copyset.new_filename,
            )
        if not filesource:
            filesource = self._find_distro_source(
                distro_obj.kernel, str(distro_mirrordir)
            )
        self._copy_distro_files(filesource, str(buildiso_dirs.root))

        # create EFI system partition (ESP) if needed, uses the ESP from the
        # distro if it was copied
        esp_location = self._find_esp(buildiso_dirs.root)
        if esp_location is None:
            esp_location = self._create_esp_image_file(buildisodir)
            self._copy_grub_into_esp(esp_location, distro_obj.arch)

        # sync repos
        if airgapped:
            buildiso_dirs.repo.mkdir(exist_ok=True)
            self._copy_repos(
                autoinstall_data.values(), repo_mirrordir, buildiso_dirs.repo
            )
        self._write_isolinux_cfg(loader_config_parts.isolinux, buildiso_dirs.isolinux)
        self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)
        self._write_autoinstall_cfg(autoinstall_data, buildiso_dirs.autoinstall)
        self._generate_iso(xorrisofs_opts, iso, buildisodir, esp_location)
