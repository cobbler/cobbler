"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import shutil
import time
import sub_process
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

    def generate_kickstart_for_profile(self,g):

        g = self.api.find_profile(name=g)
        if g is None:
           return "# profile not found"

        distro = g.get_conceptual_parent()
        meta = utils.blender(self.api, False, g)
        if distro is None:
           raise CX(_("profile %(profile)s references missing distro %(distro)s") % { "profile" : g.name, "distro" : g.distro })
        kickstart_path = utils.find_kickstart(meta["kickstart"])
        if kickstart_path is not None and os.path.exists(kickstart_path):
            # the input is an *actual* file, hence we have to copy it
            try:
                meta = utils.blender(self.api, False, g)
                ksmeta = meta["ks_meta"]
                del meta["ks_meta"]
                meta.update(ksmeta) # make available at top level
                meta["yum_repo_stanza"] = self.generate_repo_stanza(g,True)
                meta["yum_config_stanza"] = self.generate_config_stanza(g,True)
                meta["kickstart_done"]  = self.generate_kickstart_signal(0, g, None)
                meta["kickstart_start"] = self.generate_kickstart_signal(1, g, None)
                meta["kernel_options"] = utils.hash_to_string(meta["kernel_options"])
                kfile = open(kickstart_path)
                data = self.templar.render(kfile, meta, None, g)
                kfile.close()
                return data
            except:
                traceback.print_exc() # leave this in, for now...
                msg = "err_kickstart2"
                raise CX(_("Error while rendering kickstart file"))

    def generate_kickstart_signal(self, is_pre=0, profile=None, system=None):
        """
        Do things that we do at the start/end of kickstarts...
        * start: signal the status watcher we're starting
        * end:   signal the status watcher we're done
        * end:   disable PXE if needed
        * end:   save the original kickstart file for debug
        """

        nopxe = "\nwget \"http://%s/cblr/svc/?op=nopxe&system=%s\" -O /dev/null"
        saveks = "\nwget \"http://%s/cblr/svc/?op=ks&%s=%s\" -O /root/cobbler.ks"
        runpost = "\nwget \"http://%s/cblr/svc/?op=trig&mode=post&%s=%s\" -O /dev/null"
        runpre  = "\nwget \"http://%s/cblr/svc/?op=trig&mode=pre&%s=%s\" -O /dev/null"

        what = "profile"
        blend_this = profile
        if system:
            what = "system"
            blend_this = system

        blended = utils.blender(self.api, False, blend_this)
        kickstart = blended.get("kickstart",None)

        buf = ""
        srv = blended["http_server"]
        if system is not None:
            if not is_pre:
                if str(self.settings.pxe_just_once).upper() in [ "1", "Y", "YES", "TRUE" ]:
                    buf = buf + nopxe % (srv, system.name)
                if kickstart and os.path.exists(kickstart):
                    buf = buf + saveks % (srv, "system", system.name)
                if self.settings.run_install_triggers:
                    buf = buf + runpost % (srv, what, system.name)
            else:
                if self.settings.run_install_triggers:
                    buf = buf + runpre % (srv, what, system.name)

        else:
            if not is_pre:
                if kickstart and os.path.exists(kickstart):
                    buf = buf + saveks % (srv, "profile", profile.name)
                if self.settings.run_install_triggers:
                    buf = buf + runpost % (srv, what, profile.name) 
            else:
                if self.settings.run_install_triggers:
                    buf = buf + runpre % (srv, what, profile.name) 

        return buf

    def generate_repo_stanza(self, obj, is_profile=True):

        """
        Automatically attaches yum repos to profiles/systems in kickstart files
        that contain the magic $yum_repo_stanza variable.
        """

        buf = ""
        blended = utils.blender(self.api, False, obj)
        configs = self.get_repo_filenames(obj,is_profile)
        repos = self.repos

        for c in configs:
           name = c.split("/")[-1].replace(".repo","")
           (is_core, baseurl) = self.analyze_repo_config(c)
           for repo in repos:
               if repo.name == name:
                   if not repo.yumopts.has_key('enabled') or repo.yumopts['enabled'] == '1':
                       buf = buf + "repo --name=%s --baseurl=%s\n" % (name, baseurl)
        return buf

    def analyze_repo_config(self, filename):
        fd = open(filename)
        data = fd.read()
        lines = data.split("\n")
        ret = False
        baseurl = None
        for line in lines:
            if line.find("ks_mirror") != -1:
                ret = True
            if line.find("baseurl") != -1:
                first, baseurl = line.split("=")
        fd.close()
        return (ret, baseurl)

    def get_repo_baseurl(self, server, repo_name, is_repo_mirror=True):
        """
        Construct the URL to a repo definition.
        """
        if is_repo_mirror:
            return "http://%s/cobbler/repo_mirror/%s" % (server, repo_name)
        else:
            return "http://%s/cobbler/ks_mirror/config/%s" % (server, repo_name)

    def get_repo_filenames(self, obj, is_profile=True):
        """
        For a given object, return the paths to repo configuration templates
        that will be used to generate per-object repo configuration files and
        baseurls
        """        

        blended = utils.blender(self.api, False, obj)
        urlseg = self.get_repo_segname(is_profile)

        topdir = "%s/%s/%s/*.repo" % (self.settings.webdir, urlseg, blended["name"])
        files = glob.glob(topdir)
        return files


    def get_repo_segname(self, is_profile):
        if is_profile:
           return "repos_profile"
        else:
           return "repos_system"


    def generate_config_stanza(self, obj, is_profile=True):

        """
        Add in automatic to configure /etc/yum.repos.d on the remote system
        if the kickstart file contains the magic $yum_config_stanza.
        """

        if not self.settings.yum_post_install_mirror:
           return ""

        urlseg = self.get_repo_segname(is_profile)

        distro = obj.get_conceptual_parent()
        if not is_profile:
           distro = distro.get_conceptual_parent()

        blended = utils.blender(self.api, False, obj)
        configs = self.get_repo_filenames(obj, is_profile)
        buf = ""
 
        # for each kickstart template we have rendered ...
        for c in configs:

           name = c.split("/")[-1].replace(".repo","")
           # add the line to create the yum config file on the target box
           conf = self.get_repo_config_file(blended["http_server"],urlseg,blended["name"],name)
           buf = buf + "wget \"%s\" --output-document=/etc/yum.repos.d/%s.repo\n" % (conf, name)    

        return buf

    def get_repo_config_file(self,server,urlseg,obj_name,repo_name):
        """
        Construct the URL to a repo config file that is usable in kickstart
        for use with yum.  This is different than the templates cobbler reposync
        creates, as this file will allow the server to migrate and have different
        variables for different subnets/profiles/etc.
        """ 
        return "http://%s/cblr/%s/%s/%s.repo" % (server,urlseg,obj_name,repo_name)

    def generate_kickstart_for_system(self,s):


        s = self.api.find_system(name=s)
        if s is None:
            return "# system not found"

        profile = s.get_conceptual_parent()
        if profile is None:
            raise CX(_("system %(system)s references missing profile %(profile)s") % { "system" : s.name, "profile" : s.profile })
        distro = profile.get_conceptual_parent()
        meta = utils.blender(self.api, False, s)
        kickstart_path = utils.find_kickstart(meta["kickstart"])
        if kickstart_path and os.path.exists(kickstart_path):
            try:
                ksmeta = meta["ks_meta"]
                del meta["ks_meta"]
                meta.update(ksmeta) # make available at top level
                meta["yum_repo_stanza"] = self.generate_repo_stanza(s, False)
                meta["yum_config_stanza"] = self.generate_config_stanza(s, False)
                meta["kickstart_done"]  = self.generate_kickstart_signal(0, profile, s)
                meta["kickstart_start"] = self.generate_kickstart_signal(1, profile, s)
                meta["kernel_options"] = utils.hash_to_string(meta["kernel_options"])
                kfile = open(kickstart_path)
                data = self.templar.render(kfile, meta, None, s)
                kfile.close()
                return data
            except:
                traceback.print_exc()
                raise CX(_("Error templating file"))

