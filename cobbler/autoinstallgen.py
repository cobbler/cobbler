"""
Builds out filesystem trees/data based on the object tree. This is the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, List, Optional, Union, cast
from urllib import parse

from cobbler import utils, validate
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.system import System


class AutoInstallationGen:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor

        :param api: The API instance which is used for this object. Normally there is only one
                               instance of the collection manager.
        """
        self.api = api
        self.settings = api.settings()

    def generate_repo_stanza(
        self, obj: Union["Profile", "System"], is_profile: bool = True
    ) -> str:
        """
        Automatically attaches yum repos to profiles/systems in automatic installation files (template files) that
        contain the magic $yum_repo_stanza variable. This includes repo objects as well as the yum repos that are part
        of split tree installs, whose data is stored with the distro (example: RHEL5 imports)

        :param obj: The profile or system to generate the repo stanza for.
        :param is_profile: If True then obj is a profile, otherwise obj has to be a system. Otherwise this method will
                           silently fail.
        :return: The string with the attached yum repos.
        """

        buf = ""
        blended = utils.blender(self.api, False, obj)
        repos = blended["repos"]

        # keep track of URLs and be sure to not include any duplicates
        included = {}

        for repo in repos:
            # see if this is a source_repo or not; we know that this is a single match due to return_list=False
            repo_obj = self.api.find_repo(return_list=False, name=repo)
            if repo_obj is None or isinstance(repo_obj, list):
                # FIXME: what to do if we can't find the repo object that is listed?
                # This should be a warning at another point, probably not here so we'll just not list it so the
                # automatic installation file will still work as nothing will be here to read the output noise.
                # Logging might be useful.
                continue

            yumopts = ""
            for opt in repo_obj.yumopts:
                # filter invalid values to the repo statement in automatic installation files

                if opt in ["exclude", "include"]:
                    value = repo_obj.yumopts[opt].replace(" ", ",")
                    yumopts = yumopts + f" --{opt}pkgs={value}"
                elif not opt.lower() in validate.AUTOINSTALL_REPO_BLACKLIST:
                    yumopts += f" {opt}={repo_obj.yumopts[opt]}"
            if "enabled" not in repo_obj.yumopts or repo_obj.yumopts["enabled"] == "1":
                if repo_obj.mirror_locally:
                    baseurl = f"http://{blended['http_server']}/cobbler/repo_mirror/{repo_obj.name}"
                    if baseurl not in included:
                        buf += f"repo --name={repo_obj.name} --baseurl={baseurl}\n"
                    included[baseurl] = 1
                else:
                    if repo_obj.mirror not in included:
                        buf += f"repo --name={repo_obj.name} --baseurl={repo_obj.mirror} {yumopts}\n"
                    included[repo_obj.mirror] = 1

        if is_profile:
            distro = obj.get_conceptual_parent()
        else:
            profile = obj.get_conceptual_parent()
            if profile is None:
                raise ValueError("Error finding distro!")
            profile = cast(Profile, profile)
            distro = profile.get_conceptual_parent()

        if distro is None:
            raise ValueError("Error finding distro!")
        distro = cast(Distro, distro)

        source_repos = distro.source_repos
        count = 0
        for repo in source_repos:
            count += 1
            if not repo[1] in included:
                buf += f"repo --name=source-{count} --baseurl={repo[1]}\n"
                included[repo[1]] = 1

        return buf

    def generate_config_stanza(
        self, obj: Union["Profile", "System"], is_profile: bool = True
    ) -> str:
        """
        Add in automatic to configure /etc/yum.repos.d on the remote system if the automatic installation file
        (template file) contains the magic $yum_config_stanza.

        :param obj: The profile or system to generate a generate a config stanza for.
        :param is_profile: If the object is a profile. If False it is assumed that the object is a system.
        :return: The curl command to execute to get the configuration for a system or profile.
        """

        if not self.settings.yum_post_install_mirror:
            return ""

        blended = utils.blender(self.api, False, obj)
        autoinstall_scheme = self.api.settings().autoinstall_scheme
        if is_profile:
            url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/profile/{obj.name}"
        else:
            url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/system/{obj.name}"

        return f'curl "{url}" --output /etc/yum.repos.d/cobbler-config.repo\n'

    def generate_autoinstall_for_system(self, sys_name: str) -> str:
        """
        Generate an autoinstall config or script for a system.

        :param sys_name: The system name to generate an autoinstall script for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the system references a missing profile.
        """
        system_obj = self.api.find_system(name=sys_name)
        if system_obj is None or isinstance(system_obj, list):
            return "# system not found"

        profile_obj: Optional["Profile"] = system_obj.get_conceptual_parent()  # type: ignore
        if profile_obj is None:
            raise CX(
                "system %(system)s references missing profile %(profile)s"
                % {"system": system_obj.name, "profile": system_obj.profile}
            )

        distro: Optional["Distro"] = profile_obj.get_conceptual_parent()  # type: ignore
        if distro is None:
            # this is an image parented system, no automatic installation file available
            return "# image based systems do not have automatic installation files"

        return self.generate_autoinstall(profile=None, system=system_obj)

    def generate_autoinstall(
        self, profile: Optional["Profile"] = None, system: Optional["System"] = None
    ) -> str:
        """
        This is an internal method for generating an autoinstall config/script. Please use the
        ``generate_autoinstall_for_*`` methods. If you insist on using this mehtod please only supply a profile or a
        system, not both.

        :param profile: The profile to use for generating the autoinstall config/script.
        :param system: The system to use for generating the autoinstall config/script. If both arguments are given,
                       this wins.
        :return: The autoinstall script or configuration file as a string.
        """
        obj: Optional[Union["System", "Profile"]] = None
        obj_type = "none"
        if system and profile is None:
            obj = system
            obj_type = "system"
        if profile and system is None:
            obj = profile
            obj_type = "profile"

        if obj is None:
            raise ValueError("Neither profile nor system was given! One is required!")

        meta = utils.blender(self.api, False, obj)
        autoinstall_rel_path = meta["autoinstall"]

        if not autoinstall_rel_path:
            return f"# automatic installation file value missing or invalid at {obj_type} {obj.name}"

        # get parent distro
        if system is not None:
            profile = system.get_conceptual_parent()  # type: ignore
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore

        if distro is None:
            raise ValueError("Distro for object not found")

        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta["autoinstall_meta"]
        del meta["autoinstall_meta"]
        meta.update(autoinstall_meta)

        # add package repositories metadata to autoinstall metavariables
        if distro.breed == "redhat":
            meta["yum_repo_stanza"] = self.generate_repo_stanza(obj, (system is None))
            meta["yum_config_stanza"] = self.generate_config_stanza(
                obj, (system is None)
            )
        # FIXME: implement something similar to zypper (SUSE based distros) and apt (Debian based distros)

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(
                meta["kernel_options_post"]
            )

        # add install_source_directory metavariable to autoinstall metavariables if distro is based on Debian
        if distro.breed in ["debian", "ubuntu"] and "tree" in meta:
            urlparts = parse.urlsplit(meta["tree"])  # type: ignore
            meta["install_source_directory"] = urlparts[2]

        if obj.autoinstall is None:
            return "# no automatic installation template set"

        data = self.api.templar.render(obj.autoinstall.content, meta, None)

        return data

    def generate_autoinstall_for_profile(self, profile: str) -> str:
        """
        Generate an autoinstall config or script for a profile.

        :param profile: The Profile to generate the script/config for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the profile references a missing distro.
        """
        profile_obj: Optional["Profile"] = self.api.find_profile(name=profile)  # type: ignore
        if profile_obj is None or isinstance(profile_obj, list):
            return "# profile not found"

        distro: Optional["Distro"] = profile_obj.get_conceptual_parent()  # type: ignore
        if distro is None:
            raise CX(f'Profile "{profile_obj.name}" references missing distro!')

        return self.generate_autoinstall(profile=profile_obj, system=None)

    def get_last_errors(self) -> List[Any]:
        """
        Returns the list of errors generated by the last template render action.

        :return: The list of error messages which are available. This may not only contain error messages related to
                 generating autoinstallation configuration and scripts.
        """
        return self.api.templar.last_errors
