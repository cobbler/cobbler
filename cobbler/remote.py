# Interface for Cobbler's XMLRPC API(s).
# there are two:
#   a read-only API that koan uses
#   a read-write API that requires logins
#
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
from rhpl.translate import _, N_, textdomain, utf8
import xmlrpclib
import random
import base64
import string
import traceback

import api as cobbler_api
import utils
from cexceptions import *
import item_distro
import item_profile
import item_system
import item_repo

# FIXME: make configurable?
TOKEN_TIMEOUT = 60*60 # 60 minutes
OBJECT_TIMEOUT = 60*60 # 60 minutes

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

    def __init__(self,api,logger):
        self.api = api
        self.logger = self.api.logger

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def ping(self):
        return True

    def get_size(self,collection_name):
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

    def get_settings(self,token=None):
        """
        Return the contents of /var/lib/cobbler/settings, which is a hash.
        """
        self.logger.debug("remote:get_settings")
        return self.__get_all("settings")
 
    def disable_netboot(self,name,token=None):
        """
        This is a feature used by the pxe_just_once support, see manpage.
        Sets system named "name" to no-longer PXE.  Disabled by default as
        this requires public API access and is technically a read-write operation.
        """
        self.logger.debug("remote:disable_netboot(%s)" % name)
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

    def run_post_install_triggers(self,name,token=None):
        """
        This is a feature used to run the post install trigger.
        It passes the system named "name" to the trigger.  Disabled by default as
        this requires public API access and is technically a read-write operation.
        """
        self.logger.debug("remote:run_post_install_triggers(%s)")

        # used by postinstalltrigger.cgi
        self.api.clear()
        self.api.deserialize()
        if not self.api.settings().run_post_install_trigger:
            # feature disabled!
            return False
        systems = self.api.systems()
        obj = systems.find(name=name)
        if obj == None:
            # system not found!
            return False
        utils.run_triggers(obj, "/var/lib/cobbler/triggers/install/post/*")
        return True

    def _refresh(self):
        """
        Internal function to reload cobbler's configuration from disk.  This is used to prevent any out
        of band management (the cobbler CLI, or yaml hacking, etc) from resulting in the
        cobbler state of XMLRPC API's daemon being different from the actual on-disk state.
        """
        self.api.clear() 
        self.api.deserialize()


    def version(self,token=None):
        """
        Return the cobbler version for compatibility testing with remote applications.
        Returns as a float, 0.6.1-2 should result in (int) "0.612".
        """
        self.logger.debug("remote:version")
        return self.api.version()

    def get_distros(self,page=None,results_per_page=None,token=None):
        """
        Returns all cobbler distros as an array of hashes.
        """
        self.logger.debug("remote:get_distros")
        return self.__get_all("distro",page,results_per_page)

    def get_profiles(self,page=None,results_per_page=None,token=None):
        """
        Returns all cobbler profiles as an array of hashes.
        """
        self.logger.debug("remote:get_profiles")
        return self.__get_all("profile",page,results_per_page)

    def get_systems(self,page=None,results_per_page=None,token=None):
        """
        Returns all cobbler systems as an array of hashes.
        """
        self.logger.debug("remote:get_systems")
        return self.__get_all("system",page,results_per_page)

    def get_repos(self,page=None,results_per_page=None,token=None):
        """
        Returns all cobbler repos as an array of hashes.
        """
        self.logger.debug("remote:get_repos")
        return self.__get_all("repo",page,results_per_page)

    def __get_specific(self,collection_fn,name,flatten=False):
        """
        Internal function to return a hash representation of a given object if it exists,
        otherwise an empty hash will be returned.
        """
        self._refresh()
        item = collection_fn().find(name=name)
        if item is None:
            return self._fix_none({})
        result = item.to_datastruct()
        if flatten:
            result = utils.flatten(result)
        return self._fix_none(result)

    def get_distro(self,name,flatten=False,token=None):
        """
        Returns the distro named "name" as a hash.
        """
        self.logger.debug("remote:get_distro(%s)" % name)
        return self.__get_specific(self.api.distros,name,flatten=flatten)

    def get_profile(self,name,flatten=False,token=None):
        """
        Returns the profile named "name" as a hash.
        """
        self.logger.debug("remote.get_profile(%s)" % name)
        return self.__get_specific(self.api.profiles,name,flatten=flatten)

    def get_system(self,name,flatten=False,token=None):
        """
        Returns the system named "name" as a hash.
        """
        self.logger.debug("remote:get_system(%s)" % name)
        return self.__get_specific(self.api.systems,name,flatten=flatten)

    def get_repo(self,name,flatten=False,token=None):
        """
        Returns the repo named "name" as a hash.
        """
        self.logger.debug("remote:get_repo(%s)" % name)
        return self.__get_specific(self.api.repos,name,flatten=flatten)

    def get_distro_as_rendered(self,name,token=None):
        """
        Return the distribution as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_distro_for_koan(self,name)

    def get_distro_for_koan(self,name,token=None):
        """
        Same as get_distro_as_rendered.
        """
        self.logger.debug("remote:get_distro_as_rendered(%s)" % name)
        self._refresh()
        obj = self.api.distros().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
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
        self.logger.debug("remote:get_profile_as_rendered(%s)" % name)
        self._refresh()
        obj = self.api.profiles().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_system_as_rendered(self,name,token=None):
        """
        Return the system as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_system_for_koan(self,name)

    def get_system_for_koan(self,name,token=None):
        """
        Same as get_system_as_rendered.
        """
        self.logger.debug("remote:get_system_as_rendered(%s)" % name)
        self._refresh()
        obj = self.api.systems().find(name=name)
        if obj is not None:
           return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_repo_as_rendered(self,name,token=None):
        """
        Return the repo as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_repo_for_koan(self,name)

    def get_repo_for_koan(self,name,token=None):
        """
        Same as get_repo_as_rendered.
        """
        self.logger.debug("remote:get_repo_as_rendered(%s)" % name)
        self._refresh()
        obj = self.api.repos().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(self.api, True, obj))
        return self._fix_none({})

    def get_random_mac(self):
        """
        Generate a random MAC address.
        from xend/server/netif.py
        Generate a random MAC address.
        Uses OUI 00-16-3E, allocated to
        Xensource, Inc.  Last 3 fields are random.
        return: MAC address string
        """
        self.logger.debug("remote:get_random_mac")
        self._refresh()
        mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) ]
        mac = ':'.join(map(lambda x: "%02x" % x, mac))
        systems = self.api.systems()
        while ( systems.find(mac_address=mac) ):
            mac = self.get_random_mac()

        return mac

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

# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************


class ProxiedXMLRPCInterface():

    def __init__(self,api,logger,proxy_class):
        self.logger  = logger
        self.proxied = proxy_class(api,logger)

    def _dispatch(self, method, params):

        # leave the following disabled (could log pw)
        # self.logger.debug("remote:dispatch %s (%s)" % (method,params))
         
        if not hasattr(self.proxied, method):
            self.logger.error("remote:unknown method %s" % method)
            raise CX(_("Unknown remote method"))

        method_handle = getattr(self.proxied, method)

        try:
            return method_handle(*params)
        except Exception, e:
            self.logger.error("remote:exception during %s, %s" % (method, str(e)))
            utils.log_exc(self.logger)
            raise e

# **********************************************************************

class CobblerReadWriteXMLRPCInterface(CobblerXMLRPCInterface):

    def __init__(self,api,logger):
        self.api = api
        self.logger = logger
        self.token_cache = {}
        self.object_cache = {} 
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
                self.logger.debug("expiring object reference: %s" %  id)
                del self.object_cache[object_id]

    def __invalidate_expired_tokens(self):
        """
        Deletes any login tokens that might have expired.
        """
        timenow = time.time()
        for token in self.token_cache.keys():
            (tokentime, user) = self.token_cache[token]
            if (timenow > tokentime + TOKEN_TIMEOUT):
                self.logger.debug("expiring token: %s" % token)
                del self.token_cache[token]

    def __validate_user(self,input_user,input_password):
        """
        Returns whether this user/pass combo should be given
        access to the cobbler read-write API.

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
        if self.token_cache.has_key(token):
            user = self.__get_user_from_token(token)
            self.token_cache[token] = (time.time(), user) # update to prevent timeout
            return True
        else:
            self.logger.debug("invalid token: %s" % token)
            raise CX(_("invalid token: %s" % token))

    def check_access(self,token,resource,arg1=None,arg2=None):
        validated = self.__validate_token(token)
        self.logger.debug("remote:check_access(%s,%s) -> %s" % (token,resource,validated))
        return self.__authorize(token,resource,arg1,arg2)

    def __get_user_from_token(self,token):
        if not self.token_cache.has_key(token):
            raise CX(_("invalid token: %s") % token)
        else:
            return self.token_cache[token][1]

    def login(self,login_user,login_password):
        """
        Takes a username and password, validates it, and if successful
        returns a random login token which must be used on subsequent
        method calls.  The token will time out after a set interval if not
        used.  Re-logging in permitted.
        """
        self.logger.debug("remote:login (%s,?)" % login_user)
        if self.__validate_user(login_user,login_password):
            token = self.__make_token(login_user)
            self.logger.debug("remote:login (%s) -> succeeded" % login_user)
            return token
        else:
            self.logger.debug("remote:login (%s) -> failed" % login_user)
            raise CX(_("login failed: %s") % login_user)

    def __authorize(self,token,resource,arg1=None,arg2=None):
        user = self.__get_user_from_token(token)
        if self.api.authorize(user,resource,arg1,arg2):
            return True
        else:
            raise CX(_("user does not have access to resource: %s") % resource)

    def logout(self,token):
        """
        Retires a token ahead of the timeout.
        """
        self.logger.debug("remote:logout(%s)" % token)
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
        self.logger.debug("remote:new_distro")
        self.check_access(token,"new_distro")
        return self.__store_object(item_distro.Distro(self.api._config))

    def new_profile(self,token):    
        """
        Creates a new (unconfigured) profile object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.logger.debug("remote:new_profile")
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
        self.logger.debug("remote:new_subprofile")
        self.check_access(token,"new_subprofile")
        return self.__store_object(item_profile.Profile(self.api._config,is_subobject=True))

    def new_system(self,token):
        """
        Creates a new (unconfigured) system object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.logger.debug("remote:new_system")
        self.check_access(token,"new_system")
        return self.__store_object(item_system.System(self.api._config))
        
    def new_repo(self,token):
        """
        Creates a new (unconfigured) repo object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self.logger.debug("remote:new_repo")
        self.check_access(token,"new_repo")
        return self.__store_object(item_repo.Repo(self.api._config))
       
    def get_distro_handle(self,name,token):
        """
        Given the name of an distro (or other search parameters), return an
        object id that can be passed in to modify_distro() or save_distro()
        commands.  Raises an exception if no object can be matched.
        """
        self.logger.debug("remote:get_distro_handle(%s)" % name)
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
        self.logger.debug("remote:get_profile_handle(%s)" % name)
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
        self.logger.debug("remote:get_system_handle(%s)" % name)
        self.check_access(token,"get_system_handle")
        self._refresh()
        found = self.api.systems().find(name)
        return self.__store_object(found)   

    def get_repo_handle(self,name,token):
        """
        Given the name of an repo (or other search parameters), return an
        object id that can be passed in to modify_repo() or save_pro()
        commands.  Raises an exception if no object can be matched.
        """
        self.logger.debug("remote:get_repo_handle(%s)" % name)
        self.check_access(token,"get_repo_handle")
        self._refresh()
        found = self.api.repos().find(name)
        return self.__store_object(found)   

    def save_distro(self,object_id,token):
        """
        Saves a newly created or modified distro object to disk.
        """
        self.logger.debug("remote:save_distro(%s)" % object_id)
        self.check_access(token,"save_distro")
        obj = self.__get_object(object_id)
        return self.api.distros().add(obj,with_copy=True)

    def save_profile(self,object_id,token):
        """
        Saves a newly created or modified profile object to disk.
        """
        self.logger.debug("remote:save_profile(%s)" % object_id)
        self.check_access(token,"save_profile")
        obj = self.__get_object(object_id)
        return self.api.profiles().add(obj,with_copy=True)

    def save_system(self,object_id,token):
        """
        Saves a newly created or modified system object to disk.
        """
        self.logger.debug("remote:save_system(%s)" % object_id)
        self.check_access(token,"save_system")
        obj = self.__get_object(object_id)
        return self.api.systems().add(obj,with_copy=True)

    def save_repo(self,object_id,token=None):
        """
        Saves a newly created or modified repo object to disk.
        """
        self.logger.debug("remote:save_repo(%s)" % object_id)
        self.check_access(token,"save_repo")
        obj = self.__get_object(object_id)
        return self.api.repos().add(obj,with_copy=True)

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
        self.logger.debug("remote:modify_distro(%s,%s,%s)" % (object_id,attribute,arg))
        self.check_access(token, "modify_distro", attribute, arg)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_profile(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing profile object handle.
        """
        self.logger.debug("remote:modify_profile(%s,%s,%s)" % (object_id,attribute,arg))
        self.check_access(token, "modify_profile", attribute, arg)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_system(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing system object handle.
        """
        self.logger.debug("remote:modify_system(%s,%s,%s)" % (object_id,attribute,arg))
        self.check_access(token, "modify_system", attribute, arg)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_repo(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing repo object handle.
        """
        self.logger.debug("remote:modify_repo(%s,%s,%s)" % (object_id,attribute,arg))
        self.check_access(token, "modify_repo", attribute, arg)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def distro_remove(self,name,token):
        """
        Deletes a distro from a collection.  Note that this just requires the name
        of the distro, not a handle.
        """
        self.logger.debug("remote:distro_remove(%s)" % (name))
        self.check_access(token, "distro_remove", name)
        rc = self.api._config.distros().remove(name)
        return rc

    def profile_remove(self,name,token):
        """
        Deletes a profile from a collection.  Note that this just requires the name
        of the profile, not a handle.
        """
        self.logger.debug("remote:profile_remove(%s)" % (name))
        self.check_access(token, "profile_remove", name)
        rc = self.api._config.profiles().remove(name)
        return rc

    def system_remove(self,name,token):
        """
        Deletes a system from a collection.  Note that this just requires the name
        of the system, not a handle.
        """
        self.logger.debug("remote:system_remove(%s)" % (name))
        self.check_access(token, "system_remove", name)
        rc = self.api._config.systems().remove(name)
        return rc

    def repo_remove(self,name,token):
        """
        Deletes a repo from a collection.  Note that this just requires the name
        of the repo, not a handle.
        """
        self.logger.debug("remote:repo_remove(%s)" % (name))
        self.check_access(token, "repo_remove", name)
        rc = self.api._config.repos().remove(name)
        return rc

    def sync(self,token): 
        """
        Applies changes in Cobbler to the filesystem.
        Editing a leaf-node object (like a system) does not require
        this, but if updating a upper-level object or a kickstart file,
        running sync at the end of operations is a good idea.  A typical
        cobbler sync may take anywhere between a few seconds and several
        minutes, so user interfaces should be programmed accordingly.
        Future versions of cobbler may understand how to do a cascade sync
        on object edits making explicit calls to sync redundant.
        """
        self.logger.debug("remote:sync()")
        self.check_access(token, sync)
        return self.api.sync() 

    def reposync(self,repos=[],token=None):
        """
        Updates one or more mirrored yum repositories.
        reposync is very slow and probably should not be used
        through the XMLRPC API, setting up reposync on nightly cron is better.
        """
        self.logger.debug("remote:reposync(%s)" % (repos))
        self.check_access(token, "reposync", repos)
        return self.api.reposync(repos)

    def import_tree(self,mirror_url,mirror_name,network_root=None,token=None):
        """
        I'm exposing this in the XMLRPC API for consistancy but as this
        can be a very long running operation usage is /not/ recommended.
        It would be better to use the CLI.  See documentation in api.py.
        This command may be removed from the API in a future release.
        """
        self.logger.debug("remote:import_tree(%s,%s)" % (mirror_url, mirror_name))
        self.check_access(token, "import_tree")
        return self.api.import_tree(mirror_url,mirror_name,network_root)

    def get_kickstart_templates(self,token):
        """
        Returns all of the kickstarts that are in use by the system.
        """
        self.logger.debug("remote:get_kickstart_templates")
        self.check_access(token, "get_kickstart_templates")
        files = {} 
        for x in self.api.profiles():
           if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
              files[x.kickstart] = 1
        for x in self.api.systems():
           if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
              files[x.kickstart] = 1
        return files.keys() 


    def read_or_write_kickstart_template(self,kickstart_file,is_read,new_data,token):
        """ 
        Allows the WebUI to be used as a kickstart file editor.  For security
        reasons we will only allow kickstart files to be edited if they reside in
        /var/lib/cobbler/kickstarts/ or /etc/cobbler.  This limits the damage
        doable by Evil who has a cobbler password but not a system password.
        Also if living in /etc/cobbler the file must be a kickstart file.
        """

        self.logger.debug("remote:read_or_write_kickstart_template(%s,%s)" % (kickstart_file,is_read))
        self.check_access(token,"read_or_write_kickstart_templates",kickstart_file,is_read)
 
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

