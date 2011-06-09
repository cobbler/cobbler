"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import os
import os.path
import shutil
import time
import sys
import glob
import traceback
import errno

import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system

from utils import _

import xml.dom.minidom

class KickGen:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)

    def createAutoYaSTScript( self, document, script, name ):
        newScript = document.createElement("script")
        newScriptSource = document.createElement("source")
        newScriptSourceText = document.createTextNode(script)
        newScript.appendChild(newScriptSource)

        newScriptFile = document.createElement("filename")
        newScriptFileText = document.createTextNode(name)
        newScript.appendChild(newScriptFile)

        newScriptSource.appendChild(newScriptSourceText)
        newScriptFile.appendChild(newScriptFileText)
        return newScript

    def addAutoYaSTScript( self, document, type, source ):
        scripts = document.getElementsByTagName("scripts")
        if scripts.length == 0:
            newScripts = document.createElement("scripts")
            document.documentElement.appendChild( newScripts )
            scripts = document.getElementsByTagName("scripts")
        added = 0
        for stype in scripts[0].childNodes:
            if stype.nodeType == stype.ELEMENT_NODE and stype.tagName == type:
                stype.appendChild( self.createAutoYaSTScript( document, source, type+"_cobbler" ) )
                added = 1
        if added == 0:
            newChrootScripts = document.createElement( type )
            newChrootScripts.setAttribute( "config:type", "list" )
            newChrootScripts.appendChild( self.createAutoYaSTScript( document, source, type+"_cobbler" ) )
            scripts[0].appendChild( newChrootScripts )

    def generate_autoyast(self, profile=None, system=None, raw_data=None):
        self.api.logger.info("autoyast XML file found. Checkpoint: profile=%s system=%s" % (profile,system) )
        nopxe = "\nwget \"http://%s/cblr/svc/op/nopxe/system/%s\" -O /dev/null"
        runpost = "\ncurl \"http://%s/cblr/svc/op/trig/mode/post/%s/%s\" > /dev/null"
        runpre  = "\nwget \"http://%s/cblr/svc/op/trig/mode/pre/%s/%s\" -O /dev/null"

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
            #startComment = document.createComment("\ncobbler_system_name=$system_name\ncobbler_server=$server\n#raw\n")
            #endComment = document.createComment("\n#end raw\n")
            cobblerElement = document.createElement("cobbler")
            cobblerElementSystem = xml.dom.minidom.Element("system_name")
            cobblerElementProfile = xml.dom.minidom.Element("profile_name")
            if( system is not None ):
                cobblerTextSystem    = document.createTextNode(system.name)
                cobblerElementSystem.appendChild( cobblerTextSystem )
            if( profile is not None ):
                cobblerTextProfile    = document.createTextNode(profile.name)
                cobblerElementProfile.appendChild( cobblerTextProfile )

            cobblerElementServer = document.createElement("server")
            cobblerTextServer    = document.createTextNode(blended["http_server"])
            cobblerElementServer.appendChild( cobblerTextServer )

            cobblerElement.appendChild( cobblerElementServer )
            cobblerElement.appendChild( cobblerElementSystem )
            cobblerElement.appendChild( cobblerElementProfile )

            document.childNodes[1].insertBefore( cobblerElement, document.childNodes[1].childNodes[1])

        name = profile.name
        if system is not None:
            name = system.name

        if str(self.settings.pxe_just_once).upper() in [ "1", "Y", "YES", "TRUE" ]:
            self.addAutoYaSTScript( document, "chroot-scripts", nopxe % (srv, name) )
        if self.settings.run_install_triggers:
            # notify cobblerd when we start/finished the installation
            self.addAutoYaSTScript( document, "pre-scripts", runpre % ( srv, what, name ) )
            self.addAutoYaSTScript( document, "init-scripts", runpost % ( srv, what, name ) )

        return document.toxml()



    def generate_repo_stanza(self, obj, is_profile=True):

        """
        Automatically attaches yum repos to profiles/systems in kickstart files
        that contain the magic $yum_repo_stanza variable.  This includes repo
        objects as well as the yum repos that are part of split tree installs,
        whose data is stored with the distro (example: RHEL5 imports)
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
                if not repo_obj.yumopts.has_key('enabled') or repo_obj.yumopts['enabled'] == '1':
                   if repo_obj.mirror_locally:
                       baseurl = "http://%s/cobbler/repo_mirror/%s" % (blended["http_server"], repo_obj.name)
                       if not included.has_key(baseurl):
                           buf = buf + "repo --name=%s --baseurl=%s\n" % (repo_obj.name, baseurl)
                       included[baseurl] = 1
                   else:
                       if not included.has_key(repo_obj.mirror):
                           buf = buf + "repo --name=%s --baseurl=%s\n" % (repo_obj.name, repo_obj.mirror)
                       included[repo_obj.mirror] = 1
            else:
                # FIXME: what to do if we can't find the repo object that is listed?
                # this should be a warning at another point, probably not here
                # so we'll just not list it so the kickstart will still work
                # as nothing will be here to read the output noise.  Logging might
                # be useful.
                pass

        if is_profile:
            distro = obj.get_conceptual_parent()
        else:
            distro = obj.get_conceptual_parent().get_conceptual_parent()

        source_repos = distro.source_repos
        count = 0
        for x in source_repos:
            count = count + 1
            if not included.has_key(x[1]):
                buf = buf + "repo --name=source-%s --baseurl=%s\n" % (count, x[1])
                included[x[1]] = 1

        return buf

    def generate_config_stanza(self, obj, is_profile=True):

        """
        Add in automatic to configure /etc/yum.repos.d on the remote system
        if the kickstart file contains the magic $yum_config_stanza.
        """

        if not self.settings.yum_post_install_mirror:
           return ""

        blended = utils.blender(self.api, False, obj)
        if is_profile:
           url = "http://%s/cblr/svc/op/yum/profile/%s" % (blended["http_server"], obj.name)
        else:
           url = "http://%s/cblr/svc/op/yum/system/%s" % (blended["http_server"], obj.name)

        return "wget \"%s\" --output-document=/etc/yum.repos.d/cobbler-config.repo\n" % (url)

    def generate_kickstart_for_system(self, sys_name):

        s = self.api.find_system(name=sys_name)
        if s is None:
            return "# system not found"

        p = s.get_conceptual_parent()
        if p is None:
            raise CX(_("system %(system)s references missing profile %(profile)s") % { "system" : s.name, "profile" : s.profile })

        distro = p.get_conceptual_parent()
        if distro is None: 
            # this is an image parented system, no kickstart available
            return "# image based systems do not have kickstarts"

        return self.generate_kickstart(profile=p, system=s) 

    def generate_kickstart(self, profile=None, system=None):

        obj = system
        if system is None:
            obj = profile

        meta = utils.blender(self.api, False, obj)
        kickstart_path = utils.find_kickstart(meta["kickstart"])

        if not kickstart_path:
            return "# kickstart is missing or invalid: %s" % meta["kickstart"]

        ksmeta = meta["ks_meta"]
        del meta["ks_meta"]
        meta.update(ksmeta) # make available at top level
        meta["yum_repo_stanza"] = self.generate_repo_stanza(obj, (system is None))
        meta["yum_config_stanza"] = self.generate_config_stanza(obj, (system is None))
        meta["kernel_options"] = utils.hash_to_string(meta["kernel_options"])
        # meta["config_template_files"] = self.generate_template_files_stanza(g, False)

        try:
            raw_data = utils.read_file_contents(kickstart_path, self.api.logger,
                    self.settings.template_remote_kickstarts)
            if raw_data is None:
                return "# kickstart is sourced externally: %s" % meta["kickstart"]
            distro = profile.get_conceptual_parent()
            if system is not None:
                distro = system.get_conceptual_parent().get_conceptual_parent()

            data = self.templar.render(raw_data, meta, None, obj)

            if distro.breed == "suse":
                # AutoYaST profile
                data = self.generate_autoyast(profile,system,data)

            return data
        except FileNotFoundException:
            self.api.logger.warning("kickstart not found: %s" % meta["kickstart"])
            return "# kickstart not found: %s" % meta["kickstart"]

    def generate_kickstart_for_profile(self,g):

        g = self.api.find_profile(name=g)
        if g is None:
           return "# profile not found"

        distro = g.get_conceptual_parent()
        if distro is None:
           raise CX(_("profile %(profile)s references missing distro %(distro)s") % 
                   { "profile" : g.name, "distro" : g.distro })

        return self.generate_kickstart(profile=g)

    def get_last_errors(self):
        """
        Returns the list of errors generated by 
        the last template render action
        """
        return self.templar.last_errors
