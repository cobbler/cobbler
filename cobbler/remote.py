"""
Interface for Cobbler's XMLRPC API(s).
there are two:
   a read-only API that koan uses
   a read-write API that requires logins

Copyright 2007-2008, Red Hat, Inc
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
import socket
import time
import os
import SimpleXMLRPCServer
import xmlrpclib
import random
import base64
import string
import traceback
import glob
import subprocess

import api as cobbler_api
import utils
from cexceptions import *
import item_distro
import item_profile
import item_system
import item_repo
import item_image
from utils import *
from utils import _ # * does not import _

# FIXME: make configurable?
TOKEN_TIMEOUT = 60*60 # 60 minutes
OBJECT_TIMEOUT = 60*60 # 60 minutes
TOKEN_CACHE = {}
OBJECT_CACHE = {}

# *********************************************************************
# *********************************************************************

class CobblerXMLRPCInterface:
    """
    This is the interface used for all public XMLRPC methods, for instance,
    as used by koan.  The read-write interface which inherits from this adds
    more methods, though that interface can be disabled.
 
    note:  public methods take an optional parameter token that is just
    here for consistancy with the ReadWrite API.  The tokens for the read only
    interface are intentionally /not/ validated.  It's a public API.
    """

    def __init__(self,api,logger,enable_auth_if_relevant):
        self.api = api
        self.logger = logger
        self.auth_enabled = enable_auth_if_relevant

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def ping(self):
        return True

    def update(self,token=None):
        # ensure the config is up to date as of /now/
        self.api.deserialize()
        return True

    def get_user_from_token(self,token):
        if not TOKEN_CACHE.has_key(token):
            raise CX(_("invalid token: %s") % token)
        else:
            return self.token_cache[token][1]

    def log(self,msg,user=None,token=None,name=None,object_id=None,attribute=None,debug=False,error=False):

        # add the user editing the object, if supplied
        m_user = "?"
        if user is not None:
           m_user = user
        if token is not None:
           try:
               m_user = self.get_user_from_token(token)
           except:
               # invalid or expired token?
               m_user = "???"
        msg = "%s; user(%s)" % (msg, m_user)

        # add the object name being modified, if any
        oname = ""
        if name:        
           oname = name
        elif object_id:
           try:
               (objref, time) = self.object_cache[object_id]
               oname = objref.name
               if oname == "" or oname is None:
                   oname = "???"
           except:
               oname = "*EXPIRED*"
        if oname != "":
           msg = "%s; object(%s)" % (msg, oname)
                

        # add any attributes being modified, if any
        if attribute:
           msg = "%s; attribute(%s)" % (msg, attribute)
        
        # log to the correct logger
        if error:
           logger = self.logger.error
        elif debug:
           logger = self.logger.debug
        else:
           logger = self.logger.info
        logger(msg)

    def get_size(self,collection_name,**rest):
        """
        Returns the number of entries in a collection (but not the actual
        collection) for WUI/TUI interfaces that want to paginate the results.
        """
        data = self.__get_all(collection_name)
        return len(data)

    def __get_all(self,collection_name,page=None,results_per_page=None):
        """
        Helper method to return all data to the WebUI or another caller
        without going through the process of loading all the data into
        objects and recalculating.  

        Supports pagination for WUI or TUI based interfaces.
        """

        # FIXME: a global lock or module around data access loading
        # would be useful for non-db backed storage

        data = self.api.deserialize_raw(collection_name)
        total_items = len(data)

        if collection_name == "settings":
            return self._fix_none(data)

        data.sort(self.__sorter)

        if page is not None and results_per_page is not None:
            page = int(page)
            results_per_page = int(results_per_page)
            if page < 0:
                return []
            if results_per_page <= 0:
                return []
            start_point = (results_per_page * page)
            end_point   = (results_per_page * page) + results_per_page
            if start_point > total_items:
                start_point = total_items - 1 # correct ???
            if end_point > total_items:
                end_point = total_items
            data = self._fix_none(data[start_point:end_point])

        return self._fix_none(data)

    def get_kickstart_templates(self,token,**rest):
        """
        Returns all of the kickstarts that are in use by the system.
        """
        self.log("get_kickstart_templates",token=token)
        self.check_access(token, "get_kickstart_templates")
        return utils.get_kickstart_templates(self.api)

    def is_kickstart_in_use(self,ks,token,**rest):
        self.log("is_kickstart_in_use",token=token)
        for x in self.api.profiles():
           if x.kickstart is not None and x.kickstart == ks:
               return True
        for x in self.api.systems():
           if x.kickstart is not None and x.kickstart == ks:
               return True
        return False

    def generate_kickstart(self,profile=None,system=None,REMOTE_ADDR=None,REMOTE_MAC=None,**rest):
        self.log("generate_kickstart")

        if profile and not system:
            regrc = self.register_mac(REMOTE_MAC,profile)

        return self.api.generate_kickstart(profile,system)

    def get_settings(self,token=None,**rest):
        """
        Return the contents of /etc/cobbler/settings, which is a hash.
        """
        self.log("get_settings",token=token)
        return self.__get_all("settings")

    def get_repo_config_for_profile(self,profile_name,**rest):
        """
        Return the yum configuration a given profile should use to obtain
        all of it's cobbler associated repos.
        """
        obj = self.api.find_profile(profile_name)
        if obj is None:
           return "# object not found: %s" % profile_name
        return self.api.get_repo_config_for_profile(obj)
    
    def get_repo_config_for_system(self,system_name,**rest):
        """
        Return the yum configuration a given profile should use to obtain
        all of it's cobbler associated repos.
        """
        obj = self.api.find_system(system_name)
        if obj is None:
           return "# object not found: %s" % system_name
        return self.api.get_repo_config_for_system(obj)

    def get_template_file_for_profile(self,profile_name,path,**rest):
        """
        Return the templated file requested for this profile
        """
        obj = self.api.find_profile(profile_name)
        if obj is None:
           return "# object not found: %s" % profile_name
        return self.api.get_template_file_for_profile(obj,path)

    def get_template_file_for_system(self,system_name,path,**rest):
        """
        Return the templated file requested for this system
        """
        obj = self.api.find_system(system_name)
        if obj is None:
           return "# object not found: %s" % system_name
        return self.api.get_template_file_for_system(obj,path)

    def register_mac(self,mac,profile,token=None,**rest):
        """
        If allow_cgi_register_mac is enabled in settings, this allows
        kickstarts to add new system records for per-profile-provisioned
        systems automatically via a wget in %post.  This has security
        implications.
        READ: https://fedorahosted.org/cobbler/wiki/AutoRegistration
        """
        self._refresh()

        if mac is None:
            # don't go further if not being called by anaconda
            return 1

        if not self.api.settings().register_new_installs:
            # must be enabled in settings
            return 2

        system = self.api.find_system(mac_address=mac)
        if system is not None: 
            # do not allow overwrites
            return 3

        # the MAC probably looks like "eth0 AA:BB:CC:DD:EE:FF" now, fix it
        if mac.find(" ") != -1:
            mac = mac.split()[-1]

        dup = self.api.find_system(mac_address=mac)
        if dup is not None:
            return 4

        self.log("register mac for profile %s" % profile,token=token,name=mac)
        obj = self.api.new_system()
        obj.set_profile(profile)
        name = mac.replace(":","_")
        obj.set_name(name)
        obj.set_mac_address(mac, "intf0")
        obj.set_netboot_enabled(False)
        self.api.add_system(obj)
        return 0
 
    def disable_netboot(self,name,token=None,**rest):
        """
        This is a feature used by the pxe_just_once support, see manpage.
        Sets system named "name" to no-longer PXE.  Disabled by default as
        this requires public API access and is technically a read-write operation.
        """
        self.log("disable_netboot",token=token,name=name)
        # used by nopxe.cgi
        self._refresh()
        if not self.api.settings().pxe_just_once:
            # feature disabled!
            return False
        systems = self.api.systems()
        obj = systems.find(name=name)
        if obj == None:
            # system not found!
            return False
        obj.set_netboot_enabled(0)
        # disabling triggers and sync to make this extremely fast.
        systems.add(obj,save=True,with_triggers=False,with_sync=False,quick_pxe_update=True)
        return True

    def run_install_triggers(self,mode,objtype,name,ip,token=None,**rest):

        """
        This is a feature used to run the pre/post install triggers.
        See CobblerTriggers on Wiki for details
        """

        self.log("run_install_triggers",token=token)

        if mode != "pre" and mode != "post":
            return False
        if objtype != "system" and objtype !="profile":
            return False

        # the trigger script is called with name,mac, and ip as arguments 1,2, and 3
        # we do not do API lookups here because they are rather expensive at install
        # time if reinstalling all of a cluster all at once.
        # we can do that at "cobbler check" time.

        utils.run_triggers(None, "/var/lib/cobbler/triggers/install/%s/*" % mode, additional=[objtype,name,ip])


        return True

    def _refresh(self):
        """
        Internal function to reload cobbler's configuration from disk.  This is used to prevent any out
        of band management (the cobbler CLI, or yaml hacking, etc) from resulting in the
        cobbler state of XMLRPC API's daemon being different from the actual on-disk state.
        """
        self.api.clear() 
        self.api.deserialize()


    def version(self,token=None,**rest):
        """
        Return the cobbler version for compatibility testing with remote applications.
        Returns as a float, 0.6.1-2 should result in (int) "0.612".
        """
        self.log("version",token=token)
        return self.api.version()

    def get_distros(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler distros as an array of hashes.
        """
        self.log("get_distros",token=token)
        return self.__get_all("distro",page,results_per_page)

    def get_profiles(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler profiles as an array of hashes.
        """
        self.log("get_profiles",token=token)
        return self.__get_all("profile",page,results_per_page)

    def get_systems(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler systems as an array of hashes.
        """
        self.log("get_systems",token=token)
        return self.__get_all("system",page,results_per_page)

    def get_repos(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler repos as an array of hashes.
        """
        self.log("get_repos",token=token)
        return self.__get_all("repo",page,results_per_page)
   
    def get_repos_compatible_with_profile(self,profile=None,token=None,**rest):
        """
        Get repos that can be used with a given profile name
        """
        self.log("get_repos_compatible_with_profile",token=token)
        profile = self.api.find_profile(profile)
        if profile is None:
            return -1
        results = []
        distro = profile.get_conceptual_parent()
        repos = self.get_repos()
        for r in repos:
           # there be dragons!
           # accept all repos that are src/noarch
           # but otherwise filter what repos are compatible
           # with the profile based on the arch of the distro.
           if r["arch"] is None or r["arch"] in [ "", "noarch", "src" ]:
              results.append(r)
           else:
              # some backwards compatibility fuzz
              # repo.arch is mostly a text field
              # distro.arch is i386/x86_64/ia64/s390x/etc
              if r["arch"] in [ "i386", "x86", "i686" ]:
                  if distro.arch in [ "i386", "x86" ]:
                      results.append(r)
              elif r["arch"] in [ "x86_64" ]:
                  if distro.arch in [ "x86_64" ]:
                      results.append(r)
              elif r["arch"].startswith("s390"):
                  if distro.arch in [ "s390x" ]:
                      results.append(r)
              else:
                  if distro.arch == r["arch"]:
                      results.append(r)
        return results    
              
    def get_images(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler images as an array of hashes.
        """
        self.log("get_images",token=token)
        return self.__get_all("image",page,results_per_page)

    def __get_specific(self,collection_type,name,flatten=False):
        """
        Internal function to return a hash representation of a given object if it exists,
        otherwise an empty hash will be returned.
        """
        result = self.api.deserialize_item_raw(collection_type, name)
        if result is None:
            return {}
        if flatten:
            result = utils.flatten(result)
        return self._fix_none(result)

    def get_distro(self,name,flatten=False,token=None,**rest):
        """
        Returns the distro named "name" as a hash.
        """
        self.log("get_distro",token=token,name=name)
        return self.__get_specific("distro",name,flatten=flatten)

    def get_profile(self,name,flatten=False,token=None,**rest):
        """
        Returns the profile named "name" as a hash.
        """
        self.log("get_profile",token=token,name=name)
        return self.__get_specific("profile",name,flatten=flatten)

    def get_system(self,name,flatten=False,token=None,**rest):
        """
        Returns the system named "name" as a hash.
        """
        self.log("get_system",name=name,token=token)
        return self.__get_specific("system",name,flatten=flatten)

    def find_system_by_hostname(self,hostname):
        # FIXME: implement using api.py's find API
        # and expose generic finds for other methods
        # WARNING: this function is /not/ expected to stay in cobbler long term
        systems = self.get_systems()
        for x in systems:
           for y in x["interfaces"]:
              if x["interfaces"][y]["hostname"] == hostname:
                  name = x["name"]
                  return self.get_system_for_koan(name)
        return {}

    def get_repo(self,name,flatten=False,token=None,**rest):
        """
        Returns the repo named "name" as a hash.
        """
        self.log("get_repo",name=name,token=token)
        return self.__get_specific("repo",name,flatten=flatten)
    
    def get_image(self,name,flatten=False,token=None,**rest):
        """
        Returns the repo named "name" as a hash.
        """
        self.log("get_image",name=name,token=token)
        return self.__get_specific("image",name,flatten=flatten)

    def get_distro_as_rendered(self,name,token=None,**rest):
        """
        Return the distribution as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_distro_for_koan(self,name)

    def get_distro_for_koan(self,name,token=None,**rest):
        """
        Same as get_distro_as_rendered.
        """
        self.log("get_distro_as_rendered",name=name,token=token)
        self._refresh()
        obj = self.api.distros().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_profile_as_rendered(self,name,token=None,**rest):
        """
        Return the profile as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_profile_for_koan(name,token)

    def get_profile_for_koan(self,name,token=None,**rest):
        """
        Same as get_profile_as_rendered
        """
        self.log("get_profile_as_rendered", name=name, token=token)
        self._refresh()
        obj = self.api.profiles().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_system_as_rendered(self,name,token=None,**rest):
        """
        Return the system as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_system_for_koan(self,name)

    def get_system_for_koan(self,name,token=None,**rest):
        """
        Same as get_system_as_rendered.
        """
        self.log("get_system_as_rendered",name=name,token=token)
        self._refresh()
        obj = self.api.systems().find(name=name)
        if obj is not None:
           return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_repo_as_rendered(self,name,token=None,**rest):
        """
        Return the repo as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_repo_for_koan(self,name)

    def get_repo_for_koan(self,name,token=None,**rest):
        """
        Same as get_repo_as_rendered.
        """
        self.log("get_repo_as_rendered",name=name,token=token)
        self._refresh()
        obj = self.api.repos().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})
    
    def get_image_as_rendered(self,name,token=None,**rest):
        """
        Return the image as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_image_for_koan(self,name)

    def get_image_for_koan(self,name,token=None,**rest):
        """
        Same as get_image_as_rendered.
        """
        self.log("get_image_as_rendered",name=name,token=token)
        self._refresh()
        obj = self.api.images().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_random_mac(self,token=None,**rest):
        """
        Wrapper for utils.get_random_mac

        Used in the webui
        """
        self.log("get_random_mac",token=None)
        self._refresh()
        return utils.get_random_mac(self.api)

    def _fix_none(self,data):
        """
        Convert None in XMLRPC to just '~'.  The above
        XMLRPC module hack should do this, but let's make extra sure.
        """

        if data is None:
            data = '~'

        elif type(data) == list:
            data = [ self._fix_none(x) for x in data ]

        elif type(data) == dict:
            for key in data.keys():
               data[key] = self._fix_none(data[key])

        return data

    def get_status(self,**rest):
        """
        Returns the same information as `cobbler status`
        """
        return self.api.status()

# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************


class ProxiedXMLRPCInterface:

    def __init__(self,api,logger,proxy_class,enable_auth_if_relevant=True):
        self.logger  = logger
        self.proxied = proxy_class(api,logger,enable_auth_if_relevant)

    def _dispatch(self, method, params, **rest):

        if not hasattr(self.proxied, method):
            self.logger.error("remote:unknown method %s" % method)
            raise CX(_("Unknown remote method"))

        method_handle = getattr(self.proxied, method)

        try:
            return method_handle(*params)
        except Exception, e:
            utils.log_exc(self.logger)
            raise e

# **********************************************************************

class CobblerReadWriteXMLRPCInterface(CobblerXMLRPCInterface):

    def __init__(self,api,logger,enable_auth_if_relevant):
        self.api = api
        self.auth_enabled = enable_auth_if_relevant
        self.logger = logger
        self.token_cache = TOKEN_CACHE
        self.object_cache = OBJECT_CACHE
        random.seed(time.time())

    def __next_id(self,retry=0):
        """
        Used for keeping track of temporary objects.  The return value
        is a semi-unique key and has no bearing on reality.
        """
        if retry > 10:
            # I have no idea why this would happen but I want to be through :)
            raise CX(_("internal error"))
        next_id = self.__get_random(25)
        if self.object_cache.has_key(next_id):
            return self.__next_id(retry=retry+1) 
        return next_id

    def __get_random(self,length):
        urandom = open("/dev/urandom")
        b64 = base64.encodestring(urandom.read(25))
        urandom.close()
        return b64 

    def __make_token(self,user):
        """
        Returns a new random token.
        """
        b64 = self.__get_random(25)
        self.token_cache[b64] = (time.time(), user)
        return b64

    def __invalidate_expired_objects(self):
        """
        Deletes any objects that are floating around in
        the cache after a reasonable interval.
        """ 
        timenow = time.time()
        for object_id in self.object_cache.keys():
            (reference, object_time) = self.object_cache[object_id]
            if (timenow > object_time + OBJECT_TIMEOUT):
                self.log("expiring object reference: %s" % id,debug=True)
                del self.object_cache[object_id]

    def __invalidate_expired_tokens(self):
        """
        Deletes any login tokens that might have expired.
        """
        timenow = time.time()
        for token in self.token_cache.keys():
            (tokentime, user) = self.token_cache[token]
            if (timenow > tokentime + TOKEN_TIMEOUT):
                self.log("expiring token",token=token,debug=True)
                del self.token_cache[token]

    def __validate_user(self,input_user,input_password):
        """
        Returns whether this user/pass combo should be given
        access to the cobbler read-write API.

        For the system user, this answer is always "yes", but
        it is only valid for the socket interface.

        FIXME: currently looks for users in /etc/cobbler/auth.conf
        Would be very nice to allow for PAM and/or just Kerberos.
        """
        return self.api.authenticate(input_user,input_password)

    def __validate_token(self,token): 
        """
        Checks to see if an API method can be called when
        the given token is passed in.  Updates the timestamp
        of the token automatically to prevent the need to
        repeatedly call login().  Any method that needs
        access control should call this before doing anything
        else.
        """
        self.__invalidate_expired_tokens()
        self.__invalidate_expired_objects()

        #if not self.auth_enabled:
        #    user = self.get_user_from_token(token)
        #    # old stuff, preserving for future usage
        #    # if user == "<system>":
        #    #    self.token_cache[token] = (time.time(), user) # update to prevent timeout
        #    #    return True

        if self.token_cache.has_key(token):
            user = self.get_user_from_token(token)
            if user == "<system>":
               # system token is only valid over Unix socket
               return False
            self.token_cache[token] = (time.time(), user) # update to prevent timeout
            return True
        else:
            self.log("invalid token",token=token)
            raise CX(_("invalid token: %s" % token))

    def __name_to_object(self,resource,name):
        if resource.find("distro") != -1:
            return self.api.find_distro(name)
        if resource.find("profile") != -1:
            return self.api.find_profile(name)
        if resource.find("system") != -1:
            return self.api.find_system(name)
        if resource.find("repo") != -1:
            return self.api.find_repo(name)
        return None

    def check_access_no_fail(self,token,resource,arg1=None,arg2=None):
        """
        This is called by the WUI to decide whether an element
        is editable or not. It differs form check_access in that
        it is supposed to /not/ log the access checks (TBA) and does
        not raise exceptions.
        """

        need_remap = False
        for x in [ "distro", "profile", "system", "repo" ]:
           if arg1 is not None and resource.find(x) != -1:
              need_remap = True
              break

        if need_remap:
           # we're called with an object name, but need an object
           arg1 = self.__name_to_object(resource,arg1)

        try:
           self.check_access(token,resource,arg1,arg2)
           return True 
        except:
           utils.log_exc(self.logger)
           return False 

    def check_access(self,token,resource,arg1=None,arg2=None):
        validated = self.__validate_token(token)
        user = self.get_user_from_token(token)
        if not self.auth_enabled:
            # for public read-only XMLRPC, permit access
            self.log("permitting read-only access")
            return True
        rc = self.__authorize(token,resource,arg1,arg2)
        self.log("authorization result: %s" % rc)
        if not rc:
            raise CX(_("authorization failure for user %s" % user)) 
        return rc

    def login(self,login_user,login_password):
        """
        Takes a username and password, validates it, and if successful
        returns a random login token which must be used on subsequent
        method calls.  The token will time out after a set interval if not
        used.  Re-logging in permitted.
        """
        self.log("login attempt", user=login_user)
        if self.__validate_user(login_user,login_password):
            token = self.__make_token(login_user)
            self.log("login succeeded",user=login_user)
            return token
        else:
            self.log("login failed",user=login_user)
            raise CX(_("login failed: %s") % login_user)

    def __authorize(self,token,resource,arg1=None,arg2=None):
        user = self.get_user_from_token(token)
        args = [ resource, arg1, arg2 ]
        self.log("calling authorize for resource %s" % args, user=user)

        rc = self.api.authorize(user,resource,arg1,arg2)
        if rc:
            return True
        else:
            raise CX(_("user does not have access to resource: %s") % resource)

    def logout(self,token):
        """
        Retires a token ahead of the timeout.
        """
        self.log("logout", token=token)
        if self.token_cache.has_key(token):
            del self.token_cache[token]
            return True
        return False    

    def token_check(self,token):
        """
        This is a demo function that does not return anything useful.
        """
        self.__validate_token(token)
        return True

    def __store_object(self,reference):
        """
        Helper function to create a new object and store it in the
        object cache.
        """
        if reference is None:
           # this is undoubtedly from a get_*_handle call
           raise CX(_("no object found"))
        object_id = self.__next_id()
        self.object_cache[object_id] = (reference, time.time())
        return object_id

    def __get_object(self,object_id):
        """
        Helper function to load an object from the object cache.  Raises
        an exception if there is no object as specified.
        """
        if self.object_cache.has_key(object_id):
            return self.object_cache[object_id][0]
        raise CX(_("No such object for ID: %s") % object_id)

    def sync(self,token):
        """
        Run sync code, which should complete before XMLRPC timeout.  We can't
        do reposync this way.  Would be nice to send output over AJAX/other
        later.
        """
        self.log("sync",token=token)
        self.check_access(token,"sync")
        return self.api.sync()

    def new_distro(self,token):
        """
        Creates a new (unconfigured) distro object.  It works something like
        this:
              token = remote.login("user","pass")
              distro_id = remote.new_distro(token)
              remote.modify_distro(distro_id, 'name', 'example-distro', token)
              remote.modify_distro(distro_id, 'kernel', '/foo/vmlinuz', token)
              remote.modify_distro(distro_id, 'initrd', '/foo/initrd.img', token)
              remote.save_distro(distro_id, token)
        """      
        self.log("new_distro",token=token)
        self.check_access(token,"new_distro")
        return self.__store_object(item_distro.Distro(self.api._config))

    def new_profile(self,token):    
        """
        Creates a new (unconfigured) profile object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.log("new_profile",token=token)
        self.check_access(token,"new_profile")
        return self.__store_object(item_profile.Profile(self.api._config))

    def new_subprofile(self,token):
        """
        A subprofile is a profile that inherits directly from another profile,
        not a distro.  In addition to the normal profile setup, setting
        the parent variable to the name of an existing profile is also
        mandatory.   Systems can be assigned to subprofiles just like they
        were regular profiles.  The same XMLRPC API methods work on them as profiles
        also.
        """
        self.log("new_subprofile",token=token)
        self.check_access(token,"new_subprofile")
        return self.__store_object(item_profile.Profile(self.api._config,is_subobject=True))

    def new_system(self,token):
        """
        Creates a new (unconfigured) system object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.log("new_system",token=token)
        self.check_access(token,"new_system")
        return self.__store_object(item_system.System(self.api._config))
        
    def new_repo(self,token):
        """
        Creates a new (unconfigured) repo object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self.log("new_repo",token=token)
        self.check_access(token,"new_repo")
        return self.__store_object(item_repo.Repo(self.api._config))

    def new_image(self,token):
        """
        Creates a new (unconfigured) image object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self.log("new_image",token=token)
        self.check_access(token,"new_image")
        return self.__store_object(item_image.Image(self.api._config))
       
    def get_distro_handle(self,name,token):
        """
        Given the name of an distro (or other search parameters), return an
        object id that can be passed in to modify_distro() or save_distro()
        commands.  Raises an exception if no object can be matched.
        """
        self.log("get_distro_handle",token=token,name=name)
        self.check_access(token,"get_distro_handle")
        self._refresh()
        found = self.api.distros().find(name)
        return self.__store_object(found)   

    def get_profile_handle(self,name,token):
        """
        Given the name of a profile  (or other search parameters), return an
        object id that can be passed in to modify_profile() or save_profile()
        commands.  Raises an exception if no object can be matched.
        """
        self.log("get_profile_handle",token=token,name=name)
        self.check_access(token,"get_profile_handle")
        self._refresh()
        found = self.api.profiles().find(name)
        return self.__store_object(found)   

    def get_system_handle(self,name,token):
        """
        Given the name of an system (or other search parameters), return an
        object id that can be passed in to modify_system() or save_system()
        commands. Raises an exception if no object can be matched.
        """
        self.log("get_system_handle",name=name,token=token)
        self.check_access(token,"get_system_handle")
        self._refresh()
        found = self.api.systems().find(name)
        return self.__store_object(found)   

    def get_repo_handle(self,name,token):
        """
        Given the name of an repo (or other search parameters), return an
        object id that can be passed in to modify_repo() or save_repo()
        commands.  Raises an exception if no object can be matched.
        """
        self.log("get_repo_handle",name=name,token=token)
        self.check_access(token,"get_repo_handle")
        self._refresh()
        found = self.api.repos().find(name)
        return self.__store_object(found)   

    def get_image_handle(self,name,token):
        """
        Given the name of an image (or other search parameters), return an
        object id that can be passed in to modify_image() or save_image()
        commands.  Raises an exception if no object can be matched.
        """
        self.log("get_image_handle",name=name,token=token)
        self.check_access(token,"get_image_handle")
        self._refresh()
        found = self.api.images().find(name)
        return self.__store_object(found)

    def save_distro(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified distro object to disk.
        """
        self._refresh()
        self.log("save_distro",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_distro",obj)
        if editmode == "new":
            return self.api.distros().add(obj,save=True,check_for_duplicate_names=True)
        else:
            return self.api.distros().add(obj,save=True)

    def save_profile(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified profile object to disk.
        """
        self._refresh()
        self.log("save_profile",token=token,object_id=object_id)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_profile",obj)
        if editmode == "new":
           return self.api.profiles().add(obj,save=True,check_for_duplicate_names=True)
        else:
           return self.api.profiles().add(obj,save=True)

    def save_system(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified system object to disk.
        """
        self._refresh()
        self.log("save_system",token=token,object_id=object_id)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_system",obj)
        if editmode == "new":
           return self.api.systems().add(obj,save=True,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
        elif editmode == "edit":
           return self.api.systems().add(obj,save=True,check_for_duplicate_netinfo=True)
        else:
           return self.api.systems().add(obj,save=True)
           

    def save_repo(self,object_id,token=None,editmode="bypass"):
        """
        Saves a newly created or modified repo object to disk.
        """
        self._refresh()
        self.log("save_repo",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_repo",obj)
        if editmode == "new":
           return self.api.repos().add(obj,save=True,check_for_duplicate_names=True)
        else:
           return self.api.repos().add(obj,save=True)

    def save_image(self,object_id,token=None,editmode="bypass"):
        """
        Saves a newly created or modified repo object to disk.
        """
        self._refresh()
        self.log("save_image",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_image",obj)
        if editmode == "new":
           return self.api.images().add(obj,save=True,check_for_duplicate_names=True)
        else:
           return self.api.images().add(obj,save=True)

    ## FIXME: refactor out all of the boilerplate stuff like ^^

    def copy_distro(self,object_id,newname,token=None):
        """
        All copy methods are pretty much the same.  Get an object handle, pass in the new
        name for it.
        """
        self.log("copy_distro",object_id=object_id,token=token)
        self.check_access(token,"copy_distro")
        obj = self.__get_object(object_id)
        return self.api.copy_distro(obj,newname)

    def copy_profile(self,object_id,token=None):
        self.log("copy_profile",object_id=object_id,token=token)
        self.check_access(token,"copy_profile")
        obj = self.__get_object(object_id)
        return self.api.copy_profile(obj,newname)

    def copy_system(self,object_id,token=None):
        self.log("copy_system",object_id=object_id,token=token)
        self.check_access(token,"copy_system")
        obj = self.__get_object(object_id)
        return self.api.copy_system(obj,newname)

    def copy_repo(self,object_id,token=None):
        self.log("copy_repo",object_id=object_id,token=token)
        self.check_access(token,"copy_repo")
        obj = self.__get_object(object_id)
        return self.api.copy_repo(obj,newname)

    def copy_image(self,object_id,token=None):
        self.log("copy_image",object_id=object_id,token=token)
        self.check_access(token,"copy_image")
        obj = self.__get_object(object_id)
        return self.api.copy_image(obj,newname)

    def rename_distro(self,object_id,newname,token=None):
        """
        All rename methods are pretty much the same.  Get an object handle, pass in a new
        name for it.  Rename will modify dependencies to point them at the new
        object.  
        """
        self.log("rename_distro",object_id=object_id,token=token)
        self.check_access(token,"copy_repo")
        obj = self.__get_object(object_id)
        return self.api.rename_distro(obj,newname)

    def rename_profile(self,object_id,newname,token=None):
        self.log("rename_profile",object_id=object_id,token=token)
        self.check_access(token,"rename_profile")
        obj = self.__get_object(object_id)
        return self.api.rename_profile(obj,newname)

    def rename_system(self,object_id,newname,token=None):
        self.log("rename_system",object_id=object_id,token=token)
        self.check_access(token,"rename_system")
        obj = self.__get_object(object_id)
        return self.api.rename_system(obj,newname)

    def rename_repo(self,object_id,newname,token=None):
        self.log("rename_repo",object_id=object_id,token=token)
        self.check_access(token,"rename_repo")
        obj = self.__get_object(object_id)
        return self.api.rename_repo(obj,newname)
    
    def rename_image(self,object_id,newname,token=None):
        self.log("rename_image",object_id=object_id,token=token)
        self.check_access(token,"rename_image")
        obj = self.__get_object(object_id)
        return self.api.rename_image(obj,newname)

    def __call_method(self, obj, attribute, arg):
        """
        Internal function used by the modify routines.
        """
        method = obj.remote_methods().get(attribute, None)
        if method == None:
            raise CX(_("object has no method: %s") % attribute)
        return method(arg)

    def modify_distro(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing distro object handle.
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_distro", obj, attribute)
        return self.__call_method(obj, attribute, arg)

    def modify_profile(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing profile object handle.
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_profile", obj, attribute)
        return self.__call_method(obj, attribute, arg)

    def modify_system(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing system object handle.
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_system", obj, attribute)
        return self.__call_method(obj, attribute, arg)

    def modify_repo(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing repo object handle.
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_repo", obj, attribute)
        return self.__call_method(obj, attribute, arg)
    
    def modify_image(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing image object handle.
        """
        ## FIXME: lots of boilerplate to remove here, move to utils.py
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_image", obj, attribute)
        return self.__call_method(obj, attribute, arg)

    def remove_distro(self,name,token,recursive=1):
        """
        Deletes a distro from a collection.  Note that this just requires the name
        of the distro, not a handle.
        """
        self.log("remove_distro (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_distro", name)
        rc = self.api._config.distros().remove(name,recursive=True)
        return rc

    def remove_profile(self,name,token,recursive=1):
        """
        Deletes a profile from a collection.  Note that this just requires the name
        """
        self.log("remove_profile (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_profile", name)
        rc = self.api._config.profiles().remove(name,recursive=True)
        return rc

    def remove_system(self,name,token,recursive=1):
        """
        Deletes a system from a collection.  Note that this just requires the name
        of the distro, not a handle.
        """
        self.log("remove_system (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_system", name)
        rc = self.api._config.systems().remove(name,recursive=True)
        return rc

    def remove_repo(self,name,token,recursive=1):
        """
        Deletes a repo from a collection.  Note that this just requires the name
        of the repo, not a handle.
        """
        self.log("remove_repo (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_repo", name)
        rc = self.api._config.repos().remove(name,recursive=True)
        return rc

    def remove_image(self,name,token,recursive=1):
        """
        Deletes a image from a collection.  Note that this just requires the name
        of the image, not a handle.
        """
        self.log("remove_image (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_image", name)
        rc = self.api._config.images().remove(name,recursive=True)
        return rc

    def read_or_write_kickstart_template(self,kickstart_file,is_read,new_data,token):
        """
        Allows the WebUI to be used as a kickstart file editor.  For security
        reasons we will only allow kickstart files to be edited if they reside in
        /var/lib/cobbler/kickstarts/ or /etc/cobbler.  This limits the damage
        doable by Evil who has a cobbler password but not a system password.
        Also if living in /etc/cobbler the file must be a kickstart file.
        """

        if is_read:
           what = "read_kickstart_template"
        else:
           what = "write_kickstart_template"

        self.log(what,name=kickstart_file,token=token)
        self.check_access(token,what,kickstart_file,is_read)
 
        if kickstart_file.find("..") != -1 or not kickstart_file.startswith("/"):
            raise CX(_("tainted file location"))

        if not kickstart_file.startswith("/etc/cobbler/") and not kickstart_file.startswith("/var/lib/cobbler/kickstarts"):
            raise CX(_("unable to view or edit kickstart in this location"))
        
        if kickstart_file.startswith("/etc/cobbler/"):
           if not kickstart_file.endswith(".ks") and not kickstart_file.endswith(".cfg"):
              # take care to not allow config files to be altered.
              raise CX(_("this does not seem to be a kickstart file"))
           if not is_read and not os.path.exists(kickstart_file):
              raise CX(_("new files must go in /var/lib/cobbler/kickstarts"))
        
        if is_read:
            fileh = open(kickstart_file,"r")
            data = fileh.read()
            fileh.close()
            return data
        else:
            if new_data == -1:
                # delete requested
                if not self.is_kickstart_in_use(kickstart_file,token):
                    os.remove(kickstart_file)
                else:
                    raise CX(_("attempt to delete in-use file"))
            else:
                fileh = open(kickstart_file,"w+")
                fileh.write(new_data)
                fileh.close()
            return True


# *********************************************************************
# *********************************************************************

class CobblerReadWriteXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """
    This is just a wrapper used for launching the Read/Write XMLRPC Server.
    """

    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************
# *********************************************************************

def test_bootstrap_start_clean()

   # first some API calls (non-remote) to prep our data
   # clean out the distribution list
   api = cobbler_api.BootAPI()
   for d in api.distros():
       self.api.remove_distro(d,recursive=True)
   for i in api.images()
       self.api.remove_image(i)
   for r in api.repos()
       self.api.remove_repo(r)
   

def test_xmlrpc_ro()

   test_bootstrap_start_clean()

   rc1 = subprocess.call("/sbin/service cobblerd restart")
   assert rc1 == 0, "cobblerd restart ok"
 
   rc2 = subprocess.call("/sbin/service httpd restart")
   assert rc2 == 0, "httpd restart ok"

   xmlrpclib.server = Server("127.0.0.1/cobbler_api_rw")

   # delete all distributions
   distros = xmlrpclib.server.get_distros()
   

def test_xmlrpc_rw()

   # need tests for the various auth modes, not just one 
   pass

