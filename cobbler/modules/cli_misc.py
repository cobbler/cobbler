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

from rhpl.translate import _, N_, textdomain, utf8
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
        p.add_option("--mirror",             dest="mirror",             help="local path or rsync location (REQUIRED)")
        p.add_option("--name",               dest="name",               help="name, ex 'RHEL-5', (REQUIRED)")
        p.add_option("--available-as",       dest="available_as",       help="do not mirror, use this as install tree")

    def run(self):
        if not self.options.mirror:
           raise CX(_("mirror is required"))
        if not self.options.name:
           raise CX(_("name is required"))
        return self.api.import_tree(
                self.options.mirror,
                self.options.name,
                network_root=self.options.available_as
        )


########################################################

class ReserializeFunction(commands.CobblerFunction):

    def help_me(self):
        return "" # hide

    def command_name(self):
        return "reserialize"

    def run(self):
        return self.api.reserialize()

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
            self.__tree(self.api.distros(),0)
            self.__tree(self.api.repos(),0)
        if self.options.what in [ "distros"]:
            self.__list(self.api.distros())
        if self.options.what in [ "profiles"]:
            self.__list(self.api.profiles())
        if self.options.what in [ "systems" ]:
            self.__list(self.api.systems())
        if self.options.what in [ "repos"]:
            self.__list(self.api.repos())

    def __list(self, collection):
        names = [ x.name for x in collection]
        names.sort() # sorted() is 2.4 only
        for name in names:
           str = _("  %(name)s") % { "name" : name }
           print str
        return True

    def __tree(self,collection,level):
        for item in collection:
            print _("%(indent)s%(type)s %(name)s") % {
                "indent" : "   " * level,
                "type"   : item.TYPE_NAME,
                "name"   : item.name
            }
            kids = item.get_children()
            if kids is not None and len(kids) > 0:
               self.__tree(kids,level+1)

########################################################

class ReportFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler report","[ARGS|--help]")

    def command_name(self):
        return "report"

    def add_options(self, p, args):
        p.add_option("--what",              dest="what",   default="all",  help="distros/profiles/systems/repos (REQUIRED)")
        p.add_option("--name",              dest="name",                   help="report on just this object")

    def __list_names2(self, collection, name):
        obj = collection.find(name=name)
        if obj is not None:
            print obj.printable()
        return True

    def __sorter(self, a, b):
        return cmp(a.name, b.name)

    def __print_sorted(self, collection):
        collection = [x for x in collection]
        collection.sort(self.__sorter)
        for x in collection:
            print x.printable()
        return True

    def __list_names2(self, collection, name):
        obj = collection.find(name=name)
        if obj is not None:
            print obj.printable()
        return True

    def run(self):
        if self.options.what not in [ "all", "distros", "profiles", "systems", "repos" ]:
            raise CX(_("Invalid value for --what"))

        if self.options.what in [ "all", "distros"  ]:
            if self.options.name:
                self.__list_names2(self.api.distros(),self.options.name)
            else:
                self.__print_sorted(self.api.distros())

        if self.options.what in [ "all", "profiles" ]:
            if self.options.name:
                self.__list_names2(self.api.profiles(),self.options.name)
            else:
                self.__print_sorted(self.api.profiles())

        if self.options.what in [ "all", "systems"  ]:
            if self.options.name:
                self.__list_names2(self.api.systems(),self.options.name)
            else:
                self.__print_sorted(self.api.sytems())

        if self.options.what in [ "all", "repos"    ]:
            if self.options.name:
                self.__list_names2(self.api.repos(),self.options.name)
            else:
                self.__print_sorted(self.api.repos())
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

########################################################

class RepoSyncFunction(commands.CobblerFunction):

    def help_me(self):
        return HELP_FORMAT % ("cobbler reposync","[ARGS|--help]")

    def command_name(self):
        return "reposync"

    def add_options(self, p, args):
        p.add_options("--only",           dest="only",             help="update only this repository name")

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


