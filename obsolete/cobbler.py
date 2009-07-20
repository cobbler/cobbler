"""
Command line interface for cobbler.

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

import sys
import xmlrpclib
#import os
#import os.path
import traceback
import optparse
import string
import commands
import module_loader
#import cexceptions
#import utils
#from cexceptions import *
#from utils import _
#I18N_DOMAIN = "cobbler"

####################################################

class BootCLI:

    def __init__(self,endpoint="http://127.0.0.1/cobbler_api"):

        # FIXME: allow specifying other endpoints, and in which case,
        # do /not/ read the web.ss file.

        

        self.remote = xmlrpclib.Server(endpoint)
        self.loader = commands.FunctionLoader(self.remote)

        # FIXME: all of these should be loaded without an API handle now.
        # climods = self.api.get_modules_in_category("cli")

        module_loader.load_modules()
        climods = module_loader.get_modules_in_category("cli")

        for mod in climods:
            for fn in mod.cli_functions(self.remote):
                self.loader.add_func(fn)
 
    def run(self,args):
        return self.loader.run(args)

####################################################

def main():
    """
    CLI entry point
    """
    try:
        rc = BootCLI().run(sys.argv)
        if rc == True or rc is None:
            return 0
        elif rc == False:
            return 1
        return rc
    except Exception, exc:
        if sys.exc_type == SystemExit:
            return exc.code
        else:
            # FIXME: is this the correct way to show errors for remoted CLI?
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(main())
