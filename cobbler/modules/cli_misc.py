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

    def run(self):
        status = self.api.check()
        if len(status) == 0:
            print _("No setup problems found")
            print _("Manual review and editing of /var/lib/cobbler/settings is recommended to tailor cobbler to your particular configuration.")
            print _("Good luck.")
            return True
        else:
            print _("The following potential problems were detected:")
            for i,x in enumerate(status):
               print _("#%(number)d: %(problem)s") % { "number" : i, "problem" : x }
            return False

########################################################

class ImportFunction(commands.CobblerFunction):
    
    def help_me(self):
        return HELP_FORMAT % ("cobbler import","[ARGS|--help]")

    def command_name(self):
        return "import"

    def add_options(self, p, args):
        p.add_option("--arch",               dest="arch",               help="explicitly specify the architecture being imported (RECOMENDED)")
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
                arch=self.options.arch
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
        return HELP_FORMAT % ("cobbler list","[ARGS|--help]")

    def command_name(self):
        return "list"

    def add_options(self, p, args):
        p.add_option("--what",              dest="what",          default="all", help="all/distros/profiles/systems/repos")
     
    def run(self):
        if self.options.what not in [ "all", "distros", "profiles", "systems", "repos" ]:
            raise CX(_("invalid value for --what"))
        if self.options.what in [ "all" ]:       
            self.list_tree(self.api.distros(),0)
            self.list_tree(self.api.repos(),0)
        if self.options.what in [ "distros"]:
            self.list_list(self.api.distros())
        if self.options.what in [ "profiles"]:
            self.list_list(self.api.profiles())
        if self.options.what in [ "systems" ]:
            self.list_list(self.api.systems())
        if self.options.what in [ "repos"]:
            self.list_list(self.api.repos())

########################################################

class ReportFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler report","[ARGS|--help]")

    def command_name(self):
        return "report"

    def add_options(self, p, args):
        p.add_option("--what",              dest="what",   default="all",  help="distros/profiles/systems/repos")
        p.add_option("--name",              dest="name",                   help="report on just this object")

    def run(self):
        if self.options.what not in [ "all", "distros", "profiles", "systems", "repos" ]:
            raise CX(_("Invalid value for --what"))

        if self.options.what in [ "all", "distros"  ]:
            if self.options.name:
                self.reporting_list_names2(self.api.distros(),self.options.name)
            else:
                self.reporting_print_sorted(self.api.distros())

        if self.options.what in [ "all", "profiles" ]:
            if self.options.name:
                self.reporting_list_names2(self.api.profiles(),self.options.name)
            else:
                self.reporting_print_sorted(self.api.profiles())

        if self.options.what in [ "all", "systems"  ]:
            if self.options.name:
                self.reporting_list_names2(self.api.systems(),self.options.name)
            else:
                self.reporting_print_sorted(self.api.systems())

        if self.options.what in [ "all", "repos"    ]:
            if self.options.name:
                self.reporting_list_names2(self.api.repos(),self.options.name)
            else:
                self.reporting_print_sorted(self.api.repos())
        return True

## FIXME: add legacy command translator to keep things simple
## cobbler system report foo --> cobbler report --what=systems --name=foo
## cobbler system report --> cobbler report --what=systems
## ditto for "cobbler list"

########################################################

class StatusFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler status","[ARGS|--help]")

    def command_name(self):
        return "status"

    def run(self):
        return self.api.status("text")  # no other output modes supported yet

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
        return HELP_FORMAT % ("cobbler reposync","[ARGS|--help]")

    def command_name(self):
        return "reposync"

    def add_options(self, p, args):
        p.add_option("--only",           dest="only",             help="update only this repository name")

    def run(self):
        return self.api.reposync(self.options.only)

########################################################

class ValidateKsFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler validateks","")

    def command_name(self):
        return "validateks"
 
    def run(self):
        return self.api.validateks()

########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       CheckFunction(api), ImportFunction(api), ReserializeFunction(api),
       ListFunction(api), ReportFunction(api), StatusFunction(api),
       SyncFunction(api), RepoSyncFunction(api), ValidateKsFunction(api)
    ]
    return []


