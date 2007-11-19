"""
Command line interface for cobbler, a network provisioning configuration
library.  Consult 'man cobbler' for general info.  This class serves
as a good reference on how to drive the API (api.py).

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import sys
import api
import os
import os.path
import traceback
import optparse
import commands
import cexceptions

from rhpl.translate import _, N_, textdomain, utf8
I18N_DOMAIN = "cobbler"

####################################################

class BootCLI:

    def __init__(self):
        textdomain(I18N_DOMAIN)
        self.api = api.BootAPI()
        self.loader = commands.FunctionLoader()
        climods = self.api.get_modules_in_category("cli")
        for mod in climods:
            for fn in mod.cli_functions(self.api):
                self.loader.add_func(fn)
      
    def run(self,args):
        return self.loader.run(args)

####################################################

def main():
    """
    CLI entry point
    """
    exitcode = 0
    try:
        # FIXME: redo locking code?
        return BootCLI().run(sys.argv)
    except cexceptions.CX, exc:
        if str(type(exc)).find("CX") != -1:
            print str(exc)[1:-1]  # remove framing air quotes
        else:
            (t, val, tb) = sys.exc_info()
            print tb.extract_tb().join("\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
