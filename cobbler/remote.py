# Interface for Cobbler's XMLRPC API(s).
# there are two:
#   a read-only API that koan uses
#   a read-write API that requires logins

# Copyright 2007, Red Hat, Inc
# Michael DeHaan <mdehaan@redhat.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import socket
import time
import os
import SimpleXMLRPCServer
import glob
from rhpl.translate import _, N_, textdomain, utf8
import xmlrpclib
import logging
import base64

import api as cobbler_api
import yaml # Howell Clark version
import utils
from cexceptions import *
import sub_process

# FIXME: make configurable?
TOKEN_TIMEOUT = 60*60 # 60 minutes

# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCInterface:

    # note:  public methods take an optional parameter token that is just
    # here for consistancy with the ReadWrite API.  The tokens for the read only
    # interface are intentionally /not/ validated.  It's a public API.

    def __init__(self,api,logger):
        self.api = api
        self.logger = logger

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def get_settings(self,token=None):
        """
        Return the contents of /var/lib/cobbler/settings, which is a hash.
        """
        self.api.clear()
        self.api.deserialize()
        data = self.api.settings().to_datastruct()
        return self._fix_none(data)
 
    def disable_netboot(self,name,token=None):
        """
        This is a feature used by the pxe_just_once support, see manpage.
        Sets system named "name" to no-longer PXE.  Disabled by default as
        this requires public API access and is technically a read-write operation.
        """
        # used by nopxe.cgi
        self.api.clear()
        self.api.deserialize()
        if not self.api.settings().pxe_just_once:
            # feature disabled!
            return False
        systems = self.api.systems()
        obj = systems.find(name=name)
        if obj == None:
            # system not found!
            return False
        obj.set_netboot_enabled(0)
        systems.add(obj,with_copy=True)
        return True

    def __get_all(self,collection):
        self.api.clear() 
        self.api.deserialize()
        data = collection.to_datastruct()
        data.sort(self.__sorter)
        return self._fix_none(data)

    def version(self,token=None):
        """
        Return the cobbler version for compatibility testing with remote applications.
        Returns as a float, 0.6.1-2 should result in (int) "0.612".
        """
        return self.api.version()

    def get_distros(self,token=None):
        """
        Returns all cobbler distros as an array of hashes.
        """
        return self.__get_all(self.api.distros())

    def get_profiles(self,token=None):
        """
        Returns all cobbler profiles as an array of hashes.
        """
        return self.__get_all(self.api.profiles())

    def get_systems(self,token=None):
        """
        Returns all cobbler systems as an array of hashes.
        """
        return self.__get_all(self.api.systems())

    def __get_specific(self,collection,name):
        self.api.clear() 
        self.api.deserialize()
        item = collection.find(name=name)
        if item is None:
            return self._fix_none({})
        return self._fix_none(item.to_datastruct())

    def get_distro(self,name,token=None):
        """
        Returns the distro named "name" as a hash.
        """
        return self.__get_specific(self.api.distros(),name)

    def get_profile(self,name,token=None):
        """
        Returns the profile named "name" as a hash.
        """
        return self.__get_specific(self.api.profiles(),name)

    def get_system(self,name,token=None):
        """
        Returns the system named "name" as a hash.
        """
        name = self.fix_system_name(name)
        return self.__get_specific(self.api.systems(),name)

    def get_repo(self,name,token=None):
        """
        Returns the repo named "name" as a hash.
        """
        return self.__get_specific(self.api.repos(),name)

    def get_distro_as_rendered(self,name,token=None):
        """
        Return the distribution as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_distro_for_koan(self,name,token)

    def get_distro_for_koan(self,name,token=None):
        """
        Same as get_distro_as_rendered.
        """
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.distros().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(True, obj))
        return self._fix_none({})

    def get_profile_as_rendered(self,name,token=None):
        """
        Return the profile as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_profile_for_koan(name,token)

    def get_profile_for_koan(self,name,token=None):
        """
        Same as get_profile_as_rendered
        """
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.profiles().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(True, obj))
        return self._fix_none({})

    def get_system_as_rendered(self,name,token=None):
        """
        Return the system as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_system_for_koan(self,name,token)

    def get_system_for_koan(self,name,token=None):
        """
        Same as get_system_as_rendered.
        """
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.systems().find(name=name)
        if obj is not None:
           return self._fix_none(utils.blender(True, obj))
        return self._fix_none({})

    def get_repo_as_rendered(self,name,token=None):
        """
        Return the repo as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_repo_for_koan(self,name,token)

    def get_repo_for_koan(self,name,token=None):
        """
        Same as get_repo_as_rendered.
        """
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.repos().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(True, obj))
        return self._fix_none({})

    def _fix_none(self,data,recurse=False):
        """
        Convert None in XMLRPC to just '~'.  The above
        XMLRPC module hack should do this, but let's make extra sure.
        """

        if data is None:
            data = '~'

        elif type(data) == list:
            data = [ self._fix_none(x,recurse=True) for x in data ]

        elif type(data) == dict:
            for key in data.keys():
               data[key] = self._fix_none(data[key],recurse=True)

        return data

# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************

class CobblerReadWriteXMLRPCInterface:

    def __init__(self,api,logger):
        self.api = api
        self.logger = logger
        self.token_cache = {}

    def __make_token(self):
        """
        Returns a new random token.
        """
        urandom = open("/dev/urandom")
        b64 = base64.b64encode(urandom.read(100))
        self.token_cache[b64] = time.time()
        return b64

    def __invalidate_expired_tokens(self):
        """
        Deletes any login tokens that might have expired.
        """
        timenow = time.time()
        for token in self.token_cache:
            tokentime = self.token_cache[token]
            if (timenow > tokentime + TOKEN_TIMEOUT):
                self.logger.debug("expiring token: %s" % token)
                del self.token_cache[token]

    def __validate_user(self,user,password):
        """
        Returns whether this user/pass combo should be given
        access to the cobbler read-write API.

        FIXME: always returns True, implement this.
        """
        if user == "exampleuser":
            return True
        else:
            return False

    def __validate_token(self,token): 
        """
        Checks to see if an API method can be called when
        the given token is passed in.  Updates the timestamp
        of the token automatically to prevent the need to
        repeatedly call login().  Any method that needs
        access control should call this before doing anything
        else.
        """
        ok = False
        self.__invalidate_expired_tokens()
        if self.token_cache.has_key(token):
            ok = True
            self.token_cache[token] = time.time() # update to prevent timeout
        else:
            self.logger.debug("invalid token: %s" % token)
            raise CX(_("invalid token: %s" % token))

    def login(self,user,password):
        if self.__validate_user(user,password):
            token = self.__make_token()
            self.logger.info("login succeeded: %s" % user)
            return token
        else:
            self.logger.info("login failed: %s" % user)
            raise CX(_("login failed: %s") % user)
    
    def test(self,token=None):
        self.__validate_token(token)
        return "passed"
        

# *********************************************************************************
# *********************************************************************************

class CobblerReadWriteXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):

    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************

if __name__ == "__main__":

    logger = logging.getLogger("cobbler.cobblerd")
    logger.setLevel(logging.DEBUG)
    ch = logging.FileHandler("/var/log/cobbler/cobblerd.log")
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    api = cobbler_api.BootAPI()

    remote = CobblerReadWriteXMLRPCInterface(api,logger)
    token = remote.login("exampleuser","examplepass")
    print token
    rc = remote.test(token)
    print "test result: %s" % rc
    
    remote = CobblerReadWriteXMLRPCInterface(api,logger)
    try:
        token = remote.login("exampleuser2","examplepass")
    except:
        token = "fake_token"
    print token
    rc = remote.test(token)
    print "test result: %s" % rc
 
    print "cache: %s" % remote.token_cache
