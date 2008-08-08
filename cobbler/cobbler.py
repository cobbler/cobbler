"""
Command line interface for cobbler, a network provisioning configuration
library.  Consult 'man cobbler' for general info.  This class serves
as a good reference on how to drive the API (api.py).

Copyright 2006, Red Hat, Inc
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

import sys
import api
import os
import os.path
import traceback
import optparse
import string
import commands
import cexceptions
import utils
from cexceptions import *

from utils import _
I18N_DOMAIN = "cobbler"

####################################################

class BootCLI:

    def __init__(self):
        self.api = api.BootAPI()
        self.loader = commands.FunctionLoader(self.api)
        climods = self.api.get_modules_in_category("cli")
        for mod in climods:
            for fn in mod.cli_functions(self.api):
                self.loader.add_func(fn)
      
    def run(self,args):
        if not self.api.perms_ok:
            print >> sys.stderr, "Insufficient permissions.  Use cobbler aclsetup to grant access to non-root users."
            sys.exit(1)

        return self.loader.run(args)

####################################################

def run_upgrade_checks():
    """
    Cobbler tries to make manual upgrade steps unneeded, though
    this function serves to inform users of manual steps when they /are/
    needed.
    """
    # for users running pre-1.0 upgrading to 1.0
    if os.path.exists("/var/lib/cobbler/settings"):
       raise CX(_("/var/lib/cobbler/settings is no longer in use, remove this file to acknowledge you have migrated your configuration to /etc/cobbler/settings.  Do not simply copy the file over or you will lose new configuration entries. Run 'cobbler check' and then 'cobbler sync' after making changes."))

def main():
    """
    CLI entry point
    """
    exitcode = 0
    try:
        run_upgrade_checks()
        rc = BootCLI().run(sys.argv)
        if rc == True or rc is None:
            return 0
        elif rc == False:
            return 1
        return rc
    except Exception, exc:
        utils.print_exc(exc,full=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
