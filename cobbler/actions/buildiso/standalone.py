"""
This module contains the specific code for generating standalone or airgapped ISOs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
from typing import Dict, List

from cobbler import utils

from cobbler.actions import buildiso

cdregex = re.compile(r"^\s*url .*\n", re.IGNORECASE | re.MULTILINE)


def _generate_append_line_standalone(data: dict, distro, descendant) -> str:
    """
    Generates the append line for the kernel so the installation can be done unattended.
    :param data: The values for the append line. The key "kernel_options" must be present.
    :param distro: The distro object to generate the append line from.
    :param descendant: The profile or system which is underneath the distro.
    :return: The base append_line which we need for booting the built ISO. Contains initrd and autoinstall parameter.
    """
    append_line = "  APPEND initrd=%s" % os.path.basename(distro.initrd)
    if distro.breed == "redhat":
        append_line += " inst.ks=cdrom:/isolinux/%s.cfg" % descendant.name
    elif distro.breed == "suse":
        append_line += (
            " autoyast=file:///isolinux/%s.cfg install=cdrom:///" % descendant.name
        )
        if "install" in data["kernel_options"]:
            del data["kernel_options"]["install"]
    elif distro.breed in ["ubuntu", "debian"]:
        append_line += (
            " auto-install/enable=true preseed/file=/cdrom/isolinux/%s.cfg"
            % descendant.name
        )

    # add remaining kernel_options to append_line
    append_line += buildiso.add_remaining_kopts(data["kernel_options"])
    return append_line


class StandaloneBuildiso(buildiso.BuildIso):
    """
    This class contains all functionality related to building self-contained installation images.
    """

    def _validate_standalone_args(self, distro_name: str, source: str):
        """
        If building standalone, we only want --distro and --profiles (optional), systems are disallowed
        :param distro_name: The name of the distribution we want to install.
        :param source: The source which we copy to the ISO as an installation base.
        """
        if not distro_name:
            raise ValueError(
                "When building a standalone ISO, you must specify a --distro"
            )
        base_distro = self.api.find_distro(name=distro_name)
        if base_distro is None:
            raise ValueError("Distro specified was not found!")
        source = self._validate_standalone_filesource(source, base_distro)
        if not os.path.exists(source):
            raise ValueError('The specified source "%s" does not exist!' % source)

        # Ensure all profiles specified are children of the distro
        if self.profiles:
            orphan_profiles = [
                profile
                for profile in self.profiles
                if profile not in base_distro.children
            ]
            if len(orphan_profiles) > 0:
                raise ValueError(
                    "When building a standalone ISO, all --profiles must be under --distro"
                )

    def _sync_airgapped_repos(self, airgapped: bool, repo_names_to_copy: dict):
        """
        Syncs all repositories locally available into the image if the is supposed to be airgapped.
        :param airgapped: If false this method is doing nothing.
        :param repo_names_to_copy: The names of the repositories which should be included.
        :raises RuntimeError: In case the rsync of the repository was not successful.
        """
        if airgapped:
            # copy any repos found in profiles or systems to the iso build
            repodir = os.path.abspath(
                os.path.join(self.isolinuxdir, "..", "repo_mirror")
            )
            if not os.path.exists(repodir):
                os.makedirs(repodir)

            for repo_name in repo_names_to_copy:
                self.logger.info(" - copying repo '%s' for airgapped ISO", repo_name)
                rsync_successful = utils.rsync_files(
                    repo_names_to_copy[repo_name],
                    os.path.join(repodir, repo_name),
                    "--exclude=TRANS.TBL --exclude=cache/ --no-g",
                    quiet=True,
                )
                if not rsync_successful:
                    raise RuntimeError('rsync of repo "%s" failed' % repo_name)

    def _validate_standalone_filesource(self, filesource: str, distro) -> str:
        """
        Validate that the path to the installation sources is making sense. If they do then normalize the path and
        return it.
        :param filesource: The path to the installation sources.
        :param distro: The distribution of which the kernel is used for booting the image.
        :raises ValueError: In case the installation source was not found.
        :return: Normalized filesource which points to the absolute path of the source tree.
        """
        if not filesource:
            # Try to determine the source from the distro kernel path
            self.logger.debug("Trying to locate source for distro")
            (source_head, source_tail) = os.path.split(distro.kernel)
            distro_mirror = os.path.join(self.api.settings().webdir, "distro_mirror")
            while source_tail != "":
                if source_head == distro_mirror:
                    filesource = os.path.join(source_head, source_tail)
                    self.logger.debug("Found source in %s", filesource)
                    return filesource
                (source_head, source_tail) = os.path.split(source_head)
            # Can't find the source, raise an error
            raise ValueError(
                "Error, no installation source found. When building a standalone or airgapped ISO, you must specify a "
                "--source if the distro install tree is not hosted locally"
            )
        return filesource

    def _generate_autoinstall_data(
        self, descendant, distro, airgapped: bool, data: dict, repo_names_to_copy: dict
    ) -> str:
        """
        Generates the autoinstall script for the distro/profile/system we want to install.
        :param descendant: The descendant to generate the ISO for.
        :param distro: The distro to generate the ISO for.
        :param airgapped: Whether the ISO should be bootable in an airgapped environment or not.
        :param data: The data for the append line of the kernel.
        :param repo_names_to_copy: The repositories to include in case of an airgapped environment.
        :return: The generated script for the ISO.
        """
        autoinstall_data = ""
        if descendant.COLLECTION_TYPE == "profile":
            autoinstall_data = self.api.autoinstallgen.generate_autoinstall_for_profile(
                descendant.name
            )
        elif descendant.COLLECTION_TYPE == "system":
            autoinstall_data = self.api.autoinstallgen.generate_autoinstall_for_system(
                descendant.name
            )

        if distro.breed == "redhat":
            autoinstall_data = cdregex.sub("cdrom\n", autoinstall_data, count=1)

        if airgapped:
            for repo_name in data.get("repos", []):
                repo_obj = self.api.find_repo(repo_name)
                error = (
                    "%s %s refers to repo %s, which {error_message}; cannot build airgapped ISO"
                    % (descendant.COLLECTION_TYPE, descendant.name, repo_name)
                )

                if repo_obj is None:
                    raise ValueError(error.format(error_message="does not exist"))
                if not repo_obj.mirror_locally:
                    raise ValueError(
                        error.format(
                            error_message="is not configured for local mirroring"
                        )
                    )
                mirrordir = os.path.join(
                    self.api.settings().webdir, "repo_mirror", repo_obj.name
                )
                if not os.path.exists(mirrordir):
                    raise ValueError(
                        error.format(
                            error_message="has a missing local mirror directory"
                        )
                    )

                repo_names_to_copy[repo_obj.name] = mirrordir

                # update the baseurl in autoinstall_data to use the cdrom copy of this repo
                reporegex = re.compile(
                    r"^(\s*repo --name=%s --baseurl=).*" % repo_obj.name, re.MULTILINE
                )
                autoinstall_data = reporegex.sub(
                    r"\1" + "file:///mnt/source/repo_mirror/" + repo_obj.name,
                    autoinstall_data,
                )

            # rewrite any split-tree repos, such as in redhat, to use cdrom
            srcreporegex = re.compile(
                r"^(\s*repo --name=\S+ --baseurl=).*/cobbler/distro_mirror/%s/?(.*)"
                % distro.name,
                re.MULTILINE,
            )
            autoinstall_data = srcreporegex.sub(
                r"\1" + "file:///mnt/source" + r"\2", autoinstall_data
            )
        return autoinstall_data

    def _generate_descendant(
        self,
        descendant,
        cfglines: List[str],
        distro,
        airgapped: bool,
        repo_names_to_copy: dict,
    ):
        """
        Generate the ISOLINUX cfg configuration file for the descendant.
        :param descendant: The descendant to generate the config file for. Must be a profile or system object.
        :param cfglines: The content of the file which has already been generated.
        :param distro: The parent distro.
        :param airgapped: Whether the generated ISO should be bootable in an airgapped environment or not.
        :param repo_names_to_copy: The repository names to copy in the case of an airgapped environment.
        """
        menu_indent = 0
        if descendant.COLLECTION_TYPE == "system":
            menu_indent = 4

        data = utils.blender(self.api, False, descendant)

        # SUSE is not using 'text'. Instead 'textmode' is used as kernel option.
        if distro is not None:
            utils.kopts_overwrite(
                data["kernel_options"], self.api.settings().server, distro.breed
            )

        cfglines.append("")
        cfglines.append("LABEL %s" % descendant.name)
        if menu_indent:
            cfglines.append("  MENU INDENT %d" % menu_indent)
        cfglines.append("  MENU LABEL %s" % descendant.name)
        cfglines.append("  KERNEL %s" % os.path.basename(distro.kernel))

        cfglines.append(_generate_append_line_standalone(data, distro, descendant))

        autoinstall_data = self._generate_autoinstall_data(
            descendant, distro, airgapped, data, repo_names_to_copy
        )
        autoinstall_name = os.path.join(self.isolinuxdir, "%s.cfg" % descendant.name)
        with open(autoinstall_name, "w+") as autoinstall_file:
            autoinstall_file.write(autoinstall_data)

    def generate_standalone_iso(
        self, distro_name: str, filesource: str, airgapped: bool
    ):
        """Creates the ``isolinux.cfg`` for a standalone or airgapped ISO image. And copies possible repositories to
        the image source folder.
        :param distro_name: The name of the Cobbler distribution.
        :param filesource: The source directory for the ISO. This gets rsynced into isolinuxdir.
        :param airgapped: Whether the repositories have to be locally available or the internet is reachable.
        """
        # Get the distro object for the requested distro and then get all of its descendants (profiles/sub-profiles/
        # systems) with sort=True for profile/system hierarchy to allow menu indenting
        distro = self.api.find_distro(name=distro_name)
        if distro is None:
            raise ValueError(
                'Distro "%s" was not found, aborting generation of ISO-file!'
                % distro_name
            )

        self.copy_boot_files(distro, self.isolinuxdir)

        self.logger.info("generating an isolinux.cfg")

        cfglines = [self.iso_template]

        repo_names_to_copy: Dict[str, str] = {}

        for descendant in distro.children:
            descendant = self.api.find_items(what="", name=descendant)
            # if a list of profiles was given, skip any others and their systems
            if len(self.profiles) > 0 and (
                (
                    descendant.COLLECTION_TYPE == "profile"
                    and descendant.name not in self.profiles
                )
                or (
                    descendant.COLLECTION_TYPE == "system"
                    and descendant.profile not in self.profiles
                )
            ):
                continue
            self._generate_descendant(
                descendant, cfglines, distro, airgapped, repo_names_to_copy
            )

        cfglines.append("")
        cfglines.append("MENU END")
        with open(os.path.join(self.isolinuxdir, "isolinux.cfg"), "w+") as cfg:
            cfg.writelines("%s\n" % l for l in cfglines)
        self.logger.info("done writing config")

        self._sync_airgapped_repos(airgapped, repo_names_to_copy)

        # copy distro files last, since they take the most time
        cmd = [
            "rsync",
            "-rlptgu",
            "--exclude",
            "boot.cat",
            "--exclude",
            "TRANS.TBL",
            "--exclude",
            "isolinux/",
            "%s/" % filesource,
            "%s/../" % self.isolinuxdir,
        ]
        self.logger.info('- copying distro "%s" files (%s)', distro_name, cmd)
        rsync_return_code = utils.subprocess_call(cmd, shell=False)
        if rsync_return_code:
            raise OSError("rsync of distro files failed")

    def run(
        self,
        iso: str = "autoinst.iso",
        buildisodir: str = "",
        profiles: List[str] = None,
        xorrisofs_opts: str = "",
        distro_name: str = "",
        airgapped: bool = False,
        source="",
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
        buildisodir = self._prepare_iso(buildisodir, distro_name, profiles)
        self._validate_standalone_args(distro_name, source)
        self.generate_standalone_iso(distro_name, source, airgapped)
        self._generate_iso(xorrisofs_opts, iso, buildisodir)
