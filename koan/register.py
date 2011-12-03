"""
registration tool for cobbler.

Copyright 2009 Red Hat, Inc and Others.
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

import random
import os
import traceback
try:
    from optparse import OptionParser
except:
    from opt_parse import OptionParser  # importing this for backwards compat with 2.2
import exceptions
try:
    import subprocess as sub_process
except:
    import sub_process
import time
import errno
import sys
import xmlrpclib
import glob
import socket
import utils
import string
import pprint

# usage: cobbler-register [--server=server] [--hostname=hostname] --profile=foo


def main():
    """
    Command line stuff...
    """

    p = OptionParser()
    p.add_option("-s", "--server",
                 dest="server",
                 default=os.environ.get("COBBLER_SERVER",""),
                 help="attach to this cobbler server")
    p.add_option("-f", "--fqdn",
                 dest="hostname",
                 default="",
                 help="override the discovered hostname")
    p.add_option("-p", "--port",
                 dest="port",
                 default="80",
                 help="cobbler port (default 80)")
    p.add_option("-P", "--profile",
                 dest="profile",
                 default="",
                 help="assign this profile to this system")
    p.add_option("-b", "--batch",
                 dest="batch",
                 action="store_true",
                 help="indicates this is being run from a script")

    (options, args) = p.parse_args()
    #if not os.getuid() == 0:
    #    print "koan requires root access"
    #    return 3

    try:
        k = Register()
        k.server              = options.server
        k.port                = options.port
        k.profile             = options.profile
        k.hostname            = options.hostname
        k.batch               = options.batch
        k.run()
    except Exception, e:
        (xa, xb, tb) = sys.exc_info()
        try:
            getattr(e,"from_koan")
            print str(e)[1:-1] # nice exception, no traceback needed
        except:
            print xa
            print xb
            print string.join(traceback.format_list(traceback.extract_tb(tb)))
        return 1

    return 0

#=======================================================

class InfoException(exceptions.Exception):
    """
    Custom exception for tracking of fatal errors.
    """
    def __init__(self,value,**args):
        self.value = value % args
        self.from_koan = 1
    def __str__(self):
        return repr(self.value)

#=======================================================

class Register:

    def __init__(self):
        """
        Constructor.  Arguments will be filled in by optparse...
        """
        self.server            = ""
        self.port              = ""
        self.profile           = ""
        self.hostname          = ""
        self.batch           = ""

    #---------------------------------------------------

    def run(self):
        """
        Commence with the registration already.
        """
      
        # not really required, but probably best that ordinary users don't try
        # to run this not knowing what it does.
        if os.getuid() != 0:
           raise InfoException("root access is required to register")
 
        print "- preparing to koan home"
        self.conn = utils.connect_to_server(self.server, self.port)
        reg_info = {}
        print "- gathering network info"
        netinfo = utils.get_network_info()
        reg_info["interfaces"] = netinfo
        print "- checking hostname"
        sysname = ""
        if self.hostname != "" and self.hostname != "*AUTO*":
            hostname = self.hostname
            sysname  = self.hostname
        else:
            hostname = socket.getfqdn()
            if hostname == "localhost.localdomain": 
                if self.hostname == '*AUTO*':
                    hostname = ""
                    sysname = str(time.time())
                else:
                    raise InfoException("must specify --fqdn, could not discover")
            if sysname == "":
                sysname = hostname

        if self.profile == "":
            raise InfoException("must specify --profile")

        # we'll do a profile check here just to avoid some log noise on the remote end.
        # network duplication checks and profile checks also happen on the remote end.

        avail_profiles = self.conn.get_profiles()
        matched_profile = False
        for x in avail_profiles:
            if x.get("name","") == self.profile:
               matched_profile=True
               break
        
        reg_info['name'] = sysname
        reg_info['profile'] = self.profile
        reg_info['hostname'] = hostname
        
        if not matched_profile:
            raise InfoException("no such remote profile, see 'koan --list-profiles'") 

        if not self.batch:
            self.conn.register_new_system(reg_info)
            print "- registration successful, new system name: %s" % sysname
        else:
            try:
                self.conn.register_new_system(reg_info)
                print "- registration successful, new system name: %s" % sysname
            except:
                traceback.print_exc()
                print "- registration failed, ignoring because of --batch"

        return
   
if __name__ == "__main__":
    main()
 
