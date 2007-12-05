"""
python API module for Cobbler
see source for cobbler.py, or pydoc, for example usage.
CLI apps and daemons should import api.py, and no other cobbler code.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import config
import utils
import action_sync
import action_check
import action_import
import action_reposync
import action_status
import action_validate
import sub_process
import module_loader
import logging

ERROR = 100
INFO  = 10
DEBUG = 5

class BootAPI:

    __shared_state = {}
    has_loaded = False

    def __init__(self):
        """
        Constructor
        """

        self.__dict__ = self.__shared_state
        if not BootAPI.has_loaded:


            logger = logging.getLogger("cobbler.api")
            logger.setLevel(logging.DEBUG)
            ch = logging.FileHandler("/var/log/cobbler/cobbler.log")
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            BootAPI.has_loaded   = True
            module_loader.load_modules()
            self._config         = config.Config(self)
            self.deserialize()
            self.logger = logger
            self.logger.debug("API handle initialized")

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

    def version(self):
        """
        What version is cobbler?
        Currently checks the RPM DB, which is not perfect.
        Will return "?" if not installed.
        """
        self.logger.debug("cobbler version")
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

    def settings(self):
        """
        Return the application configuration
        """
        return self._config.settings()

    def new_system(self,is_subobject=False):
        """
        Return a blank, unconfigured system, unattached to a collection
        """
        self.logger.debug("new_system")
        return self._config.new_system(is_subobject=is_subobject)

    def new_distro(self,is_subobject=False):
        """
        Create a blank, unconfigured distro, unattached to a collection.
        """
        self.logger.debug("new_distro")
        return self._config.new_distro(is_subobject=is_subobject)


    def new_profile(self,is_subobject=False):
        """
        Create a blank, unconfigured profile, unattached to a collection
        """
        self.logger.debug("new_profile")
        return self._config.new_profile(is_subobject=is_subobject)

    def new_repo(self,is_subobject=False):
        """
        Create a blank, unconfigured repo, unattached to a collection
        """
        self.logger.debug("new_repo")
        return self._config.new_repo(is_subobject=is_subobject)

    def auto_add_repos(self):
        """
        Import any repos this server knows about and mirror them.
        Credit: Seth Vidal.
        """
        self.logger.debug("auto_add_repos")
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
            self._config.repos().add(cobbler_repo,with_copy=True)

        print "run cobbler reposync to apply changes"
        return True 
 
    def check(self):
        """
        See if all preqs for network booting are valid.  This returns
        a list of strings containing instructions on things to correct.
        An empty list means there is nothing to correct, but that still
        doesn't mean there are configuration errors.  This is mainly useful
        for human admins, who may, for instance, forget to properly set up
        their TFTP servers for PXE, etc.
        """
        self.logger.debug("check")
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
        self.logger.debug("validateks")
        validator = action_validate.Validate(self._config)
        return validator.run()

    def sync(self):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        self.logger.debug("sync")
        sync = action_sync.BootSync(self._config)
        return sync.run()

    def reposync(self, name=None):
        """
        Take the contents of /var/lib/cobbler/repos and update them --
        or create the initial copy if no contents exist yet.
        """
        self.logger.debug("reposync")
        reposync = action_reposync.RepoSync(self._config)
        return reposync.run(name)

    def status(self,mode):
        self.logger.debug("status")
        statusifier = action_status.BootStatusReport(self._config, mode)
        return statusifier.run()

    def import_tree(self,mirror_url,mirror_name,network_root=None):
        """
        Automatically import a directory tree full of distribution files.
        mirror_url can be a string that represents a path, a user@host 
        syntax for SSH, or an rsync:// address.  If mirror_url is a 
        filesystem path and mirroring is not desired, set network_root 
        to something like "nfs://path/to/mirror_url/root" 
        """
        importer = action_import.Importer(
            self, self._config, mirror_url, mirror_name, network_root
        )
        return importer.run()

    def serialize(self):
        """
        Save the config file(s) to disk.
        """
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
        self.logger.debug("authorize(%s)" % (user))
        rc = self.authn.authenticate(self,user,password)     
        self.logger.debug("authorize(%s)=%s" % (user,rc))
        return rc 

    def authorize(self,user,resource,arg1=None,arg2=None):
        """
        (Remote) access control.
        """
        rc = self.authz.authorize(self,user,resource,arg1,arg2)
        self.logger.debug("authorize(%s,%s)=%s" % (user,resource,rc))
        return rc

