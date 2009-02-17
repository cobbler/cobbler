"""
Report CLI module.

Copyright 2008, Red Hat, Inc
Anderson Silva <ansilva@redhat.com

This software may be freely redistributed under the terms of the GNU
general public license.:

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import sys

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _, get_random_mac
import commands
from cexceptions import *
HELP_FORMAT = commands.HELP_FORMAT


class ReportFunction(commands.CobblerFunction):
    
    def help_me(self):
        return HELP_FORMAT % ("cobbler report","[ARGS]")

    def command_name(self):
        return "report"

    def add_options(self, p, args):
        p.add_option("--what",              dest="what",      default="all",   help="distros/profiles/systems/repos")
        p.add_option("--name",              dest="name",                       help="report on just this object")
        p.add_option("--format",            dest="type",      default="text",  help="text/csv/trac/doku/mediawiki")
        p.add_option("--fields",            dest="fields",    default="all" ,  help="what fields to display")
        p.add_option("--no-headers",         dest="noheaders", help="don't output headers", action='store_true', default=False)


    def run(self):
        if self.options.what not in [ "all", "distros", "profiles", "systems", "repos" ]:
            raise CX(_("Invalid value for --what"))
        if self.options.type not in ["text", "csv", "trac", "doku", "mediawiki" ]:
            raise CX(_("Invalid vavlue for --type"))


        return self.api.report(report_what = self.options.what, report_name = self.options.name, \
                               report_type = self.options.type, report_fields = self.options.fields, \
                               report_noheaders = self.options.noheaders)
    
########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       ReportFunction(api)
    ]


