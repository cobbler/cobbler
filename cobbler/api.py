"""
python API module for Cobbler
see source for cobbler.py, or pydoc, for example usage.
CLI apps and daemons should import api.py, and no other cobbler code.

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

import yaml
import config
import utils
import action_sync
import action_check
import action_reposync
import action_status
import action_validate
import action_buildiso
import action_replicate
import action_acl
import action_report
import action_power
import action_log
import action_hardlink
import action_dlcontent
from cexceptions import *
try:
    import subprocess as sub_process
except:
    import sub_process
import module_loader
import kickgen
import yumgen
import pxegen
from utils import _

import logging
import time
import random
import os
import xmlrpclib
import traceback
import exceptions
import clogger

import item_distro
import item_profile
import item_system
import item_repo
import item_image
import item_mgmtclass
import item_package
import item_file

ERROR = 100
INFO  = 10
DEBUG = 5

# FIXME: add --quiet depending on if not --verbose?
RSYNC_CMD =  "rsync -a %s '%s' %s --exclude-from=/etc/cobbler/rsync.exclude --progress"

# notes on locking:
# BootAPI is a singleton object
# the XMLRPC variants allow 1 simultaneous request
# therefore we flock on /etc/cobbler/settings for now
# on a request by request basis.

class BootAPI:

    __shared_state = {}
    __has_loaded = False

    # ===========================================================

    def __init__(self, is_cobblerd=False):
        """
        Constructor
        """

        # FIXME: this should be switchable through some simple system

        self.__dict__ = BootAPI.__shared_state
        self.perms_ok = False
        if not BootAPI.__has_loaded:

            if os.path.exists("/etc/cobbler/use.couch"):
                 self.use_couch = True
            else:
                 self.use_couch = False

            # NOTE: we do not log all API actions, because
            # a simple CLI invocation may call adds and such
            # to load the config, which would just fill up
            # the logs, so we'll do that logging at CLI
            # level (and remote.py web service level) instead.

            random.seed()
            self.is_cobblerd = is_cobblerd

            try:
                self.logger = clogger.Logger("/var/log/cobbler/cobbler.log")
            except CX:
                # return to CLI/other but perms are not valid
                # perms_ok is False
                return

            # FIMXE: conslidate into 1 server instance

            self.selinux_enabled = utils.is_selinux_enabled()
            self.dist = utils.check_dist()
            self.os_version = utils.os_release()

            BootAPI.__has_loaded   = True

            module_loader.load_modules()

            self._config         = config.Config(self)
            self.deserialize()

            self.authn = self.get_module_from_file(
                "authentication",
                "module",
                "authn_configfile"
            )
            self.authz  = self.get_module_from_file(
                "authorization",
                "module",
                "authz_allowall"
            )
        
            # FIXME: pass more loggers around, and also see that those
            # using things via tasks construct their own kickgen/yumgen/
            # pxegen versus reusing this one, which has the wrong logger
            # (most likely) for background tasks.

            self.kickgen = kickgen.KickGen(self._config)
            self.yumgen  = yumgen.YumGen(self._config)
            self.pxegen  = pxegen.PXEGen(self._config, logger=self.logger)
            self.logger.debug("API handle initialized")
            self.perms_ok = True

    # ==========================================================

    def is_selinux_enabled(self):
        """
        Returns whether selinux is enabled on the cobbler server.
        We check this just once at cobbler API init time, because
        a restart is required to change this; this does /not/ check
        enforce/permissive, nor does it need to.
        """
        return self.selinux_enabled

    def is_selinux_supported(self):
        """
        Returns whether or not the OS is sufficient enough
        to run with SELinux enabled (currently EL 5 or later).
        """
        self.dist
        if self.dist == "redhat" and self.os_version < 5:
           # doesn't support public_content_t
           return False 
        return True

    # ==========================================================

    def last_modified_time(self):
        """
        Returns the time of the last modification to cobbler, made by any
        API instance, regardless of the serializer type.
        """
        if not os.path.exists("/var/lib/cobbler/.mtime"):
            old = os.umask(0x777)
            fd = open("/var/lib/cobbler/.mtime","w")
            fd.write("0")
            fd.close()
            os.umask(old)
            return 0
        fd = open("/var/lib/cobbler/.mtime")
        data = fd.read().strip()
        return float(data)

    # ==========================================================

    def log(self,msg,args=None,debug=False):
        if debug:
            logger = self.logger.debug
        else:
            logger = self.logger.info 
        if args is None:
            logger("%s" % msg)
        else:
            logger("%s; %s" % (msg, str(args)))

    # ==========================================================

    def version(self, extended=False):
        """
        What version is cobbler?

        If extended == False, returns a float for backwards compatibility
         
        If extended == True, returns a dict:

            gitstamp      -- the last git commit hash
            gitdate       -- the last git commit date on the builder machine
            builddate     -- the time of the build
            version       -- something like "1.3.2"
            version_tuple -- something like [ 1, 3, 2 ]
        """
        fd = open("/etc/cobbler/version")
        ydata = fd.read()
        fd.close()
        data = yaml.load(ydata)
        if not extended:
            # for backwards compatibility and use with koan's comparisons
            elems = data["version_tuple"] 
            return int(elems[0]) + 0.1*int(elems[1]) + 0.001*int(elems[2])
        else:
            return data

    # ==========================================================

    def clear(self):
        """
        Forget about current list of profiles, distros, and systems
        # FIXME: is this used anymore?
        """
        return self._config.clear()

    def __cmp(self,a,b):
        return cmp(a.name,b.name)
    # ==========================================================

    def get_item(self, what, name):
        self.log("get_item",[what,name],debug=True)
        item = self._config.get_items(what).get(name)
        self.log("done with get_item",[what,name],debug=True)
        return item #self._config.get_items(what).get(name)

    # =============================================================

    def get_items(self, what):
        self.log("get_items",[what],debug=True)
        items = self._config.get_items(what)
        self.log("done with get_items",[what],debug=True)
        return items #self._config.get_items(what)
    
    def distros(self):
        """
        Return the current list of distributions
        """
        return self.get_items("distro")

    def profiles(self):
        """
        Return the current list of profiles
        """
        return self.get_items("profile")

    def systems(self):
        """
        Return the current list of systems
        """
        return self.get_items("system")

    def repos(self):
        """
        Return the current list of repos
        """
        return self.get_items("repo")

    def images(self):
        """
        Return the current list of images
        """
        return self.get_items("image")

    def settings(self):
        """
        Return the application configuration
        """
        return self._config.settings()
    
    def mgmtclasses(self):
        """
        Return the current list of mgmtclasses
        """
        return self.get_items("mgmtclass")
    
    def packages(self):
        """
        Return the current list of packages
        """
        return self.get_items("package")
    
    def files(self):
        """
        Return the current list of files
        """
        return self.get_items("file")

    # =======================================================================

    def update(self):
        """
        This can be called is no longer used by cobbler.
        And is here to just avoid breaking older scripts.
        """
        return True
    
    # ========================================================================

    def copy_item(self, what, ref, newname, logger=None):
        self.log("copy_item(%s)"%what,[ref.name, newname])
        return self.get_items(what).copy(ref,newname,logger=logger)

    def copy_distro(self, ref, newname):
        return self.copy_item("distro", ref, newname, logger=None)

    def copy_profile(self, ref, newname):
        return self.copy_item("profile", ref, newname, logger=None)

    def copy_system(self, ref, newname):
        return self.copy_item("system", ref, newname, logger=None)

    def copy_repo(self, ref, newname):
        return self.copy_item("repo", ref, newname, logger=None)
    
    def copy_image(self, ref, newname):
        return self.copy_item("image", ref, newname, logger=None)
    
    def copy_mgmtclass(self, ref, newname):
        return self.copy_item("mgmtclass", ref, newname, logger=None)
    
    def copy_package(self, ref, newname):
        return self.copy_item("package", ref, newname, logger=None)
    
    def copy_file(self, ref, newname):
        return self.copy_item("file", ref, newname, logger=None)

    # ==========================================================================

    def remove_item(self, what, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        if isinstance(what, basestring):
            if isinstance(ref, basestring):
                ref = self.get_item(what, ref)
                if ref is None:
                    return # nothing to remove
        self.log("remove_item(%s)" % what, [ref.name])
        return self.get_items(what).remove(ref.name, recursive=recursive, with_delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_distro(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("distro", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)
    
    def remove_profile(self,ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("profile", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_system(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("system", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_repo(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("repo", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_image(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("image", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)
    
    def remove_mgmtclass(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("mgmtclass", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)
    
    def remove_package(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("package", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)
    
    def remove_file(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        return self.remove_item("file", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    # ==========================================================================

    def rename_item(self, what, ref, newname, logger=None):
        self.log("rename_item(%s)"%what,[ref.name,newname])
        return self.get_items(what).rename(ref,newname,logger=logger)

    def rename_distro(self, ref, newname, logger=None):
        return self.rename_item("distro", ref, newname, logger=logger)

    def rename_profile(self, ref, newname, logger=None):
        return self.rename_item("profile", ref, newname, logger=logger)

    def rename_system(self, ref, newname, logger=None):
        return self.rename_item("system", ref, newname, logger=logger)

    def rename_repo(self, ref, newname, logger=None):
        return self.rename_item("repo", ref, newname, logger=logger)
    
    def rename_image(self, ref, newname, logger=None):
        return self.rename_item("image", ref, newname, logger=logger)
    
    def rename_mgmtclass(self, ref, newname, logger=None):
        return self.rename_item("mgmtclass", ref, newname, logger=logger)
    
    def rename_package(self, ref, newname, logger=None):
        return self.rename_item("package", ref, newname, logger=logger)
    
    def rename_file(self, ref, newname, logger=None):
        return self.rename_item("file", ref, newname, logger=logger)

    # ==========================================================================
   
    # FIXME: add a new_item method

    def new_distro(self,is_subobject=False):
        self.log("new_distro",[is_subobject])
        return self._config.new_distro(is_subobject=is_subobject)

    def new_profile(self,is_subobject=False):
        self.log("new_profile",[is_subobject])
        return self._config.new_profile(is_subobject=is_subobject)
    
    def new_system(self,is_subobject=False):
        self.log("new_system",[is_subobject])
        return self._config.new_system(is_subobject=is_subobject)

    def new_repo(self,is_subobject=False):
        self.log("new_repo",[is_subobject])
        return self._config.new_repo(is_subobject=is_subobject)
    
    def new_image(self,is_subobject=False):
        self.log("new_image",[is_subobject])
        return self._config.new_image(is_subobject=is_subobject)
    
    def new_mgmtclass(self,is_subobject=False):
        self.log("new_mgmtclass",[is_subobject])
        return self._config.new_mgmtclass(is_subobject=is_subobject)
    
    def new_package(self,is_subobject=False):
        self.log("new_package",[is_subobject])
        return self._config.new_package(is_subobject=is_subobject)
    
    def new_file(self,is_subobject=False):
        self.log("new_file",[is_subobject])
        return self._config.new_file(is_subobject=is_subobject)

    # ==========================================================================

    def add_item(self, what, ref, check_for_duplicate_names=False, save=True,logger=None):
        self.log("add_item(%s)"%what,[ref.name])
        return self.get_items(what).add(ref,check_for_duplicate_names=check_for_duplicate_names,save=save,logger=logger)

    def add_distro(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        return self.add_item("distro", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)

    def add_profile(self, ref, check_for_duplicate_names=False,save=True, logger=None):
        return self.add_item("profile", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)

    def add_system(self, ref, check_for_duplicate_names=False, check_for_duplicate_netinfo=False, save=True, logger=None):
        return self.add_item("system", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)

    def add_repo(self, ref, check_for_duplicate_names=False,save=True,logger=None):
        return self.add_item("repo", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)

    def add_image(self, ref, check_for_duplicate_names=False,save=True, logger=None):
        return self.add_item("image", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)
    
    def add_mgmtclass(self, ref, check_for_duplicate_names=False,save=True, logger=None):
        return self.add_item("mgmtclass", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)
    
    def add_package(self, ref, check_for_duplicate_names=False,save=True, logger=None):
        return self.add_item("package", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)
    
    def add_file(self, ref, check_for_duplicate_names=False,save=True, logger=None):
        return self.add_item("file", ref, check_for_duplicate_names=check_for_duplicate_names, save=save,logger=logger)

    # ==========================================================================

    # FIXME: find_items should take all the arguments the other find
    # methods do.

    def find_items(self, what, criteria=None):
        self.log("find_items",[what])
        # defaults
        if criteria is None:
            criteria={}
        items=self._config.get_items(what)
        # empty criteria returns everything
        if criteria == {}:
            res=items
        else:
            res=items.find(return_list=True, no_errors=False, **criteria)
        return res


    def find_distro(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.distros().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)
        
    def find_profile(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.profiles().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_system(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.systems().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_repo(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.repos().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_image(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.images().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)
    
    def find_mgmtclass(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.mgmtclasses().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)
    
    def find_package(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.packages().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)
    
    def find_file(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._config.files().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    # ==========================================================================

    def __since(self,mtime,collector,collapse=False):
        """
        Called by get_*_since functions.
        """
        results1 = collector()
        results2 = []
        for x in results1:
           if x.mtime == 0 or x.mtime >= mtime:
              if not collapse:
                  results2.append(x)
              else:
                  results2.append(x.to_datastruct())
        return results2

    def get_distros_since(self,mtime,collapse=False):
        """
        Returns distros modified since a certain time (in seconds since Epoch)
        collapse=True specifies returning a hash instead of objects.
        """
        return self.__since(mtime,self.distros,collapse=collapse)

    def get_profiles_since(self,mtime,collapse=False):
        return self.__since(mtime,self.profiles,collapse=collapse)

    def get_systems_since(self,mtime,collapse=False):
        return self.__since(mtime,self.systems,collapse=collapse)

    def get_repos_since(self,mtime,collapse=False):
        return self.__since(mtime,self.repos,collapse=collapse)

    def get_images_since(self,mtime,collapse=False):
        return self.__since(mtime,self.images,collapse=collapse)
    
    def get_mgmtclasses_since(self,mtime,collapse=False):
        return self.__since(mtime,self.mgmtclasses,collapse=collapse)
    
    def get_packages_since(self,mtime,collapse=False):
        return self.__since(mtime,self.packages,collapse=collapse)
    
    def get_files_since(self,mtime,collapse=False):
        return self.__since(mtime,self.files,collapse=collapse)

    # ==========================================================================

    def dump_vars(self, obj, format=False):
        return obj.dump_vars(format)

    # ==========================================================================

    def auto_add_repos(self):
        """
        Import any repos this server knows about and mirror them.
        Credit: Seth Vidal.
        """
        self.log("auto_add_repos")
        try:
            import yum
        except:
            raise CX(_("yum is not installed"))

        version = yum.__version__
        (a,b,c) = version.split(".")
        version = a* 1000 + b*100 + c
        if version < 324:
            raise CX(_("need yum > 3.2.4 to proceed"))

        base = yum.YumBase()
        base.doRepoSetup()
        repos = base.repos.listEnabled()
        if len(repos) == 0:
            raise CX(_("no repos enabled/available -- giving up."))

        for repo in repos:
            url = repo.urls[0]
            cobbler_repo = self.new_repo()
            auto_name = repo.name.replace(" ","")
            # FIXME: probably doesn't work for yum-rhn-plugin ATM
            cobbler_repo.set_mirror(url)
            cobbler_repo.set_name(auto_name)
            print "auto adding: %s (%s)" % (auto_name, url)
            self._config.repos().add(cobbler_repo,save=True)

        # run cobbler reposync to apply changes
        return True 

    # ==========================================================================

    def get_repo_config_for_profile(self,obj):
        return self.yumgen.get_yum_config(obj,True)
    
    def get_repo_config_for_system(self,obj):
        return self.yumgen.get_yum_config(obj,False)

    # ==========================================================================

    def get_template_file_for_profile(self,obj,path):
        template_results = self.pxegen.write_templates(obj,False,path)
        if template_results.has_key(path):
            return template_results[path]
        else:
            return "# template path not found for specified profile"

    def get_template_file_for_system(self,obj,path):
        template_results = self.pxegen.write_templates(obj,False,path)
        if template_results.has_key(path):
            return template_results[path]
        else:
            return "# template path not found for specified system"

    # ==========================================================================

    def generate_kickstart(self,profile,system):
        self.log("generate_kickstart")
        if system:
            return self.kickgen.generate_kickstart_for_system(system)
        else:
            return self.kickgen.generate_kickstart_for_profile(profile) 

    # ==========================================================================

    def check(self, logger=None):
        """
        See if all preqs for network booting are valid.  This returns
        a list of strings containing instructions on things to correct.
        An empty list means there is nothing to correct, but that still
        doesn't mean there are configuration errors.  This is mainly useful
        for human admins, who may, for instance, forget to properly set up
        their TFTP servers for PXE, etc.
        """
        self.log("check")
        check = action_check.BootCheck(self._config, logger=logger)
        return check.run()

    # ==========================================================================

    def dlcontent(self,force=False,logger=None):
        """
        Downloads bootloader content that may not be avialable in packages
        for the given arch, ex: if installing on PPC, get syslinux. If installing
        on x86_64, get elilo, etc.
        """
        # FIXME: teach code that copies it to grab from the right place
        self.log("dlcontent")
        grabber = action_dlcontent.ContentDownloader(self._config, logger=logger)
        return grabber.run(force)

    # ==========================================================================

    def validateks(self, logger=None):
        """
        Use ksvalidator (from pykickstart, if available) to determine
        whether the cobbler kickstarts are going to be (likely) well
        accepted by Anaconda.  Presence of an error does not indicate
        the kickstart is bad, only that the possibility exists.  ksvalidator
        is not available on all platforms and can not detect "future"
        kickstart format correctness.
        """
        self.log("validateks")
        validator = action_validate.Validate(self._config, logger=logger)
        return validator.run()

    # ==========================================================================

    def sync(self,verbose=False, logger=None):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        self.log("sync")
        sync = self.get_sync(verbose=verbose, logger=logger)
        return sync.run()

    # ==========================================================================

    def get_sync(self,verbose=False,logger=None):
        self.dhcp = self.get_module_from_file(
           "dhcp",
           "module",
           "manage_isc"
        ).get_manager(self._config,logger)
        self.dns = self.get_module_from_file(
           "dns",
           "module",
           "manage_bind"
        ).get_manager(self._config,logger)
        self.tftpd = self.get_module_from_file(
           "tftpd",
           "module",
           "in_tftpd",
        ).get_manager(self._config,logger)

        return action_sync.BootSync(self._config,dhcp=self.dhcp,dns=self.dns,tftpd=self.tftpd,verbose=verbose,logger=logger)

    # ==========================================================================

    def reposync(self, name=None, tries=1, nofail=False, logger=None):
        """
        Take the contents of /var/lib/cobbler/repos and update them --
        or create the initial copy if no contents exist yet.
        """
        self.log("reposync",[name])
        reposync = action_reposync.RepoSync(self._config, tries=tries, nofail=nofail, logger=logger)
        return reposync.run(name)

    # ==========================================================================

    def status(self,mode,logger=None):
        statusifier = action_status.BootStatusReport(self._config,mode,logger=logger)
        return statusifier.run()

    # ==========================================================================

    def import_tree(self,mirror_url,mirror_name,network_root=None,kickstart_file=None,rsync_flags=None,arch=None,breed=None,os_version=None,logger=None):
        """
        Automatically import a directory tree full of distribution files.
        mirror_url can be a string that represents a path, a user@host 
        syntax for SSH, or an rsync:// address.  If mirror_url is a 
        filesystem path and mirroring is not desired, set network_root 
        to something like "nfs://path/to/mirror_url/root" 
        """
        self.log("import_tree",[mirror_url, mirror_name, network_root, kickstart_file, rsync_flags])

        # both --import and --name are required arguments
        if mirror_url is None:
            self.log("import failed.  no --path specified")
            return False
        if mirror_name is None:
            self.log("import failed.  no --name specified")
            return False

        path = os.path.normpath("%s/ks_mirror/%s" % (self.settings().webdir, mirror_name))
        if arch is not None:
            arch = arch.lower()
            if arch == "x86":
                # be consistent
                arch = "i386"
            path += ("-%s" % arch)

        if network_root is None:
            # we need to mirror (copy) the files
            self.log("importing from a network location, running rsync to fetch the files first")

            utils.mkdir(path)

            # prevent rsync from creating the directory name twice
            # if we are copying via rsync

            if not mirror_url.endswith("/"):
                mirror_url = "%s/" % mirror_url

            if mirror_url.startswith("http://") or mirror_url.startswith("ftp://") or mirror_url.startswith("nfs://"):
                # http mirrors are kind of primative.  rsync is better.
                # that's why this isn't documented in the manpage and we don't support them.
                # TODO: how about adding recursive FTP as an option?
                self.log("unsupported protocol")
                return False
            else:
                # good, we're going to use rsync..
                # we don't use SSH for public mirrors and local files.
                # presence of user@host syntax means use SSH
                spacer = ""
                if not mirror_url.startswith("rsync://") and not mirror_url.startswith("/"):
                    spacer = ' -e "ssh" '
                rsync_cmd = RSYNC_CMD
                if rsync_flags:
                    rsync_cmd = rsync_cmd + " " + rsync_flags

                # kick off the rsync now

                utils.run_this(rsync_cmd, (spacer, mirror_url, path), self.logger)

        else:

            # rather than mirroring, we're going to assume the path is available
            # over http, ftp, and nfs, perhaps on an external filer.  scanning still requires
            # --mirror is a filesystem path, but --available-as marks the network path

            if not os.path.exists(mirror_url):
                self.log("path does not exist: %s" % mirror_url)
                return False

            # find the filesystem part of the path, after the server bits, as each distro
            # URL needs to be calculated relative to this.

            if not network_root.endswith("/"):
                network_root = network_root + "/"
            path = os.path.normpath( mirror_url )
            valid_roots = [ "nfs://", "ftp://", "http://" ]
            for valid_root in valid_roots:
                if network_root.startswith(valid_root):
                    break
            else:
                self.log("Network root given to --available-as must be nfs://, ftp://, or http://")
                return False

            if network_root.startswith("nfs://"):
                try:
                    (a,b,rest) = network_root.split(":",3)
                except:
                    self.log("Network root given to --available-as is missing a colon, please see the manpage example.")
                    return False

        importer_modules = self.get_modules_in_category("manage/import")
        for importer_module in importer_modules:
            manager = importer_module.get_import_manager(self._config,logger)
            try:
                (found,pkgdir) = manager.check_for_signature(path,breed)
                if found: 
                    self.log("running import manager: %s" % manager.what())
                    return manager.run(pkgdir,mirror_name,path,network_root,kickstart_file,rsync_flags,arch,breed,os_version)
            except:
                self.log("an error occured while running the import manager")
                continue
        self.log("No import managers found a valid signature at the location specified")
        return False

    # ==========================================================================

    def acl_config(self,adduser=None,addgroup=None,removeuser=None,removegroup=None, logger=None):
        """
        Configures users/groups to run the cobbler CLI as non-root.
        Pass in only one option at a time.  Powers "cobbler aclconfig"
        """
        acl = action_acl.AclConfig(self._config, logger)
        return acl.run(
            adduser=adduser,
            addgroup=addgroup,
            removeuser=removeuser,
            removegroup=removegroup
        )

    # ==========================================================================

    def serialize(self):
        """
        Save the config file(s) to disk.
        Cobbler internal use only.
        """
        return self._config.serialize()

    def deserialize(self):
        """
        Load the current configuration from config file(s)
        Cobbler internal use only.
        """
        return self._config.deserialize()

    def deserialize_raw(self,collection_name):
        """
        Get the collection back just as raw data.
        Cobbler internal use only.
        """
        return self._config.deserialize_raw(collection_name)

    def deserialize_item_raw(self,collection_name,obj_name):
        """
        Get an object back as raw data.
        Can be very fast for shelve or catalog serializers
        Cobbler internal use only.
        """
        return self._config.deserialize_item_raw(collection_name,obj_name)

    # ==========================================================================

    def get_module_by_name(self,module_name):
        """
        Returns a loaded cobbler module named 'name', if one exists, else None.
        Cobbler internal use only.
        """
        return module_loader.get_module_by_name(module_name)

    def get_module_from_file(self,section,name,fallback=None):
        """
        Looks in /etc/cobbler/modules.conf for a section called 'section'
        and a key called 'name', and then returns the module that corresponds
        to the value of that key.
        Cobbler internal use only.
        """
        return module_loader.get_module_from_file(section,name,fallback)

    def get_modules_in_category(self,category):
        """
        Returns all modules in a given category, for instance "serializer", or "cli".
        Cobbler internal use only.
        """
        return module_loader.get_modules_in_category(category)

    # ==========================================================================

    def authenticate(self,user,password):
        """
        (Remote) access control.
        Cobbler internal use only.
        """
        rc = self.authn.authenticate(self,user,password)
        self.log("authenticate",[user,rc])
        return rc 

    def authorize(self,user,resource,arg1=None,arg2=None):
        """
        (Remote) access control.
        Cobbler internal use only.
        """
        rc = self.authz.authorize(self,user,resource,arg1,arg2)
        self.log("authorize",[user,resource,arg1,arg2,rc],debug=True)
        return rc

    # ==========================================================================

    def build_iso(self,iso=None,profiles=None,systems=None,buildisodir=None,distro=None,standalone=None,source=None, exclude_dns=None, logger=None):
        builder = action_buildiso.BuildIso(self._config, logger=logger)
        return builder.run(
           iso=iso, profiles=profiles, systems=systems, buildisodir=buildisodir, distro=distro, standalone=standalone, source=source, exclude_dns=exclude_dns
        )

    # ==========================================================================

    def hardlink(self, logger=None):
        linker = action_hardlink.HardLinker(self._config, logger=logger)
        return linker.run()

    # ==========================================================================

    def replicate(self, cobbler_master = None, distro_patterns="", profile_patterns="", system_patterns="", repo_patterns="", image_patterns="",
                  mgmtclass_patterns=None, package_patterns=None, file_patterns=None, prune=False, omit_data=False, sync_all=False, logger=None):
        """
        Pull down data/configs from a remote cobbler server that is a master to this server.
        """
        replicator = action_replicate.Replicate(self._config, logger=logger)
        return replicator.run(
              cobbler_master       = cobbler_master,
              distro_patterns      = distro_patterns,
              profile_patterns     = profile_patterns,
              system_patterns      = system_patterns,
              repo_patterns        = repo_patterns,
              image_patterns       = image_patterns,
              mgmtclass_patterns   = mgmtclass_patterns,
              package_patterns     = package_patterns,
              file_patterns        = file_patterns,
              prune                = prune,
              omit_data            = omit_data,
              sync_all             = sync_all
        )

    # ==========================================================================

    def report(self, report_what = None, report_name = None, report_type = None, report_fields = None, report_noheaders = None):
        """
        Report functionality for cobbler
        """
        reporter = action_report.Report(self._config)
        return reporter.run(report_what = report_what, report_name = report_name,\
                            report_type = report_type, report_fields = report_fields,\
                            report_noheaders = report_noheaders)

    # ==========================================================================

    def get_kickstart_templates(self):
        return utils.get_kickstar_templates(self)

    # ==========================================================================

    def power_on(self, system, user=None, password=None, logger=None):
        """
        Powers up a system that has power management configured.
        """
        return action_power.PowerTool(self._config,system,self,user,password,logger=logger).power("on")

    def power_off(self, system, user=None, password=None, logger=None):
        """
        Powers down a system that has power management configured.
        """
        return action_power.PowerTool(self._config,system,self,user,password,logger=logger).power("off")

    def reboot(self,system, user=None, password=None, logger=None):
        """
        Cycles power on a system that has power management configured.
        """
        self.power_off(system, user, password, logger=logger)
        time.sleep(5)
        return self.power_on(system, user, password, logger=logger)

    def power_status(self, system, user=None, password=None, logger=None):
        """
        Returns the power status for a system that has power management configured.

        @return: 0  the system is powered on, False if it's not or None on error
        """
        return action_power.PowerTool(self._config, system, self, user, password, logger = logger).power("status")


    # ==========================================================================

    def clear_logs(self, system, logger=None):
        """
        Clears console and anamon logs for system
        """
        return action_log.LogTool(self._config,system,self, logger=logger).clear()

    def get_os_details(self):
        return (self.dist, self.os_version)
