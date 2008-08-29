"""
python API module for Cobbler
see source for cobbler.py, or pydoc, for example usage.
CLI apps and daemons should import api.py, and no other cobbler code.

Copyright 2006-2008, Red Hat, Inc
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

import config
import utils
import action_sync
import action_check
import action_import
import action_reposync
import action_status
import action_validate
import action_buildiso
import action_replicate
import action_acl
from cexceptions import *
import sub_process
import module_loader
import kickgen
import yumgen

import logging
import os
import fcntl
from utils import _

ERROR = 100
INFO  = 10
DEBUG = 5

# notes on locking:
# BootAPI is a singleton object
# the XMLRPC variants allow 1 simultaneous request
# therefore we flock on /etc/cobbler/settings for now
# on a request by request basis.

class BootAPI:


    __shared_state = {}
    __has_loaded = False

    def __init__(self):
        """
        Constructor
        """

        self.__dict__ = BootAPI.__shared_state
        self.perms_ok = False
        if not BootAPI.__has_loaded:

            # NOTE: we do not log all API actions, because
            # a simple CLI invocation may call adds and such
            # to load the config, which would just fill up
            # the logs, so we'll do that logging at CLI
            # level (and remote.py web service level) instead.

            try:
                self.logger = self.__setup_logger("api")
            except CX:
                # return to CLI/other but perms are not valid
                # perms_ok is False
                return

            self.logger_remote = self.__setup_logger("remote")

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
            self.kickgen = kickgen.KickGen(self._config)
            self.yumgen  = yumgen.YumGen(self._config)
            self.logger.debug("API handle initialized")
            self.perms_ok = True
 
    def __setup_logger(self,name):
        return utils.setup_logger(name)

    def log(self,msg,args=None,debug=False):
        if debug:
            logger = self.logger.debug
        else:
            logger = self.logger.info 
        if args is None:
            logger("%s" % msg)
        else:
            logger("%s; %s" % (msg, str(args)))

    def version(self):
        """
        What version is cobbler?
        Currently checks the RPM DB, which is not perfect.
        Will return "?" if not installed.
        """
        self.log("version")
        cmd = sub_process.Popen("/bin/rpm -q cobbler", stdout=sub_process.PIPE, shell=True)
        result = cmd.communicate()[0].replace("cobbler-","")
        if result.find("not installed") != -1:
            return "?"
        tokens = result[:result.rfind("-")].split(".")
        return int(tokens[0]) + 0.1 * int(tokens[1]) + 0.001 * int(tokens[2])

    def clear(self):
        """
        Forget about current list of profiles, distros, and systems
        """
        return self._config.clear()

    def __cmp(self,a,b):
        return cmp(a.name,b.name)

    def systems(self):
        """
        Return the current list of systems
        """
        return self._config.systems()

    def profiles(self):
        """
        Return the current list of profiles
        """
        return self._config.profiles()

    def distros(self):
        """
        Return the current list of distributions
        """
        return self._config.distros()

    def repos(self):
        """
        Return the current list of repos
        """
        return self._config.repos()

    def images(self):
        """
        Return the current list of images
        """
        return self._config.images()

    def settings(self):
        """
        Return the application configuration
        """
        return self._config.settings()

    def copy_distro(self, ref, newname):
        self.log("copy_distro",[ref.name, newname])
        return self._config.distros().copy(ref,newname)

    def copy_profile(self, ref, newname):
        self.log("copy_profile",[ref.name, newname])
        return self._config.profiles().copy(ref,newname)

    def copy_system(self, ref, newname):
        self.log("copy_system",[ref.name, newname])
        return self._config.systems().copy(ref,newname)

    def copy_repo(self, ref, newname):
        self.log("copy_repo",[ref.name, newname])
        return self._config.repos().copy(ref,newname)
    
    def copy_image(self, ref, newname):
        self.log("copy_image",[ref.name, newname])
        return self._config.images().copy(ref,newname)

    def remove_distro(self, ref, recursive=False):
        self.log("remove_distro",[ref.name])
        return self._config.distros().remove(ref.name, recursive=recursive)

    def remove_profile(self,ref, recursive=False):
        self.log("remove_profile",[ref.name])
        return self._config.profiles().remove(ref.name, recursive=recursive)

<<<<<<< HEAD:cobbler/api.py
    def remove_system(self,ref,recursive=False):
=======
    def remove_system(self,ref, recursive=False):
>>>>>>> devel:cobbler/api.py
        self.log("remove_system",[ref.name])
        return self._config.systems().remove(ref.name)

    def remove_repo(self, ref,recursive=False):
        self.log("remove_repo",[ref.name])
        return self._config.repos().remove(ref.name)
    
    def remove_image(self, ref):
        self.log("remove_image",[ref.name])
        return self._config.images().remove(ref.name)

    def rename_distro(self, ref, newname):
        self.log("rename_distro",[ref.name,newname])
        return self._config.distros().rename(ref,newname)

    def rename_profile(self, ref, newname):
        self.log("rename_profiles",[ref.name,newname])
        return self._config.profiles().rename(ref,newname)

    def rename_system(self, ref, newname):
        self.log("rename_system",[ref.name,newname])
        return self._config.systems().rename(ref,newname)

    def rename_repo(self, ref, newname):
        self.log("rename_repo",[ref.name,newname])
        return self._config.repos().rename(ref,newname)
    
    def rename_image(self, ref, newname):
        self.log("rename_image",[ref.name,newname])
        return self._config.image().rename(ref,newname)

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

    def add_distro(self, ref, check_for_duplicate_names=False):
        self.log("add_distro",[ref.name])
        return self._config.distros().add(ref,save=True,check_for_duplicate_names=check_for_duplicate_names)

    def add_profile(self, ref, check_for_duplicate_names=False):
        self.log("add_profile",[ref.name])
        return self._config.profiles().add(ref,save=True,check_for_duplicate_names=check_for_duplicate_names)

    def add_system(self, ref, check_for_duplicate_names=False, check_for_duplicate_netinfo=False):
        self.log("add_system",[ref.name])
        return self._config.systems().add(ref,save=True,check_for_duplicate_names=check_for_duplicate_names,check_for_duplicate_netinfo=check_for_duplicate_netinfo)

    def add_repo(self, ref, check_for_duplicate_names=False):
        self.log("add_repo",[ref.name])
        return self._config.repos().add(ref,save=True,check_for_duplicate_names=check_for_duplicate_names)
    
    def add_image(self, ref, check_for_duplicate_names=False):
        self.log("add_image",[ref.name])
        return self._config.images().add(ref,save=True,check_for_duplicate_names=check_for_duplicate_names)

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

    def dump_vars(self, obj, format=False):
        return obj.dump_vars(format)

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

    def get_repo_config_for_profile(self,obj):
        return self.yumgen.get_yum_config(obj,True)
    
    def get_repo_config_for_system(self,obj):
        return self.yumgen.get_yum_config(obj,False)

    def generate_kickstart(self,profile,system):
        self.log("generate_kickstart")
        if system:
            return self.kickgen.generate_kickstart_for_system(system)
        else:
            return self.kickgen.generate_kickstart_for_profile(profile) 

    def check(self):
        """
        See if all preqs for network booting are valid.  This returns
        a list of strings containing instructions on things to correct.
        An empty list means there is nothing to correct, but that still
        doesn't mean there are configuration errors.  This is mainly useful
        for human admins, who may, for instance, forget to properly set up
        their TFTP servers for PXE, etc.
        """
        self.log("check")
        check = action_check.BootCheck(self._config)
        return check.run()

    def validateks(self):
        """
        Use ksvalidator (from pykickstart, if available) to determine
        whether the cobbler kickstarts are going to be (likely) well
        accepted by Anaconda.  Presence of an error does not indicate
        the kickstart is bad, only that the possibility exists.  ksvalidator
        is not available on all platforms and can not detect "future"
        kickstart format correctness.
        """
        self.log("validateks")
        validator = action_validate.Validate(self._config)
        return validator.run()

    def sync(self):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        self.log("sync")
        sync = self.get_sync()
        return sync.run()

    def get_sync(self):
        self.dhcp = self.get_module_from_file(
           "dhcp",
           "module",
           "manage_isc"
        ).get_manager(self._config)
        self.dns = self.get_module_from_file(
           "dns",
           "module",
           "manage_bind"
        ).get_manager(self._config)
        return action_sync.BootSync(self._config,dhcp=self.dhcp,dns=self.dns)

    def reposync(self, name=None):
        """
        Take the contents of /var/lib/cobbler/repos and update them --
        or create the initial copy if no contents exist yet.
        """
        self.log("reposync",[name])
        reposync = action_reposync.RepoSync(self._config)
        return reposync.run(name)

    def status(self,mode=None):
        self.log("status")
        statusifier = action_status.BootStatusReport(self._config,mode)
        return statusifier.run()

    def import_tree(self,mirror_url,mirror_name,network_root=None,kickstart_file=None,rsync_flags=None,arch=None):
        """
        Automatically import a directory tree full of distribution files.
        mirror_url can be a string that represents a path, a user@host 
        syntax for SSH, or an rsync:// address.  If mirror_url is a 
        filesystem path and mirroring is not desired, set network_root 
        to something like "nfs://path/to/mirror_url/root" 
        """
        self.log("import_tree",[mirror_url, mirror_name, network_root, kickstart_file, rsync_flags])
        importer = action_import.Importer(
            self, self._config, mirror_url, mirror_name, network_root, kickstart_file, rsync_flags, arch
        )
        return importer.run()

    def acl_config(self,adduser=None,addgroup=None,removeuser=None,removegroup=None):
        """
        Configures users/groups to run the cobbler CLI as non-root.
        Pass in only one option at a time.  Powers "cobbler aclconfig"
        """
        acl = action_acl.AclConfig(self._config)
        return acl.run(
            adduser=adduser,
            addgroup=addgroup,
            removeuser=removeuser,
            removegroup=removegroup
        )

    def serialize(self):
        """
        Save the config file(s) to disk.
        """
        self.log("serialize")
        return self._config.serialize()

    def deserialize(self):
        """
        Load the current configuration from config file(s)
        """
        return self._config.deserialize()

    def deserialize_raw(self,collection_name):
        """
        Get the collection back just as raw data.
        """
        return self._config.deserialize_raw(collection_name)

    def deserialize_item_raw(self,collection_name,obj_name):
        """
        Get an object back as raw data.
        Can be very fast for shelve or catalog serializers
        """
        return self._config.deserialize_item_raw(collection_name,obj_name)

    def get_module_by_name(self,module_name):
        """
        Returns a loaded cobbler module named 'name', if one exists, else None.
        """
        return module_loader.get_module_by_name(module_name)

    def get_module_from_file(self,section,name,fallback=None):
        """
        Looks in /etc/cobbler/modules.conf for a section called 'section'
        and a key called 'name', and then returns the module that corresponds
        to the value of that key.
        """
        return module_loader.get_module_from_file(section,name,fallback)

    def get_modules_in_category(self,category):
        """
        Returns all modules in a given category, for instance "serializer", or "cli".
        """
        return module_loader.get_modules_in_category(category)

    def authenticate(self,user,password):
        """
        (Remote) access control.
        """
        rc = self.authn.authenticate(self,user,password)
        self.log("authenticate",[user,rc])
        return rc 

    def authorize(self,user,resource,arg1=None,arg2=None):
        """
        (Remote) access control.
        """
        rc = self.authz.authorize(self,user,resource,arg1,arg2)
        self.log("authorize",[user,resource,arg1,arg2,rc],debug=True)
        return rc

    def build_iso(self,iso=None,profiles=None,systems=None,tempdir=None):
        builder = action_buildiso.BuildIso(self._config)
        return builder.run(
           iso=iso, profiles=profiles, systems=systems, tempdir=tempdir
        )

    def replicate(self, cobbler_master = None, sync_all=False, sync_kickstarts=False, sync_trees=False, sync_repos=False, sync_triggers=False, systems=False):
        """
        Pull down metadata from a remote cobbler server that is a master to this server.
        Optionally rsync data from it.
        """
        replicator = action_replicate.Replicate(self._config)
        return replicator.run(
              cobbler_master = cobbler_master,
              sync_all = sync_all,
              sync_kickstarts = sync_kickstarts,
              sync_trees = sync_trees,
              sync_repos = sync_repos,
              sync_triggers = sync_triggers,
              include_systems = systems
        )

    def get_kickstart_templates(self):
        return utils.get_kickstar_templates(self)

