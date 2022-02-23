"""
Builds out filesystem trees/data based on the object tree.
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

import urllib.parse
import xml.dom.minidom

from cobbler import templar
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX


class AutoInstallationGen:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """
    def __init__(self, api):
        """
        Constructor

        :param api: The API instance which is used for this object. Normally there is only one
                               instance of the collection manager.
        """
        self.api = api
        self.settings = api.settings()
        self.templar = templar.Templar(self.api)

    def createAutoYaSTScript(self, document, script, name):
        """
        This method attaches a script with a given name to an existing AutoYaST XML file.

        :param document: The existing AutoYaST XML file.
        :param script: The script to attach.
        :param name: The name of the script.
        :return: The AutoYaST file with the attached script.
        """
        newScript = document.createElement("script")
        newScriptSource = document.createElement("source")
        newScriptSourceText = document.createCDATASection(script)
        newScript.appendChild(newScriptSource)

        newScriptFile = document.createElement("filename")
        newScriptFileText = document.createTextNode(name)
        newScript.appendChild(newScriptFile)

        newScriptSource.appendChild(newScriptSourceText)
        newScriptFile.appendChild(newScriptFileText)
        return newScript

    def addAutoYaSTScript(self, document, type, source):
        """
        Add scripts to an existing AutoYaST XML.

        :param document: The existing AutoYaST XML object.
        :param type: The type of the script which should be added.
        :param source: The source of the script. This should be ideally a string.
        """
        scripts = document.getElementsByTagName("scripts")
        if scripts.length == 0:
            newScripts = document.createElement("scripts")
            document.documentElement.appendChild(newScripts)
            scripts = document.getElementsByTagName("scripts")
        added = 0
        for stype in scripts[0].childNodes:
            if stype.nodeType == stype.ELEMENT_NODE and stype.tagName == type:
                stype.appendChild(self.createAutoYaSTScript(document, source, type + "_cobbler"))
                added = 1
        if added == 0:
            newChrootScripts = document.createElement(type)
            newChrootScripts.setAttribute("config:type", "list")
            newChrootScripts.appendChild(self.createAutoYaSTScript(document, source, type + "_cobbler"))
            scripts[0].appendChild(newChrootScripts)

    def generate_autoyast(self, profile=None, system=None, raw_data=None) -> str:
        """
        Generate auto installation information for SUSE distribution (AutoYaST XML file) for a specific system or
        general profile. Only a system OR profile can be supplied, NOT both.

        :param profile: The profile to generate the AutoYaST file for.
        :param system: The system to generate the AutoYaST file for.
        :param raw_data: The raw data which should be included in the profile.
        :return: The generated AutoYaST XML file.
        """
        self.api.logger.info("AutoYaST XML file found. Checkpoint: profile=%s system=%s" % (profile, system))
        runpost = "\ncurl \"http://%s/cblr/svc/op/trig/mode/post/%s/%s\" > /dev/null"
        runpre = "\ncurl \"http://%s/cblr/svc/op/trig/mode/pre/%s/%s\" > /dev/null"

        what = "profile"
        blend_this = profile
        if system:
            what = "system"
            blend_this = system
        blended = utils.blender(self.api, False, blend_this)
        srv = blended["http_server"]

        document = xml.dom.minidom.parseString(raw_data)

        # Do we already have the #raw comment in the XML? (addComment = 0 means, don't add #raw comment)
        addComment = 1
        for node in document.childNodes[1].childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == "cobbler":
                addComment = 0
                break

        # Add some cobbler information to the XML file, maybe that should be configurable.
        if addComment == 1:
            # startComment = document.createComment("\ncobbler_system_name=$system_name\ncobbler_server=$server\n#raw\n")
            # endComment = document.createComment("\n#end raw\n")
            cobblerElement = document.createElement("cobbler")
            cobblerElementSystem = xml.dom.minidom.Element("system_name")
            cobblerElementProfile = xml.dom.minidom.Element("profile_name")
            if (system is not None):
                cobblerTextSystem = document.createTextNode(system.name)
                cobblerElementSystem.appendChild(cobblerTextSystem)
            if (profile is not None):
                cobblerTextProfile = document.createTextNode(profile.name)
                cobblerElementProfile.appendChild(cobblerTextProfile)

            cobblerElementServer = document.createElement("server")
            cobblerTextServer = document.createTextNode(blended["http_server"])
            cobblerElementServer.appendChild(cobblerTextServer)

            cobblerElement.appendChild(cobblerElementServer)
            cobblerElement.appendChild(cobblerElementSystem)
            cobblerElement.appendChild(cobblerElementProfile)

            # FIXME: this is all broken and no longer works. This entire if block should probably not be hard-coded
            #  anyway
            # self.api.log(document.childNodes[2].childNodes)
            # document.childNodes[1].insertBefore( cobblerElement, document.childNodes[2].childNodes[1])
            # document.childNodes[1].insertBefore( cobblerElement, document.childNodes[1].childNodes[0])

        name = profile.name
        if system is not None:
            name = system.name

        if self.settings.run_install_triggers:
            # notify cobblerd when we start/finished the installation
            self.addAutoYaSTScript(document, "pre-scripts", runpre % (srv, what, name))
            self.addAutoYaSTScript(document, "init-scripts", runpost % (srv, what, name))

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
                yumopts = ''
                for opt in repo_obj.yumopts:
                    # filter invalid values to the repo statement in automatic installation files

                    if opt in ['exclude', 'include']:
                        value = repo_obj.yumopts[opt].replace(' ', ',')
                        yumopts = yumopts + " --%spkgs=%s" % (opt, value)
                    elif not opt.lower() in validate.AUTOINSTALL_REPO_BLACKLIST:
                        yumopts += " %s=%s" % (opt, repo_obj.yumopts[opt])
                if 'enabled' not in repo_obj.yumopts or repo_obj.yumopts['enabled'] == '1':
                    if repo_obj.mirror_locally:
                        baseurl = "http://%s/cobbler/repo_mirror/%s" % (blended["http_server"], repo_obj.name)
                        if baseurl not in included:
                            buf += "repo --name=%s --baseurl=%s\n" % (repo_obj.name, baseurl)
                        included[baseurl] = 1
                    else:
                        if repo_obj.mirror not in included:
                            buf += "repo --name=%s --baseurl=%s %s\n" % (repo_obj.name, repo_obj.mirror, yumopts)
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
        for x in source_repos:
            count += 1
            if not x[1] in included:
                buf += "repo --name=source-%s --baseurl=%s\n" % (count, x[1])
                included[x[1]] = 1

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
        if is_profile:
            url = "http://%s/cblr/svc/op/yum/profile/%s" % (blended["http_server"], obj.name)
        else:
            url = "http://%s/cblr/svc/op/yum/system/%s" % (blended["http_server"], obj.name)

        return "curl \"%s\" --output /etc/yum.repos.d/cobbler-config.repo\n" % (url)

    def generate_autoinstall_for_system(self, sys_name) -> str:
        """
        Generate an autoinstall config or script for a system.

        :param sys_name: The system name to generate an autoinstall script for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the system references a missing profile.
        """
        s = self.api.find_system(name=sys_name)
        if s is None:
            return "# system not found"

        p = s.get_conceptual_parent()
        if p is None:
            raise CX("system %(system)s references missing profile %(profile)s"
                     % {"system": s.name, "profile": s.profile})

        distro = p.get_conceptual_parent()
        if distro is None:
            # this is an image parented system, no automatic installation file available
            return "# image based systems do not have automatic installation files"

        return self.generate_autoinstall(profile=p, system=s)

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
            return "# automatic installation file value missing or invalid at %s %s" % (obj_type, obj.name)

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
            meta["yum_config_stanza"] = self.generate_config_stanza(obj, (system is None))
        # FIXME: implement something similar to zypper (SUSE based distros) and apt (Debian based distros)

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(meta["kernel_options_post"])

        # add install_source_directory metavariable to autoinstall metavariables if distro is based on Debian
        if distro.breed in ["debian", "ubuntu"] and "tree" in meta:
            urlparts = urllib.parse.urlsplit(meta["tree"])
            meta["install_source_directory"] = urlparts[2]

        try:
            autoinstall_path = "%s/%s" % (self.settings.autoinstall_templates_dir, autoinstall_rel_path)
            raw_data = utils.read_file_contents(autoinstall_path)

            data = self.templar.render(raw_data, meta, None)

            return data
        except FileNotFoundError:
            error_msg = "automatic installation file %s not found at %s" \
                        % (meta["autoinstall"], self.settings.autoinstall_templates_dir)
            self.api.logger.warning(error_msg)
            return "# %s" % error_msg

    def generate_autoinstall_for_profile(self, g) -> str:
        """
        Generate an autoinstall config or script for a profile.

        :param g: The Profile to generate the script/config for.
        :return: The generated output or an error message with a human readable description.
        :raises CX: Raised in case the profile references a missing distro.
        """
        g = self.api.find_profile(name=g)
        if g is None:
            return "# profile not found"

        distro = g.get_conceptual_parent()
        if distro is None:
            raise CX("profile %(profile)s references missing distro %(distro)s"
                     % {"profile": g.name, "distro": g.distro})

        return self.generate_autoinstall(profile=g)

    def get_last_errors(self) -> list:
        """
        Returns the list of errors generated by the last template render action.

        :return: The list of error messages which are available. This may not only contain error messages related to
                 generating autoinstallation configuration and scripts.
        """
        return self.templar.last_errors
