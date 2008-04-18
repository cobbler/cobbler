# Mod Python service functions for Cobbler's public interface
# (aka cool stuff that works with wget)
#
# Copyright 2007 Albert P. Tobey <tobert@gmail.com>
# additions: Michael DeHaan <mdehaan@redhat.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import exceptions
import xmlrpclib
import os
import traceback
import string
import sys
import time

def log_exc(apache):
    """
    Log active traceback to logfile.
    """
    (t, v, tb) = sys.exc_info()
    apache.log_error("Exception occured: %s" % t )
    apache.log_error("Exception value: %s" % v)
    apache.log_error("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))

class CobblerSvc(object):
    """
    Interesting mod python functions are all keyed off the parameter
    mode, which defaults to index.  All options are passed
    as parameters into the function.
    """
    def __init__(self, server=None, apache=None):
        self.server = server
        self.apache = apache
        self.remote = None

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server. 
        This is the version that does not require logins.
        """
        self.remote = xmlrpclib.Server(self.server, allow_none=True)

    def modes(self):
        """
        Returns a list of methods in this object that can be run as web
        modes.   
        """
        retval = list()
        for m in dir(self):
            func = getattr( self, m )
            if hasattr(func, 'exposed') and getattr(func,'exposed'):
                retval.append(m) 
        return retval

    def index(self,**args):
        return "no mode specified"

    def ks(self,profile=None,system=None,REMOTE_ADDR=None,REMOTE_MAC=None,reg=None,**rest):
        """
        Generate kickstart files...
        """
        self.__xmlrpc_setup()
        return self.remote.generate_kickstart(profile,system,REMOTE_ADDR,REMOTE_MAC)
    
    def trig(self,mode="?",profile=None,system=None,REMOTE_ADDR=None,**rest):
        """
        Hook to call install triggers.
        """
        self.__xmlrpc_setup()
        ip = REMOTE_ADDR
        if profile:
            rc = self.remote.run_install_triggers(mode,"profile",profile,ip)
        else:
            rc = self.remote.run_install_triggers(mode,"system",system,ip)
        return str(rc)

    def nopxe(self,system=None,**rest):
        self.__xmlrpc_setup()
        return str(self.remote.disable_netboot(system))

    # =======================================================
    # list of functions that are callable via mod_python:
    modes.exposed = False
    index.exposed = True
    ks.exposed = True
    trig.exposed = True


