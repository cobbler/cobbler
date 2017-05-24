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

import urlparse
import xml.dom.minidom

from cobbler import templar
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import FileNotFoundException, CX
from cobbler.utils import _


class AutoInstallationGen:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """
    def __init__(self, collection_mgr):
        """
        Constructor
        """
        self.collection_mgr = collection_mgr
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.templar = templar.Templar(collection_mgr)

    def createAutoYaSTScript(self, document, script, name):
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

    def generate_autoyast(self, profile=None, system=None, raw_data=None):
        self.api.logger.info("autoyast XML file found. Checkpoint: profile=%s system=%s" % (profile, system))
        nopxe = "\ncurl \"http://%s/cblr/svc/op/nopxe/system/%s\" > /dev/null"
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

        # do we already have the #raw comment in the XML? (addComment = 0 means, don't add #raw comment)
        addComment = 1
        for node in document.childNodes[1].childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == "cobbler":
                addComment = 0
                break

        # add some cobbler information to the XML file
        # maybe that should be configureable
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

            # FIXME: this is all broken and no longer works.
            #        this entire if block should probably not be
            #        hard-coded anyway
            # self.api.log(document.childNodes[2].childNodes)
            # document.childNodes[1].insertBefore( cobblerElement, document.childNodes[2].childNodes[1])
            # document.childNodes[1].insertBefore( cobblerElement, document.childNodes[1].childNodes[0])

        name = profile.name
        if system is not None:
            name = system.name

        if str(self.settings.pxe_just_once).upper() in ["1", "Y", "YES", "TRUE"]:
            self.addAutoYaSTScript(document, "chroot-scripts", nopxe % (srv, name))
        if self.settings.run_install_triggers:
            # notify cobblerd when we start/finished the installation
            self.addAutoYaSTScript(document, "pre-scripts", runpre % (srv, what, name))
            self.addAutoYaSTScript(document, "init-scripts", runpost % (srv, what, name))

        return document.toxml()

    def generate_repo_stanza(self, obj, is_profile=True):

        """
        Automatically attaches yum repos to profiles/systems in automatic
        installation files (kickstart files) that contain the magic
        $yum_repo_stanza variable.  This includes repo objects as well as the
        yum repos that are part of split tree installs, whose data is stored
        with the distro (example: RHEL5 imports)
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
                    # filter invalid values to the repo statement in automatic
                    # installation files

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
                # this should be a warning at another point, probably not here
                # so we'll just not list it so the automatic installation file
                # will still work as nothing will be here to read the output noise.
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

    def generate_config_stanza(self, obj, is_profile=True):

        """
        Add in automatic to configure /etc/yum.repos.d on the remote system
        if the automatic installation file (kickstart file) contains the magic
        $yum_config_stanza.
        """

        if not self.settings.yum_post_install_mirror:
            return ""

        blended = utils.blender(self.api, False, obj)
        if is_profile:
            url = "http://%s/cblr/svc/op/yum/profile/%s" % (blended["http_server"], obj.name)
        else:
            url = "http://%s/cblr/svc/op/yum/system/%s" % (blended["http_server"], obj.name)

        return "curl \"%s\" --output /etc/yum.repos.d/cobbler-config.repo\n" % (url)

    def generate_autoinstall_for_system(self, sys_name):

        s = self.api.find_system(name=sys_name)
        if s is None:
            return "# system not found"

        p = s.get_conceptual_parent()
        if p is None:
            raise CX(_("system %(system)s references missing profile %(profile)s") % {"system": s.name, "profile": s.profile})

        distro = p.get_conceptual_parent()
        if distro is None:
            # this is an image parented system, no automatic installation file available
            return "# image based systems do not have automatic installation files"

        return self.generate_autoinstall(profile=p, system=s)

    def generate_autoinstall(self, profile=None, system=None):

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
        # FIXME: implement something similar to zypper (SUSE based distros) and apt
        #        (Debian based distros)

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(meta["kernel_options_post"])

        # add install_source_directory metavariable to autoinstall metavariables
        # if distro is based on Debian
        if distro.breed in ["debian", "ubuntu"] and "tree" in meta:
            urlparts = urlparse.urlsplit(meta["tree"])
            meta["install_source_directory"] = urlparts[2]

        try:
            autoinstall_path = "%s/%s" % (self.settings.autoinstall_templates_dir, autoinstall_rel_path)
            raw_data = utils.read_file_contents(autoinstall_path, self.api.logger)

            data = self.templar.render(raw_data, meta, None, obj)

            return data
        except FileNotFoundException:
            error_msg = "automatic installation file %s not found at %s" % (meta["autoinstall"], self.settings.autoinstall_templates_dir)
            self.api.logger.warning(error_msg)
            return "# %s" % error_msg

    def generate_autoinstall_for_profile(self, g):

        g = self.api.find_profile(name=g)
        if g is None:
            return "# profile not found"

        distro = g.get_conceptual_parent()
        if distro is None:
            raise CX(_("profile %(profile)s references missing distro %(distro)s") % {"profile": g.name, "distro": g.distro})

        return self.generate_autoinstall(profile=g)

    def get_last_errors(self):
        """
        Returns the list of errors generated by
        the last template render action
        """
        return self.templar.last_errors
