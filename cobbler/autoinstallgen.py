"""
Builds out filesystem trees/data based on the object tree. This is the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import urllib.parse
import xml.dom.minidom
from typing import TYPE_CHECKING

from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


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

    def createAutoYaSTScript(self, document, script, name):
        """
        This method attaches a script with a given name to an existing AutoYaST XML file.

        :param document: The existing AutoYaST XML file.
        :param script: The script to attach.
        :param name: The name of the script.
        :return: The AutoYaST file with the attached script.
        """
        new_script = document.createElement("script")
        new_script_source = document.createElement("source")
        new_script_source_text = document.createCDATASection(script)
        new_script.appendChild(new_script_source)

        new_script_file = document.createElement("filename")
        new_script_file_text = document.createTextNode(name)
        new_script.appendChild(new_script_file)

        new_script_source.appendChild(new_script_source_text)
        new_script_file.appendChild(new_script_file_text)
        return new_script

    def addAutoYaSTScript(self, document, script_type, source):
        """
        Add scripts to an existing AutoYaST XML.

        :param document: The existing AutoYaST XML object.
        :param script_type: The type of the script which should be added.
        :param source: The source of the script. This should be ideally a string.
        """
        scripts = document.getElementsByTagName("scripts")
        if scripts.length == 0:
            new_scripts = document.createElement("scripts")
            document.documentElement.appendChild(new_scripts)
            scripts = document.getElementsByTagName("scripts")
        added = 0
        for stype in scripts[0].childNodes:
            if stype.nodeType == stype.ELEMENT_NODE and stype.tagName == script_type:
                stype.appendChild(
                    self.createAutoYaSTScript(
                        document, source, script_type + "_cobbler"
                    )
                )
                added = 1
        if added == 0:
            new_chroot_scripts = document.createElement(script_type)
            new_chroot_scripts.setAttribute("config:type", "list")
            new_chroot_scripts.appendChild(
                self.createAutoYaSTScript(document, source, script_type + "_cobbler")
            )
            scripts[0].appendChild(new_chroot_scripts)

    def generate_autoyast(self, profile=None, system=None, raw_data=None) -> str:
        """
        Generate auto installation information for SUSE distribution (AutoYaST XML file) for a specific system or
        general profile. Only a system OR profile can be supplied, NOT both.

        :param profile: The profile to generate the AutoYaST file for.
        :param system: The system to generate the AutoYaST file for.
        :param raw_data: The raw data which should be included in the profile.
        :return: The generated AutoYaST XML file.
        """
        self.api.logger.info(
            "AutoYaST XML file found. Checkpoint: profile=%s system=%s", profile, system
        )

        what = "profile"
        blend_this = profile
        if system:
            what = "system"
            blend_this = system
        blended = utils.blender(self.api, False, blend_this)
        srv = blended["http_server"]

        document = xml.dom.minidom.parseString(raw_data)

        # Do we already have the #raw comment in the XML? (add_comment = 0 means, don't add #raw comment)
        add_comment = 1
        for node in document.childNodes[1].childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == "cobbler":
                add_comment = 0
                break

        # Add some cobbler information to the XML file, maybe that should be configurable.
        if add_comment == 1:
            cobbler_element = document.createElement("cobbler")
            cobbler_element_system = xml.dom.minidom.Element("system_name")
            cobbler_element_profile = xml.dom.minidom.Element("profile_name")
            if system is not None:
                cobbler_text_system = document.createTextNode(system.name)
                cobbler_element_system.appendChild(cobbler_text_system)
            if profile is not None:
                cobbler_text_profile = document.createTextNode(profile.name)
                cobbler_element_profile.appendChild(cobbler_text_profile)

            cobbler_element_server = document.createElement("server")
            cobbler_text_server = document.createTextNode(blended["http_server"])
            cobbler_element_server.appendChild(cobbler_text_server)

            cobbler_element.appendChild(cobbler_element_server)
            cobbler_element.appendChild(cobbler_element_system)
            cobbler_element.appendChild(cobbler_element_profile)

        name = profile.name
        if system is not None:
            name = system.name

        if self.settings.run_install_triggers:
            # notify cobblerd when we start/finished the installation
            protocol = self.api.settings().autoinstall_scheme
            self.addAutoYaSTScript(
                document,
                "pre-scripts",
                f'\ncurl "{protocol}://{srv}/cblr/svc/op/trig/mode/pre/{what}/{name}" > /dev/null',
            )
            self.addAutoYaSTScript(
                document,
                "init-scripts",
                f'\ncurl "{protocol}://{srv}/cblr/svc/op/trig/mode/post/{what}/{name}" > /dev/null',
            )

        return document.toxml()

    def generate_repo_stanza(self, obj, is_profile: bool = True) -> str:
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
            repo_obj = self.api.find_repo(repo)
            if repo_obj is not None:
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
            distro = obj.get_conceptual_parent()
        else:
            distro = obj.get_conceptual_parent().get_conceptual_parent()

        source_repos = distro.source_repos
        count = 0
        for repo in source_repos:
            count += 1
            if not repo[1] in included:
                buf += f"repo --name=source-{count} --baseurl={repo[1]}\n"
                included[repo[1]] = 1

        return buf

    def generate_config_stanza(self, obj, is_profile: bool = True):
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

    def generate_autoinstall_for_system(self, sys_name) -> str:
        """
        Generate an autoinstall config or script for a system.

        :param sys_name: The system name to generate an autoinstall script for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the system references a missing profile.
        """
        system_obj = self.api.find_system(name=sys_name)
        if system_obj is None:
            return "# system not found"

        profile_obj = system_obj.get_conceptual_parent()
        if profile_obj is None:
            raise CX(
                "system %(system)s references missing profile %(profile)s"
                % {"system": system_obj.name, "profile": system_obj.profile}
            )

        distro = profile_obj.get_conceptual_parent()
        if distro is None:
            # this is an image parented system, no automatic installation file available
            return "# image based systems do not have automatic installation files"

        return self.generate_autoinstall(profile=profile_obj, system=system_obj)

    def generate_autoinstall(self, profile=None, system=None) -> str:
        """
        This is an internal method for generating an autoinstall config/script. Please use the
        ``generate_autoinstall_for_*`` methods. If you insist on using this mehtod please only supply a profile or a
        system, not both.

        :param profile: The profile to use for generating the autoinstall config/script.
        :param system: The system to use for generating the autoinstall config/script. If both arguments are given,
                       this wins.
        :return: The autoinstall script or configuration file as a string.
        """
        obj = system
        obj_type = "system"
        if system is None:
            obj = profile
            obj_type = "profile"

        meta = utils.blender(self.api, False, obj)
        autoinstall_rel_path = meta["autoinstall"]

        if not autoinstall_rel_path:
            return f"# automatic installation file value missing or invalid at {obj_type} {obj.name}"

        # get parent distro
        distro = profile.get_conceptual_parent()
        if system is not None:
            distro = system.get_conceptual_parent().get_conceptual_parent()

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
            urlparts = urllib.parse.urlsplit(meta["tree"])
            meta["install_source_directory"] = urlparts[2]

        try:
            autoinstall_path = (
                f"{self.settings.autoinstall_templates_dir}/{autoinstall_rel_path}"
            )
            raw_data = utils.read_file_contents(autoinstall_path)

            data = self.api.templar.render(raw_data, meta, None)

            return data
        except FileNotFoundError:
            error_msg = (
                f"automatic installation file {meta['autoinstall']} not found"
                f" at {self.settings.autoinstall_templates_dir}"
            )
            self.api.logger.warning(error_msg)
            return f"# {error_msg}"

    def generate_autoinstall_for_profile(self, profile) -> str:
        """
        Generate an autoinstall config or script for a profile.

        :param profile: The Profile to generate the script/config for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the profile references a missing distro.
        """
        profile = self.api.find_profile(name=profile)
        if profile is None:
            return "# profile not found"

        distro = profile.get_conceptual_parent()
        if distro is None:
            raise CX(
                "profile %(profile)s references missing distro %(distro)s"
                % {"profile": profile.name, "distro": profile.distro}
            )

        return self.generate_autoinstall(profile=profile)

    def get_last_errors(self) -> list:
        """
        Returns the list of errors generated by the last template render action.

        :return: The list of error messages which are available. This may not only contain error messages related to
                 generating autoinstallation configuration and scripts.
        """
        return self.api.templar.last_errors
