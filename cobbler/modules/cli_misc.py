"""
Misc CLI functions.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import sys
import time

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _
import commands
from cexceptions import *
HELP_FORMAT = commands.HELP_FORMAT

# TO DO list
# cobbler check
# cobbler import (--name, --mirror, --available-as)
# cobbler reserialize
# cobbler --type=[profile|system|distro|repo] [--name=list]
# cobbler --type=[profile|system|distro|profile] [--name=report]
# cobbler status
# cobbler reposync --name=$name
# cobbler sync
# cobbler validateks
# elsewhere: repo auto-add

########################################################

class CheckFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler check","")

    def command_name(self):
        return "check"

    def add_options(self, p, args):
        pass

    def logprint(self,fd,msg,log_only=False):
        fd.write("%s\n" % msg)
        if log_only:
           return
        print msg

    def run(self):
        status = self.api.check()
        fd = open("/var/log/cobbler/check.log","w+")
        self.logprint(fd,"cobbler check log from %s" % time.asctime(),log_only=True)
        if len(status) != 0:
            self.logprint(fd,"No setup problems found")
             
            self.logprint(fd,"Manual review and editing of /var/lib/cobbler/settings is recommended to tailor cobbler to your particular configuration.")
            self.logprint(fd,"Good luck.")
            return True
        else:
            self.logprint(fd,"The following potential problems were detected:")
            for i,x in enumerate(status):
               self.logprint(fd,"#%(number)d: %(problem)s" % { "number" : i, "problem" : x })
            return False

########################################################

class ImportFunction(commands.CobblerFunction):
    
    def help_me(self):
        return HELP_FORMAT % ("cobbler import","[ARGS]")

    def command_name(self):
        return "import"

    def add_options(self, p, args):
        p.add_option("--arch",               dest="arch",               help="explicitly specify the architecture being imported (RECOMENDED)")
        p.add_option("--breed",              dest="breed",              help="explicitly specify the breed being imported (RECOMENDED)")
        p.add_option("--path",               dest="mirror",             help="local path or rsync location (REQUIRED)")
        p.add_option("--mirror",             dest="mirror_alt",         help="alias for --path")
        p.add_option("--name",               dest="name",               help="name, ex 'RHEL-5', (REQUIRED)")
        p.add_option("--available-as",       dest="available_as",       help="do not mirror, use this as install tree base")
        p.add_option("--kickstart",          dest="kickstart_file",     help="use the kickstart file specified as the profile's kickstart file, do not auto-assign")
        p.add_option("--rsync-flags",        dest="rsync_flags",        help="pass additional flags to rsync")

    def run(self):
        if self.options.mirror_alt and not self.options.mirror:
           self.options.mirror = self.options.mirror_alt
        if not self.options.mirror:
           raise CX(_("mirror is required"))
        if not self.options.name:
           raise CX(_("name is required"))
        return self.api.import_tree(
                self.options.mirror,
                self.options.name,
                network_root=self.options.available_as,
                kickstart_file=self.options.kickstart_file,
                rsync_flags=self.options.rsync_flags,
                arch=self.options.arch,
                breed=self.options.breed
        )


########################################################

class ReserializeFunction(commands.CobblerFunction):

    def help_me(self):
        return "" # hide

    def command_name(self):
        return "reserialize"

    def run(self):
        # already deserialized when API is instantiated
        # this just saves files in new config format (if any)
        return self.api.serialize()

########################################################

class ListFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler list","[ARGS]")

    def command_name(self):
        return "list"

    def add_options(self, p, args):
        p.add_option("--what",              dest="what",          default="all", help="all/distros/profiles/systems/repos")
     
    def run(self):
        if self.options.what not in [ "all", "distros", "profiles", "systems", "repos", "images" ]:
            raise CX(_("invalid value for --what"))
        if self.options.what in ["all"]:
            self.list_tree(self.api.distros(),0)
            self.list_tree(self.api.repos(),0)
            self.list_tree(self.api.images(),0)
        if self.options.what in ["distros"]:
            self.list_list(self.api.distros())
        if self.options.what in ["profiles"]:
            self.list_list(self.api.profiles())
        if self.options.what in ["systems" ]:
            self.list_list(self.api.systems())
        if self.options.what in ["repos"]:
            self.list_list(self.api.repos())
        if self.options.what in ["images"]:
            self.list_list(self.api.images())

########################################################

class StatusFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler status","[ARGS]")

    def command_name(self):
        return "status"

    def run(self):
        return self.api.status("text") # no other output modes supported yet

########################################################

class SyncFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler sync","")

    def command_name(self):
        return "sync"

    def run(self):
        return self.api.sync()

########################################################

class RepoSyncFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler reposync","[ARGS]")

    def command_name(self):
        return "reposync"

    def add_options(self, p, args):
        p.add_option("--only",           dest="only",             help="update only this repository name")
        p.add_option("--tries",          dest="tries",            help="try each repo this many times", default=1)
        p.add_option("--no-fail",        dest="nofail",           help="don't stop reposyncing if a failure occurs", action="store_true")

    def run(self):
        return self.api.reposync(self.options.only, tries=self.options.tries, nofail=self.options.nofail)

########################################################

class ValidateKsFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler validateks","")

    def command_name(self):
        return "validateks"
 
    def run(self):
        return self.api.validateks()

########################################################

class BuildIsoFunction(commands.CobblerFunction):

    def add_options(self,p,args): 
        p.add_option("--iso",      dest="isoname",  help="(OPTIONAL) output ISO to this path")
        p.add_option("--profiles", dest="profiles", help="(OPTIONAL) use these profiles only")
        p.add_option("--systems",  dest="systems",  help="(OPTIONAL) use these systems only")
        p.add_option("--tempdir",  dest="tempdir",  help="(OPTIONAL) working directory")

    def help_me(self):
       return HELP_FORMAT % ("cobbler buildiso","[ARGS]")
    
    def command_name(self):
       return "buildiso"

    def run(self):
       return self.api.build_iso(
           iso=self.options.isoname,
           profiles=self.options.profiles,
           systems=self.options.systems,
           tempdir=self.options.tempdir
       )

########################################################

class ReplicateFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler replicate","[ARGS]")

    def command_name(self):
        return "replicate"

    def add_options(self, p, args):
        p.add_option("--master",               dest="master",           help="Cobbler server to replicate from.")
        p.add_option("--include-systems",      dest="systems",          action="store_true", help="include systems in addition to distros, profiles, and repos")
        p.add_option("--full-data-sync",       dest="all",              action="store_true", help="rsync everything")
        p.add_option("--sync-kickstarts",      dest="kickstarts",       action="store_true", help="rsync kickstart templates")
        p.add_option("--sync-trees",           dest="trees",            action="store_true", help="rsync imported trees")
        p.add_option("--sync-triggers",        dest="triggers",         action="store_true", help="rsync trigger scripts")
        p.add_option("--sync-repos",           dest="repos",            action="store_true", help="rsync mirrored repo data")

    def run(self):
        return self.api.replicate(
             cobbler_master = self.options.master,
             sync_all = self.options.all,
             sync_kickstarts = self.options.kickstarts,
             sync_trees = self.options.trees,
             sync_repos = self.options.repos,
             sync_triggers = self.options.triggers,
             systems = self.options.systems
        )

########################################################

class AclFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler aclsetup","[ARGS]")

    def command_name(self):
        return "aclsetup"

    def add_options(self, p, args):
        p.add_option("--adduser",            dest="adduser",            help="give acls to this user")
        p.add_option("--addgroup",           dest="addgroup",           help="give acls to this group")
        p.add_option("--removeuser",         dest="removeuser",         help="remove acls from this user")
        p.add_option("--removegroup",        dest="removegroup",        help="remove acls from this group")

    def run(self):
        return self.api.acl_config(
            self.options.adduser,
            self.options.addgroup,
            self.options.removeuser,
            self.options.removegroup
        )

########################################################

class VersionFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler version","")

    def command_name(self):
        return "version"

    def add_options(self, p, args):
        pass

    def run(self):
 
        # --version output format borrowed from ls, so it must be right :)

        versions = self.api.version(extended=True)

        print "cobbler %s" % versions["version"]
        print ""

        # print extended info if available, which is useful for devel branch testing
        print "build date  : %s" % versions["builddate"]
        if versions.get("gitstamp","?") != "?":
           print "git hash    : %s" % versions["gitstamp"]
        if versions.get("gitdate", "?") != "?":
           print "git date    : %s" % versions["gitdate"]

        print ""

        print "Copyright (C) 2006-2008 Red Hat, Inc."
        print "License GPLv2+: GNU GPL version 2 or later <http://gnu.org/licenses/gpl.html>"
        print "This is free software: you are free to change and redistribute it."
        print "There is NO WARRANTY, to the extent permitted by law."

        print ""
        
        print "Written by Michael DeHaan."

        return True

    
########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       BuildIsoFunction(api), 
       CheckFunction(api), ImportFunction(api), ReserializeFunction(api),
       ListFunction(api), StatusFunction(api),
       SyncFunction(api), RepoSyncFunction(api), ValidateKsFunction(api),
       ReplicateFunction(api), AclFunction(api),
       VersionFunction(api)
    ]
    return []


