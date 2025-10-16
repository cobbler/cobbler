"""
This module is responsible to generate auto-installation files and metadata. This is the legacy "mixed" way that
combines AutoYAST, Kickstart and Preseed.
"""

import urllib.parse
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import SplitResult

from cobbler import utils, validate
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.distro import Distro
    from cobbler.items.template import Template


# TODO: Check changes from main branch from Template refactoring
class LegacyGenerator(AutoinstallBaseGenerator):
    """
    This is the legacy way of requesting auto-installation templates. New features will not be added and only bugs will
    be fixed.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        meta = utils.blender(self.api, False, obj)
        autoinstall_rel_path = meta["autoinstall"]

        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        if not autoinstall_rel_path:
            return f"# automatic installation file value missing or invalid at {obj.TYPE_NAME} {obj.name}"

        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta["autoinstall_meta"]
        del meta["autoinstall_meta"]
        meta.update(autoinstall_meta)

        # get parent distro
        if obj.TYPE_NAME == "system":
            distro: "Distro" = obj.get_conceptual_parent().get_conceptual_parent()  # type: ignore
        else:  # must be a profile then
            distro = obj.get_conceptual_parent()  # type: ignore

        # add package repositories metadata to autoinstall metavariables
        if distro.breed == "redhat":
            meta["yum_repo_stanza"] = self.generate_autoinstall_metadata(
                obj, "yum_repo_stanza"
            )
            meta["yum_config_stanza"] = self.generate_autoinstall_metadata(
                obj, "yum_config_stanza"
            )

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(
                meta["kernel_options_post"]
            )

        # add install_source_directory metavariable to autoinstall metavariables if distro is based on Preseed
        if distro.breed in ["debian", "ubuntu"] and "tree" in meta:
            urlparts: "SplitResult" = urllib.parse.urlsplit(meta["tree"])  # type: ignore
            meta["install_source_directory"] = urlparts[2]

        if obj.autoinstall is None:  # type: ignore
            return "# no automatic installation template set"

        return self.api.templar.render(obj.autoinstall.content, meta, None)  # type: ignore

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        if key == "yum_repo_stanza":
            return self.__generate_repo_stanza(obj, (obj.TYPE_NAME == "system"))  # type: ignore
        if key == "yum_repo_stanza":
            return self.__generate_config_stanza(obj, (obj.TYPE_NAME == "system"))  # type: ignore
        return None

    def __generate_repo_stanza(
        self, obj: "BootableItem", is_profile: bool = True
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
            # see if this is a source_repo or not
            repo_obj = self.api.find_repo(return_list=False, uid=repo)
            if repo_obj is not None and not isinstance(repo_obj, list):
                yumopts = ""
                for opt in repo_obj.yumopts:
                    # filter invalid values to the repo statement in automatic installation files

                    if opt in ["exclude", "include"]:
                        value = repo_obj.yumopts[opt].replace(" ", ",")
                        yumopts = yumopts + f" --{opt}pkgs={value}"
                    elif not opt.lower() in validate.AUTOINSTALL_REPO_BLACKLIST:
                        yumopts += f" {opt}={repo_obj.yumopts[opt]}"
                if (
                    "enabled" not in repo_obj.yumopts
                    or repo_obj.yumopts["enabled"] == "1"
                ):
                    if repo_obj.mirror_locally:
                        baseurl = f"http://{blended['http_server']}/cobbler/repo_mirror/{repo_obj.name}"
                        if baseurl not in included:
                            buf += f"repo --name={repo_obj.name} --baseurl={baseurl}\n"
                        included[baseurl] = 1
                    else:
                        if repo_obj.mirror not in included:
                            buf += f"repo --name={repo_obj.name} --baseurl={repo_obj.mirror} {yumopts}\n"
                        included[repo_obj.mirror] = 1
            else:
                # FIXME: what to do if we can't find the repo object that is listed?
                # This should be a warning at another point, probably not here so we'll just not list it so the
                # automatic installation file will still work as nothing will be here to read the output noise.
                # Logging might be useful.
                pass

        if is_profile:
            distro: "Distro" = obj.get_conceptual_parent()  # type: ignore
        else:
            distro: "Distro" = obj.get_conceptual_parent().get_conceptual_parent()  # type: ignore

        source_repos = distro.source_repos
        count = 0
        for repo in source_repos:
            count += 1
            if not repo[1] in included:
                buf += f"repo --name=source-{count} --baseurl={repo[1]}\n"
                included[repo[1]] = 1

        return buf

    def __generate_config_stanza(self, obj: "BootableItem", is_profile: bool = True):
        """
        Add in automatic to configure /etc/yum.repos.d on the remote system if the automatic installation file
        (template file) contains the magic $yum_config_stanza.

        :param obj: The profile or system to generate a generate a config stanza for.
        :param is_profile: If the object is a profile. If False it is assumed that the object is a system.
        :return: The curl command to execute to get the configuration for a system or profile.
        """

        if not self.api.settings().yum_post_install_mirror:
            return ""

        blended = utils.blender(self.api, False, obj)
        autoinstall_scheme = self.api.settings().autoinstall_scheme
        if is_profile:
            url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/profile/{obj.name}"
        else:
            url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/system/{obj.name}"

        return f'curl "{url}" --output /etc/yum.repos.d/cobbler-config.repo\n'
