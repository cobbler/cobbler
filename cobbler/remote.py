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
import base64
import SimpleXMLRPCServer
import xmlrpclib
import random
import stat
import base64
import fcntl
import string
import traceback
import glob
import sub_process as subprocess

import api as cobbler_api
import utils
from cexceptions import *
import item_distro
import item_profile
import item_system
import item_repo
import item_image
from utils import *
from utils import _

# FIXME: make configurable?
TOKEN_TIMEOUT = 60*60 # 60 minutes
OBJECT_TIMEOUT = 60*60 # 60 minutes
TOKEN_CACHE = {}
OBJECT_CACHE = {}

class DataCache:

    def __init__(self, api):
        """
        Constructor
        """
        self.api = api

    def update(self,collection_type, name):
         data = self.api.deserialize_item_raw(collection_type, name)

         if data is None:
             return False

         if collection_type == "distro":
             obj = item_distro.Distro(self.api._config)
             obj.from_datastruct(data)
             self.api.add_distro(obj, False, False)

         if collection_type == "profile":
             subprofile = False
             if data.has_key("parent") and data["parent"] != "":
                subprofile = True
             obj = item_profile.Profile(self.api._config, is_subobject = subprofile)
             obj.from_datastruct(data)
             self.api.add_profile(obj, False, False)

         if collection_type == "system":
             obj = item_system.System(self.api._config)
             obj.from_datastruct(data)
             self.api.add_system(obj, False, False, False)

         if collection_type == "repo":
             obj = item_repo.Repo(self.api._config)
             obj.from_datastruct(data)
             self.api.add_repo(obj, False, False)

         if collection_type == "image":
             obj = item_image.Image(self.api._config)
             obj.from_datastruct(data)
             self.api.add_image(obj, False, False)


    def remove(self,collection_type, name):
         # for security reasons, only remove if actually gone
         data = self.api.deserialize_item_raw(collection_type, name)
         if data is None:
             if collection_type == "distro":
                 self.api.remove_distro(name, delete=False, recursive=True, with_triggers=False)
             if collection_type == "profile":
                 self.api.remove_profile(name, delete=False, recursive=True, with_triggers=False)
             if collection_type == "system":
                 self.api.remove_system(name, delete=False, recursive=True, with_triggers=False)
             if collection_type == "repo":
                 self.api.remove_repo(name, delete=False, recursive=True, with_triggers=False)
             if collection_type == "image":
                 self.api.remove_image(name, delete=False, recursive=True, with_triggers=False)

# *********************************************************************
# *********************************************************************

class CobblerXMLRPCInterface:
    """
    This is the interface used for all XMLRPC methods, for instance,
    as used by koan or CobblerWeb
 
    note:  public methods take an optional parameter token that is just
    here for consistancy with the ReadWrite API.  Read write operations do
    require the token.
    """

    def __init__(self,api,enable_auth_if_relevant):
        self.api = api
        self.auth_enabled = enable_auth_if_relevant
        self.cache = DataCache(self.api)
        self.logger = self.api.logger
        self.token_cache = TOKEN_CACHE
        self.object_cache = OBJECT_CACHE
        self.timestamp = self.api.last_modified_time()
        random.seed(time.time())

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def last_modified_time(self):
        """
        Return the time of the last modification to any object
        so that we can tell if we need to check for any other
        modified objects via more specific calls.
        """
        return self.api.last_modified_time()

    def update(self, token=None):
        # no longer neccessary
        return True

    def internal_cache_update(self, collection_type, data):
        self.cache.update(collection_type, data)
        return True

    def internal_cache_remove(self, collection_type, data):
        self.cache.remove(collection_type, data)
        return True

    def ping(self):
        return True

    def get_user_from_token(self,token):
        if not TOKEN_CACHE.has_key(token):
            raise CX(_("invalid token: %s") % token)
        else:
            return self.token_cache[token][1]

    def _log(self,msg,user=None,token=None,name=None,object_id=None,attribute=None,debug=False,error=False):

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

        if collection_name == "settings":
            data = self.api.deserialize_raw("settings")
            return self.xmlrpc_hacks(data)
        else:
            contents = []
            if collection_name.startswith("distro"):
               contents = self.api.distros()
            elif collection_name.startswith("profile"):
               contents = self.api.profiles()
            elif collection_name.startswith("system"):
               contents = self.api.systems()
            elif collection_name.startswith("repo"):
               contents = self.api.repos()
            elif collection_name.startswith("image"):
               contents = self.api.images()
            else:
               raise CX("internal error, collection name is %s" % collection_name)
            # FIXME: speed this up
            data = contents.to_datastruct()
            total_items = len(data)

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
            data = self.xmlrpc_hacks(data[start_point:end_point])

        return self.xmlrpc_hacks(data)

    def get_kickstart_templates(self,token=None,**rest):
        """
        Returns all of the kickstarts that are in use by the system.
        """
        self._log("get_kickstart_templates",token=token)
        #self.check_access(token, "get_kickstart_templates")
        return utils.get_kickstart_templates(self.api)

    def is_kickstart_in_use(self,ks,token=None,**rest):
        self._log("is_kickstart_in_use",token=token)
        for x in self.api.profiles():
           if x.kickstart is not None and x.kickstart == ks:
               return True
        for x in self.api.systems():
           if x.kickstart is not None and x.kickstart == ks:
               return True
        return False

    def generate_kickstart(self,profile=None,system=None,REMOTE_ADDR=None,REMOTE_MAC=None,**rest):
        self._log("generate_kickstart")

        if profile and not system:
            regrc = self.register_mac(REMOTE_MAC,profile)

        return self.api.generate_kickstart(profile,system)

    def get_settings(self,token=None,**rest):
        """
        Return the contents of /etc/cobbler/settings, which is a hash.
        """
        self._log("get_settings",token=token)
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
        If register_new_installs is enabled in settings, this allows
        kickstarts to add new system records for per-profile-provisioned
        systems automatically via a wget in %post.  This has security
        implications.
        READ: https://fedorahosted.org/cobbler/wiki/AutoRegistration
        """

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

        self._log("register mac for profile %s" % profile,token=token,name=mac)
        obj = self.api.new_system()
        obj.set_profile(profile)
        name = mac.replace(":","_")
        obj.set_name(name)
        obj.set_mac_address(mac, "eth0")
        obj.set_netboot_enabled(False)
        self.api.add_system(obj)
        return 0
 
    def disable_netboot(self,name,token=None,**rest):
        """
        This is a feature used by the pxe_just_once support, see manpage.
        Sets system named "name" to no-longer PXE.  Disabled by default as
        this requires public API access and is technically a read-write operation.
        """
        self._log("disable_netboot",token=token,name=name)
        # used by nopxe.cgi
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

    def upload_log_data(self, sys_name, file, size, offset, data, token=None,**rest):

        """
        This is a logger function used by the "anamon" logging system to
        upload all sorts of auxilliary data from Anaconda.
        As it's a bit of a potential log-flooder, it's off by default
        and needs to be enabled in /etc/cobbler/settings.
        """

        self._log("upload_log_data (file: '%s', size: %s, offset: %s)" % (file, size, offset), token=token, name=sys_name)

        # Check if enabled in self.api.settings()
        if not self.api.settings().anamon_enabled:
            # feature disabled!
            return False

        # Find matching system record
        systems = self.api.systems()
        obj = systems.find(name=sys_name)
        if obj == None:
            # system not found!
            self._log("upload_log_data - system '%s' not found" % sys_name, token=token, name=sys_name)
            return False

        return self.__upload_file(sys_name, file, size, offset, data)

    def __upload_file(self, sys_name, file, size, offset, data):
        '''
        system: the name of the system
        name: the name of the file
        size: size of contents (bytes)
        data: base64 encoded file contents
        offset: the offset of the chunk
         files can be uploaded in chunks, if so the size describes
         the chunk rather than the whole file. the offset indicates where
         the chunk belongs
         the special offset -1 is used to indicate the final chunk'''
        contents = base64.decodestring(data)
        del data
        if offset != -1:
            if size is not None:
                if size != len(contents): 
                    return False

        #XXX - have an incoming dir and move after upload complete
        # SECURITY - ensure path remains under uploadpath
        tt = string.maketrans("/","+")
        fn = string.translate(file, tt)
        if fn.startswith('..'):
            raise CX(_("invalid filename used: %s") % fn)

        # FIXME ... get the base dir from cobbler settings()
        udir = "/var/log/cobbler/anamon/%s" % sys_name
        if not os.path.isdir(udir):
            os.mkdir(udir, 0755)

        fn = "%s/%s" % (udir, fn)
        try:
            st = os.lstat(fn)
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        else:
            if not stat.S_ISREG(st.st_mode):
                raise CX(_("destination not a file: %s") % fn)

        fd = os.open(fn, os.O_RDWR | os.O_CREAT, 0644)
        # log_error("fd=%r" %fd)
        try:
            if offset == 0 or (offset == -1 and size == len(contents)):
                #truncate file
                fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                try:
                    os.ftruncate(fd, 0)
                    # log_error("truncating fd %r to 0" %fd)
                finally:
                    fcntl.lockf(fd, fcntl.LOCK_UN)
            if offset == -1:
                os.lseek(fd,0,2)
            else:
                os.lseek(fd,offset,0)
            #write contents
            fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB, len(contents), 0, 2)
            try:
                os.write(fd, contents)
                # log_error("wrote contents")
            finally:
                fcntl.lockf(fd, fcntl.LOCK_UN, len(contents), 0, 2)
            if offset == -1:
                if size is not None:
                    #truncate file
                    fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                    try:
                        os.ftruncate(fd, size)
                        # log_error("truncating fd %r to size %r" % (fd,size))
                    finally:
                        fcntl.lockf(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        return True

    def run_install_triggers(self,mode,objtype,name,ip,token=None,**rest):

        """
        This is a feature used to run the pre/post install triggers.
        See CobblerTriggers on Wiki for details
        """

        self._log("run_install_triggers",token=token)

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

    def version(self,token=None,**rest):
        """
        Return the cobbler version for compatibility testing with remote applications.
        See api.py for documentation.
        """
        self._log("version",token=token)
        return self.api.version()

    def extended_version(self,token=None,**rest):
        """
        Returns the full dictionary of version information.  See api.py for documentation.
        """
        self._log("version",token=token)
        return self.api.version(extended=True)

    def get_distros(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler distros as an array of hashes.
        """
        self._log("get_distros",token=token)
        return self.__get_all("distro",page,results_per_page)

    def get_distros_since(self,mtime):
        """
        Return all of the distro objects that have been modified
        after mtime.
        """
        data = self.api.get_distros_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_profiles_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_profiles_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_systems_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_systems_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_repos_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_repos_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_images_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_images_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_profiles(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler profiles as an array of hashes.
        """
        self._log("get_profiles",token=token)
        return self.__get_all("profile",page,results_per_page)

    def get_systems(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler systems as an array of hashes.
        """
        self._log("get_systems",token=token)
        return self.__get_all("system",page,results_per_page)

    def get_repos(self,page=None,results_per_page=None,token=None,**rest):
        """
        Returns all cobbler repos as an array of hashes.
        """
        self._log("get_repos",token=token)
        return self.__get_all("repo",page,results_per_page)
   
    def get_repos_compatible_with_profile(self,profile=None,token=None,**rest):
        """
        Get repos that can be used with a given profile name
        """
        self._log("get_repos_compatible_with_profile",token=token)
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
        self._log("get_images",token=token)
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
        return self.xmlrpc_hacks(result)

    def get_distro(self,name,flatten=False,token=None,**rest):
        """
        Returns the distro named "name" as a hash.
        """
        self._log("get_distro",token=token,name=name)
        return self.__get_specific("distro",name,flatten=flatten)

    def get_profile(self,name,flatten=False,token=None,**rest):
        """
        Returns the profile named "name" as a hash.
        """
        self._log("get_profile",token=token,name=name)
        return self.__get_specific("profile",name,flatten=flatten)

    def get_system(self,name,flatten=False,token=None,**rest):
        """
        Returns the system named "name" as a hash.
        """
        self._log("get_system",name=name,token=token)
        return self.__get_specific("system",name,flatten=flatten)

    # this is used by the puppet external nodes feature
    def find_system_by_dns_name(self,dns_name):
        # FIXME: implement using api.py's find API
        # and expose generic finds for other methods
        # WARNING: this function is /not/ expected to stay in cobbler long term
        systems = self.get_systems()
        for x in systems:
           for y in x["interfaces"]:
              if x["interfaces"][y]["dns_name"] == dns_name:
                  name = x["name"]
                  return self.get_system_for_koan(name)
        return {}

    def get_repo(self,name,flatten=False,token=None,**rest):
        """
        Returns the repo named "name" as a hash.
        """
        self._log("get_repo",name=name,token=token)
        return self.__get_specific("repo",name,flatten=flatten)
    
    def get_image(self,name,flatten=False,token=None,**rest):
        """
        Returns the repo named "name" as a hash.
        """
        self._log("get_image",name=name,token=token)
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
        self._log("get_distro_as_rendered",name=name,token=token)
        obj = self.api.find_distro(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

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
        self._log("get_profile_as_rendered", name=name, token=token)
        obj = self.api.find_profile(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

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
        self._log("get_system_as_rendered",name=name,token=token)
        obj = self.api.find_system(name=name)
        if obj is not None:
           return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

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
        self._log("get_repo_as_rendered",name=name,token=token)
        obj = self.api.find_repo(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})
    
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
        self._log("get_image_as_rendered",name=name,token=token)
        obj = self.api.find_image(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_random_mac(self,token=None,**rest):
        """
        Wrapper for utils.get_random_mac

        Used in the webui
        """
        self._log("get_random_mac",token=None)
        return utils.get_random_mac(self.api)

    def xmlrpc_hacks(self,data):
        """
        Convert None in XMLRPC to just '~' to make extra sure a client
        that can't allow_none can deal with this.  ALSO: a weird hack ensuring
        that when dicts with integer keys (or other types) are transmitted
        with string keys.
        """

        if data is None:
            data = '~'

        elif type(data) == list:
            data = [ self.xmlrpc_hacks(x) for x in data ]

        elif type(data) == dict:
            data2 = {}
            for key in data.keys():
               data2[str(key)] = self.xmlrpc_hacks(data[key])
            return data2

        return data

    def get_status(self,**rest):
        """
        Returns the same information as `cobbler status`
        """
        return self.api.status()

   ######
   # READ WRITE METHODS BELOW REQUIRE A TOKEN, use login()
   # TO OBTAIN ONE
   ######


    def __next_id(self,retry=0):
        """
        Used for keeping track of temporary objects.  The return value
        is a semi-unique key and has no bearing on reality.
        """
        if retry > 10:
            # I have no idea why this would happen but I want to be through :)
            raise CX(_("internal error, retry exceeded"))
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
                self._log("expiring object reference: %s" % id,debug=True)
                del self.object_cache[object_id]

    def __invalidate_expired_tokens(self):
        """
        Deletes any login tokens that might have expired.
        """
        timenow = time.time()
        for token in self.token_cache.keys():
            (tokentime, user) = self.token_cache[token]
            if (timenow > tokentime + TOKEN_TIMEOUT):
                self._log("expiring token",token=token,debug=True)
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
            self._log("invalid token",token=token)
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
            self._log("permitting read-only access")
            return True
        rc = self.__authorize(token,resource,arg1,arg2)
        self._log("authorization result: %s" % rc)
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
        self._log("login attempt", user=login_user)
        if self.__validate_user(login_user,login_password):
            token = self.__make_token(login_user)
            self._log("login succeeded",user=login_user)
            return token
        else:
            self._log("login failed",user=login_user)
            raise CX(_("login failed: %s") % login_user)

    def __authorize(self,token,resource,arg1=None,arg2=None):
        user = self.get_user_from_token(token)
        args = [ resource, arg1, arg2 ]
        self._log("calling authorize for resource %s" % args, user=user)

        rc = self.api.authorize(user,resource,arg1,arg2)
        if rc:
            return True
        else:
            raise CX(_("user does not have access to resource: %s") % resource)

    def logout(self,token):
        """
        Retires a token ahead of the timeout.
        """
        self._log("logout", token=token)
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
        # FIXME: performance
        self._log("sync",token=token)
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
        self._log("new_distro",token=token)
        self.check_access(token,"new_distro")
        return self.__store_object(item_distro.Distro(self.api._config))

    def new_profile(self,token):    
        """
        Creates a new (unconfigured) profile object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self._log("new_profile",token=token)
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
        self._log("new_subprofile",token=token)
        self.check_access(token,"new_subprofile")
        return self.__store_object(item_profile.Profile(self.api._config,is_subobject=True))

    def new_system(self,token):
        """
        Creates a new (unconfigured) system object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self._log("new_system",token=token)
        self.check_access(token,"new_system")
        return self.__store_object(item_system.System(self.api._config))
        
    def new_repo(self,token):
        """
        Creates a new (unconfigured) repo object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self._log("new_repo",token=token)
        self.check_access(token,"new_repo")
        return self.__store_object(item_repo.Repo(self.api._config))

    def new_image(self,token):
        """
        Creates a new (unconfigured) image object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self._log("new_image",token=token)
        self.check_access(token,"new_image")
        return self.__store_object(item_image.Image(self.api._config))
       
    def get_distro_handle(self,name,token):
        """
        Given the name of an distro (or other search parameters), return an
        object id that can be passed in to modify_distro() or save_distro()
        commands.  Raises an exception if no object can be matched.
        """
        self._log("get_distro_handle",token=token,name=name)
        self.check_access(token,"get_distro_handle")
        found = self.api.find_distro(name)
        return self.__store_object(found)   

    def get_profile_handle(self,name,token):
        """
        Given the name of a profile  (or other search parameters), return an
        object id that can be passed in to modify_profile() or save_profile()
        commands.  Raises an exception if no object can be matched.
        """
        self._log("get_profile_handle",token=token,name=name)
        self.check_access(token,"get_profile_handle")
        found = self.api.find_profile(name)
        return self.__store_object(found)   

    def get_system_handle(self,name,token):
        """
        Given the name of an system (or other search parameters), return an
        object id that can be passed in to modify_system() or save_system()
        commands. Raises an exception if no object can be matched.
        """
        self._log("get_system_handle",name=name,token=token)
        self.check_access(token,"get_system_handle")
        found = self.api.find_system(name)
        return self.__store_object(found)   

    def get_repo_handle(self,name,token):
        """
        Given the name of an repo (or other search parameters), return an
        object id that can be passed in to modify_repo() or save_repo()
        commands.  Raises an exception if no object can be matched.
        """
        self._log("get_repo_handle",name=name,token=token)
        self.check_access(token,"get_repo_handle")
        found = self.api.find_repo(name)
        return self.__store_object(found)   

    def get_image_handle(self,name,token):
        """
        Given the name of an image (or other search parameters), return an
        object id that can be passed in to modify_image() or save_image()
        commands.  Raises an exception if no object can be matched.
        """
        self._log("get_image_handle",name=name,token=token)
        self.check_access(token,"get_image_handle")
        found = self.api.find_image(name)
        return self.__store_object(found)

    def save_distro(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified distro object to disk.
        """
        self._log("save_distro",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_distro",obj)
        if editmode == "new":
            return self.api.add_distro(obj,check_for_duplicate_names=True)
        else:
            return self.api.add_distro(obj)

    def save_profile(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified profile object to disk.
        """
        self._log("save_profile",token=token,object_id=object_id)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_profile",obj)
        if editmode == "new":
           return self.api.add_profile(obj,check_for_duplicate_names=True)
        else:
           return self.api.add_profile(obj)

    def save_system(self,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified system object to disk.
        """
        self._log("save_system",token=token,object_id=object_id)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_system",obj)
        if editmode == "new":
           return self.api.add_system(obj,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
        elif editmode == "edit":
           return self.api.add_system(obj,check_for_duplicate_netinfo=True)
        else:
           return self.api.add_system(obj)
           

    def save_repo(self,object_id,token=None,editmode="bypass"):
        """
        Saves a newly created or modified repo object to disk.
        """
        self._log("save_repo",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_repo",obj)
        if editmode == "new":
           return self.api.add_repo(obj,check_for_duplicate_names=True)
        else:
           return self.api.add_repo(obj)

    def save_image(self,object_id,token=None,editmode="bypass"):
        """
        Saves a newly created or modified repo object to disk.
        """
        self._log("save_image",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_image",obj)
        if editmode == "new":
           return self.api.add_image(obj,check_for_duplicate_names=True)
        else:
           return self.api.add_image(obj)

    ## FIXME: refactor out all of the boilerplate stuff like ^^

    def copy_distro(self,object_id,newname,token=None):
        """
        All copy methods are pretty much the same.  Get an object handle, pass in the new
        name for it.
        """
        self._log("copy_distro",object_id=object_id,token=token)
        self.check_access(token,"copy_distro")
        obj = self.__get_object(object_id)
        return self.api.copy_distro(obj,newname)

    def copy_profile(self,object_id,newname,token=None):
        self._log("copy_profile",object_id=object_id,token=token)
        self.check_access(token,"copy_profile")
        obj = self.__get_object(object_id)
        return self.api.copy_profile(obj,newname)

    def copy_system(self,object_id,newname,token=None):
        self._log("copy_system",object_id=object_id,token=token)
        self.check_access(token,"copy_system")
        obj = self.__get_object(object_id)
        return self.api.copy_system(obj,newname)

    def copy_repo(self,object_id,newname,token=None):
        self._log("copy_repo",object_id=object_id,token=token)
        self.check_access(token,"copy_repo")
        obj = self.__get_object(object_id)
        return self.api.copy_repo(obj,newname)

    def copy_image(self,object_id,newname,token=None):
        self._log("copy_image",object_id=object_id,token=token)
        self.check_access(token,"copy_image")
        obj = self.__get_object(object_id)
        return self.api.copy_image(obj,newname)

    def rename_distro(self,object_id,newname,token=None):
        """
        All rename methods are pretty much the same.  Get an object handle, pass in a new
        name for it.  Rename will modify dependencies to point them at the new
        object.  
        """
        self._log("rename_distro",object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        return self.api.rename_distro(obj,newname)

    def rename_profile(self,object_id,newname,token=None):
        self._log("rename_profile",object_id=object_id,token=token)
        self.check_access(token,"rename_profile")
        obj = self.__get_object(object_id)
        return self.api.rename_profile(obj,newname)

    def rename_system(self,object_id,newname,token=None):
        self._log("rename_system",object_id=object_id,token=token)
        self.check_access(token,"rename_system")
        obj = self.__get_object(object_id)
        return self.api.rename_system(obj,newname)

    def rename_repo(self,object_id,newname,token=None):
        self._log("rename_repo",object_id=object_id,token=token)
        self.check_access(token,"rename_repo")
        obj = self.__get_object(object_id)
        return self.api.rename_repo(obj,newname)
    
    def rename_image(self,object_id,newname,token=None):
        self._log("rename_image",object_id=object_id,token=token)
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
        self._log("remove_distro (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_distro", name)
        rc = self.api.remove_distro(name,recursive=True)
        return rc

    def remove_profile(self,name,token,recursive=1):
        """
        Deletes a profile from a collection.  Note that this just requires the name
        """
        self._log("remove_profile (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_profile", name)
        rc = self.api.remove_profile(name,recursive=True)
        return rc

    def remove_system(self,name,token,recursive=1):
        """
        Deletes a system from a collection.  Note that this just requires the name
        of the distro, not a handle.
        """
        self._log("remove_system (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_system", name)
        rc = self.api.remove_system(name)
        return rc

    def remove_repo(self,name,token,recursive=1):
        """
        Deletes a repo from a collection.  Note that this just requires the name
        of the repo, not a handle.
        """
        self._log("remove_repo (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_repo", name)
        rc = self.api.remove_repo(name, recursive=True)
        return rc

    def remove_image(self,name,token,recursive=1):
        """
        Deletes a image from a collection.  Note that this just requires the name
        of the image, not a handle.
        """
        self._log("remove_image (%s)" % recursive,name=name,token=token)
        self.check_access(token, "remove_image", name)
        rc = self.api.remove_image(name, recursive=True)
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

        self._log(what,name=kickstart_file,token=token)
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

    def power_system(self,object_id,power=None,token=None):
        """
        Allows poweron/poweroff/reboot of a system
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "power_system", obj)
        if power=="on":
            rc=self.api.power_on(obj)
        elif power=="off":
            rc=self.api.power_off(obj)
        elif power=="reboot":
            rc=self.api.reboot(obj)
        else:
            raise CX(_("invalid power mode '%s', expected on/off/reboot" % power))
        return rc





# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************


class ProxiedXMLRPCInterface:

    def __init__(self,api,proxy_class,enable_auth_if_relevant=True):
        self.proxied = proxy_class(api,enable_auth_if_relevant)
        self.logger = self.proxied.api.logger

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

# *********************************************************************
# *********************************************************************

def _test_setup_modules(authn="authn_testing",authz="authz_allowall",pxe_once=1):

    # rewrite modules.conf so we know we can use the testing module
    # for xmlrpc rw testing (Makefile will put the user value back)
    
    import yaml
    import Cheetah.Template as Template

    MODULES_TEMPLATE = "installer_templates/modules.conf.template"
    DEFAULTS = "installer_templates/defaults"
    data = yaml.loadFile(DEFAULTS).next()
    data["authn_module"] = authn
    data["authz_module"] = authz
    data["pxe_once"] = pxe_once
    
    t = Template.Template(file=MODULES_TEMPLATE, searchList=[data])
    open("/etc/cobbler/modules.conf","w+").write(t.respond())


def _test_setup_settings(pxe_once=1):

    # rewrite modules.conf so we know we can use the testing module
    # for xmlrpc rw testing (Makefile will put the user value back)
   
    import yaml
    import Cheetah.Template as Template

    MODULES_TEMPLATE = "installer_templates/settings.template"
    DEFAULTS = "installer_templates/defaults"
    data = yaml.loadFile(DEFAULTS).next()
    data["pxe_once"] = pxe_once

    t = Template.Template(file=MODULES_TEMPLATE, searchList=[data])
    open("/etc/cobbler/settings","w+").write(t.respond())

    

def _test_bootstrap_restart():

   rc1 = subprocess.call(["/sbin/service","cobblerd","restart"],shell=False,close_fds=True)
   assert rc1 == 0
   rc2 = subprocess.call(["/sbin/service","httpd","restart"],shell=False,close_fds=True)
   assert rc2 == 0
   time.sleep(5)
   
   _test_remove_objects()

def _test_remove_objects():

   api = cobbler_api.BootAPI() # local handle

   # from ro tests
   d0 = api.find_distro("distro0")
   i0 = api.find_image("image0")
   r0 = api.find_image("repo0")

   # from rw tests
   d1 = api.find_distro("distro1")
   i1 = api.find_image("image1")
   r1 = api.find_image("repo1")
   
   if d0 is not None: api.remove_distro(d0, recursive = True)
   if i0 is not None: api.remove_image(i0)
   if r0 is not None: api.remove_repo(r0)
   if d1 is not None: api.remove_distro(d1, recursive = True)
   if i1 is not None: api.remove_image(i1)
   if r1 is not None: api.remove_repo(r1)
   

def test_xmlrpc_ro():

   _test_bootstrap_restart()

   server = xmlrpclib.Server("http://127.0.0.1/cobbler_api")
   time.sleep(2) 

   # delete all distributions
   distros  = server.get_distros()
   profiles = server.get_profiles()
   systems  = server.get_systems()
   repos    = server.get_repos()
   images   = server.get_systems()
   settings = server.get_settings()
    
   assert type(distros) == type([])
   assert type(profiles) == type([]) 
   assert type(systems) == type([])
   assert type(repos) == type([])
   assert type(images) == type([])
   assert type(settings) == type({})

   # now populate with something more useful
   # using the non-remote API

   api = cobbler_api.BootAPI() # local handle

   before_distros  = len(api.distros())
   before_profiles = len(api.profiles())
   before_systems  = len(api.systems())
   before_repos    = len(api.repos())
   before_images   = len(api.images())

   fake = open("/tmp/cobbler.fake","w+")
   fake.write("")
   fake.close()

   distro = api.new_distro()
   distro.set_name("distro0")
   distro.set_kernel("/tmp/cobbler.fake")
   distro.set_initrd("/tmp/cobbler.fake")
   api.add_distro(distro)
   
   repo = api.new_repo()
   repo.set_name("repo0")

   if not os.path.exists("/tmp/empty"):
      os.mkdir("/tmp/empty",770)
   repo.set_mirror("/tmp/empty")
   files = glob.glob("rpm-build/*.rpm")
   if len(files) == 0:
      raise Exception("Tests must be run from the cobbler checkout directory.")
   subprocess.call("cp rpm-build/*.rpm /tmp/empty",shell=True,close_fds=True)
   api.add_repo(repo)

   profile = api.new_profile()
   profile.set_name("profile0")
   profile.set_distro("distro0")
   profile.set_kickstart("/var/lib/cobbler/kickstarts/sample.ks")
   profile.set_repos(["repo0"])
   api.add_profile(profile)

   system = api.new_system()
   system.set_name("system0")
   system.set_hostname("hostname0")
   system.set_gateway("192.168.1.1")
   system.set_profile("profile0")
   system.set_dns_name("hostname0","eth0")
   api.add_system(system)

   image = api.new_image()
   image.set_name("image0")
   image.set_file("/tmp/cobbler.fake")
   api.add_image(image)

   # reposync is required in order to create the repo config files
   api.reposync(name="repo0")
   
   # FIXME: the following tests do not yet look to see that all elements
   # retrieved match what they were created with, but we presume this
   # all works.  It is not a high priority item to test but do not assume
   # this is a complete test of access functions.

   def comb(haystack, needle):
      for x in haystack:
         if x["name"] == needle:
             return True
      return False
   
   distros = server.get_distros()

   assert len(distros) == before_distros + 1
   assert comb(distros, "distro0")
   
   profiles = server.get_profiles()

   print "BEFORE: %s" % before_profiles
   print "CURRENT: %s" % len(profiles)
   for p in profiles:
      print "   PROFILES: %s" % p["name"]
   for p in api.profiles():
      print "   API     : %s" % p.name

   assert len(profiles) == before_profiles + 1
   assert comb(profiles, "profile0")

   systems = server.get_systems()
   # assert len(systems) == before_systems + 1
   assert comb(systems, "system0")

   repos = server.get_repos()
   # FIXME: disable temporarily
   # assert len(repos) == before_repos + 1
   assert comb(repos, "repo0")


   images = server.get_images()
   # assert len(images) == before_images + 1
   assert comb(images, "image0")

   # now test specific gets
   distro = server.get_distro("distro0")
   assert distro["name"] == "distro0"
   assert type(distro["kernel_options"] == type({}))

   profile = server.get_profile("profile0")
   assert profile["name"] == "profile0"
   assert type(profile["kernel_options"] == type({}))

   system = server.get_system("system0")
   assert system["name"] == "system0"
   assert type(system["kernel_options"] == type({}))

   repo = server.get_repo("repo0")
   assert repo["name"] == "repo0"

   image = server.get_image("image0")
   assert image["name"] == "image0"
  
   # now test the calls koan uses   
   # the difference is that koan's object types are flattened somewhat
   # and also that they are passed through utils.blender() so they represent
   # not the object but the evaluation of the object tree at that object.

   server.update() # should be unneeded
   distro  = server.get_distro_for_koan("distro0")
   assert distro["name"] == "distro0"
   assert type(distro["kernel_options"] == type(""))

   profile = server.get_profile_for_koan("profile0")
   assert profile["name"] == "profile0"
   assert type(profile["kernel_options"] == type(""))

   system = server.get_system_for_koan("system0")
   assert system["name"] == "system0"
   assert type(system["kernel_options"] == type(""))

   repo = server.get_repo_for_koan("repo0")
   assert repo["name"] == "repo0"

   image = server.get_image_for_koan("image0")
   assert image["name"] == "image0"

   # now test some of the additional webui calls
   # compatible profiles, etc

   assert server.ping() == True

   assert server.get_size("distros") == 1
   assert server.get_size("profiles") == 1
   assert server.get_size("systems") == 1
   assert server.get_size("repos") == 1
   assert server.get_size("images") == 1

   templates = server.get_kickstart_templates("???")
   assert "/var/lib/cobbler/kickstarts/sample.ks" in templates
   assert server.is_kickstart_in_use("/var/lib/cobbler/kickstarts/sample.ks","???") == True
   assert server.is_kickstart_in_use("/var/lib/cobbler/kickstarts/legacy.ks","???") == False
   generated = server.generate_kickstart("profile0")
   assert type(generated) == type("")
   assert generated.find("ERROR") == -1
   assert generated.find("url") != -1
   assert generated.find("network") != -1

   yumcfg = server.get_repo_config_for_profile("profile0")
   assert type(yumcfg) == type("")
   assert yumcfg.find("ERROR") == -1
   assert yumcfg.find("http://") != -1
 
   yumcfg = server.get_repo_config_for_system("system0")
   assert type(yumcfg) == type("")
   assert yumcfg.find("ERROR") == -1
   assert yumcfg.find("http://") != -1

   server.register_mac("CC:EE:FF:GG:AA:AA","profile0")
   systems = server.get_systems()
   found = False
   for s in systems:
       if s["name"] == "CC:EE:FF:GG:AA:AA":
           for iname in s["interfaces"]:
               if s["interfaces"]["iname"].get("mac_address") == "CC:EE:FF:GG:AA:AA":
                  found = True
                  break
       if found:
           break

   # FIXME: mac registration test code needs a correct settings file in order to 
   # be enabled.
   # assert found == True

   # FIXME:  the following tests don't work if pxe_just_once is disabled in settings so we need
   # to account for this by turning it on...
   # basically we need to rewrite the settings file 

   # system = server.get_system("system0")
   # assert system["netboot_enabled"] == "True"
   # rc = server.disable_netboot("system0") 
   # assert rc == True
   # ne = server.get_system("system0")["netboot_enabled"]
   # assert ne == False

   # FIXME: tests for new built-in configuration management feature
   # require that --template-files attributes be set.  These do not
   # retrieve the kickstarts but rather config files (see Wiki topics).
   # This is probably better tested at the URL level with urlgrabber, one layer
   # up, in a different set of tests..

   # FIXME: tests for rendered kickstart retrieval, same as above

   assert server.run_install_triggers("pre","profile","profile0","127.0.0.1")
   assert server.run_install_triggers("post","profile","profile0","127.0.0.1")
   assert server.run_install_triggers("pre","system","system0","127.0.0.1")
   assert server.run_install_triggers("post","system","system0","127.0.0.1")
   
   ver = server.version()
   assert (str(ver)[0] == "?" or str(ver).find(".") != -1)

   # do removals via the API since the read-only API can't do them
   # and the read-write tests are seperate

   _test_remove_objects()

   # this last bit mainly tests the tests, to ensure we've left nothing behind
   # not XMLRPC.  Tests polluting the user config is not desirable even though
   # we do save/restore it.

   # assert (len(api.distros()) == before_distros)
   # assert (len(api.profiles()) == before_profiles)
   # assert (len(api.systems()) == before_systems)
   # assert (len(api.images()) == before_images)
   # assert (len(api.repos()) == before_repos)
  
def test_xmlrpc_rw():

   # ideally we need tests for the various auth modes, not just one 
   # and the ownership module, though this will provide decent coverage.

   _test_setup_modules(authn="authn_testing",authz="authz_allowall")
   _test_bootstrap_restart()

   server = xmlrpclib.Server("http://127.0.0.1/cobbler_api") # remote 
   api = cobbler_api.BootAPI() # local instance, /DO/ ping cobblerd

   # note if authn_testing is not engaged this will not work
   # test getting token, will raise remote exception on fail 

   token = server.login("testing","testing")

   # create distro
   did = server.new_distro(token)
   server.modify_distro(did, "name", "distro1", token)
   server.modify_distro(did, "kernel", "/tmp/cobbler.fake", token) 
   server.modify_distro(did, "initrd", "/tmp/cobbler.fake", token) 
   server.modify_distro(did, "kopts", { "dog" : "fido", "cat" : "fluffy" }, token) # hash or string
   server.modify_distro(did, "ksmeta", "good=sg1 evil=gould", token) # hash or string
   server.modify_distro(did, "breed", "redhat", token)
   server.modify_distro(did, "os-version", "rhel5", token)
   server.modify_distro(did, "owners", "sam dave", token) # array or string
   server.modify_distro(did, "mgmt-classes", "blip", token) # list or string
   server.modify_distro(did, "template-files", "/tmp/cobbler.fake=/tmp/a /etc/fstab=/tmp/b",token) # hash or string
   server.modify_distro(did, "comment", "...", token)
   server.modify_distro(did, "redhat_management_key", "ALPHA", token)
   server.save_distro(did, token)

   # use the non-XMLRPC API to check that it's added seeing we tested XMLRPC RW APIs above
   # this makes extra sure it's been committed to disk.
   api.deserialize() 
   assert api.find_distro("distro1") != None

   pid = server.new_profile(token)
   server.modify_profile(pid, "name",   "profile1", token)
   server.modify_profile(pid, "distro", "distro1", token)
   server.modify_profile(pid, "enable-menu", True, token)
   server.modify_profile(pid, "kickstart", "/var/lib/cobbler/kickstarts/sample.ks", token)
   server.modify_profile(pid, "kopts", { "level" : "11" }, token)
   server.modify_profile(pid, "kopts-post", "noapic", token)
   server.modify_profile(pid, "virt-file-size", 20, token)
   server.modify_profile(pid, "virt-ram", 2048, token)
   server.modify_profile(pid, "repos", [], token)
   server.modify_profile(pid, "template-files", {}, token)
   server.modify_profile(pid, "virt-path", "VolGroup00", token)
   server.modify_profile(pid, "virt-bridge", "virbr1", token)
   server.modify_profile(pid, "virt-cpus", 2, token)
   server.modify_profile(pid, "owners", [ "sam", "dave" ], token)
   server.modify_profile(pid, "mgmt-classes", "one two three", token)
   server.modify_profile(pid, "comment", "...", token)
   server.modify_profile(pid, "name_servers", ["one","two"], token)
   server.modify_profile(pid, "name_servers_search", ["one","two"], token)
   server.modify_profile(pid, "redhat_management_key", "BETA", token)
   server.save_profile(pid, token)

   api.deserialize() 
   assert api.find_profile("profile1") != None

   sid = server.new_system(token)
   server.modify_system(sid, 'name', 'system1', token)
   server.modify_system(sid, 'hostname', 'system1', token)
   server.modify_system(sid, 'gateway', '127.0.0.1', token)
   server.modify_system(sid, 'profile', 'profile1', token)
   server.modify_system(sid, 'kopts', { "dog" : "fido" }, token)
   server.modify_system(sid, 'kopts-post', { "cat" : "fluffy" }, token)
   server.modify_system(sid, 'kickstart', '/var/lib/cobbler/kickstarts/sample.ks', token)
   server.modify_system(sid, 'netboot-enabled', True, token)
   server.modify_system(sid, 'virt-path', "/opt/images", token)
   server.modify_system(sid, 'virt-type', 'qemu', token)
   server.modify_system(sid, 'name_servers', 'one two three four', token)
   server.modify_system(sid, 'name_servers_search', 'one two three four', token)
   server.modify_system(sid, 'modify-interface', { 
       "macaddress-eth0"   : "AA:BB:CC:EE:EE:EE",
       "ipaddress-eth0"    : "192.168.10.50",
       "gateway-eth0"      : "192.168.10.1",
       "virtbridge-eth0"   : "virbr0",
       "dnsname-eth0"      : "foo.example.com",
       "static-eth0"       : False,
       "dhcptag-eth0"      : "section2",
       "staticroutes-eth0" : "a:b:c d:e:f"
   }, token)
   server.modify_system(sid, 'modify-interface', {
       "static-eth1"     : False,
       "staticroutes-eth1" : [ "g:h:i", "j:k:l" ]
   }, token)
   server.modify_system(sid, "mgmt-classes", [ "one", "two", "three"], token)
   server.modify_system(sid, "template-files", {}, token)
   server.modify_system(sid, "comment", "...", token)
   server.modify_system(sid, "power_address", "power.example.org", token)
   server.modify_system(sid, "power_type", "ipmitool", token)
   server.modify_system(sid, "power_user", "Admin", token)
   server.modify_system(sid, "power_pass", "magic", token)
   server.modify_system(sid, "power_id", "7", token)
   server.modify_system(sid, "redhat_management_key", "GAMMA", token)

   server.save_system(sid,token)
   
   api.deserialize() 
   assert api.find_system("system1") != None
   # FIXME: add some checks on object contents

   iid = server.new_image(token)
   server.modify_image(iid, "name", "image1", token)
   server.modify_image(iid, "image-type", "iso", token)
   server.modify_image(iid, "breed", "redhat", token)
   server.modify_image(iid, "os-version", "rhel5", token)
   server.modify_image(iid, "arch", "x86_64", token)
   server.modify_image(iid, "file", "nfs://server/path/to/x.iso", token)
   server.modify_image(iid, "owners", [ "alex", "michael" ], token)
   server.modify_image(iid, "virt-cpus", 1, token)
   server.modify_image(iid, "virt-file-size", 5, token)
   server.modify_image(iid, "virt-bridge", "virbr0", token)
   server.modify_image(iid, "virt-path", "VolGroup01", token)
   server.modify_image(iid, "virt-ram", 1024, token)
   server.modify_image(iid, "virt-type", "xenpv", token)
   server.modify_image(iid, "comment", "...", token)
   server.save_image(iid, token)

   api.deserialize() 
   assert api.find_image("image1") != None
   # FIXME: add some checks on object contents
   
   # FIXME: repo adds
   rid = server.new_repo(token)
   server.modify_repo(rid, "name", "repo1", token)
   server.modify_repo(rid, "arch", "x86_64", token)
   server.modify_repo(rid, "mirror", "http://example.org/foo/x86_64", token)
   server.modify_repo(rid, "keep-updated", True, token)
   server.modify_repo(rid, "priority", "50", token)
   server.modify_repo(rid, "rpm-list", [], token)
   server.modify_repo(rid, "createrepo-flags", "--verbose", token)
   server.modify_repo(rid, "yumopts", {}, token)
   server.modify_repo(rid, "owners", [ "slash", "axl" ], token)
   server.modify_repo(rid, "mirror-locally", True, token)
   server.modify_repo(rid, "environment", {}, token)
   server.modify_repo(rid, "comment", "...", token)
   server.save_repo(rid, token)
   
   api.deserialize() 
   assert api.find_repo("repo1") != None
   # FIXME: add some checks on object contents

   # test handle lookup

   did = server.get_distro_handle("distro1", token)
   assert did != None
   rid = server.get_repo_handle("repo1", token)
   assert rid != None
   iid = server.get_image_handle("image1", token)
   assert iid != None

   # test renames
   rc = server.rename_distro(did, "distro2", token)
   assert rc == True
   # object has changed due to parent rename, get a new handle
   pid = server.get_profile_handle("profile1", token)
   assert pid != None
   rc = server.rename_profile(pid, "profile2", token)
   assert rc == True
   # object has changed due to parent rename, get a new handle
   sid = server.get_system_handle("system1", token)
   assert sid != None
   rc = server.rename_system(sid, "system2", token)
   assert rc == True
   rc = server.rename_repo(rid, "repo2", token)
   assert rc == True
   rc = server.rename_image(iid, "image2", token)
   assert rc == True
   
   # FIXME: make the following code unneccessary
   api.clear()
   api.deserialize()

   assert api.find_distro("distro2") != None
   assert api.find_profile("profile2") != None
   assert api.find_repo("repo2") != None
   assert api.find_image("image2") != None
   assert api.find_system("system2") != None

   # BOOKMARK: currently here in terms of test testing.

   for d in api.distros():
      print "FOUND DISTRO: %s" % d.name


   assert api.find_distro("distro1") == None
   assert api.find_profile("profile1") == None
   assert api.find_repo("repo1") == None
   assert api.find_image("image1") == None
   assert api.find_system("system1") == None
   
   did = server.get_distro_handle("distro2", token)
   assert did != None
   pid = server.get_profile_handle("profile2", token)
   assert pid != None
   rid = server.get_repo_handle("repo2", token)
   assert rid != None
   sid = server.get_system_handle("system2", token)
   assert sid != None
   iid = server.get_image_handle("image2", token)
   assert iid != None

   # test copies
   server.copy_distro(did, "distro1", token)
   server.copy_profile(pid, "profile1", token)
   server.copy_repo(rid, "repo1", token)
   server.copy_image(iid, "image1", token)
   server.copy_system(sid, "system1", token)

   api.deserialize()
   assert api.find_distro("distro2") != None
   assert api.find_profile("profile2") != None
   assert api.find_repo("repo2") != None
   assert api.find_image("image2") != None
   assert api.find_system("system2") != None

   assert api.find_distro("distro1") != None
   assert api.find_profile("profile1") != None
   assert api.find_repo("repo1") != None
   assert api.find_image("image1") != None
   assert api.find_system("system1") != None
  
   assert server.last_modified_time() > 0
   print server.get_distros_since(2)
   assert len(server.get_distros_since(2)) > 0
   assert len(server.get_profiles_since(2)) > 0
   assert len(server.get_systems_since(2)) > 0
   assert len(server.get_images_since(2)) > 0
   assert len(server.get_repos_since(2)) > 0
   assert len(server.get_distros_since(2)) > 0

   now = time.time()
   the_future = time.time() + 99999
   assert len(server.get_distros_since(the_future)) == 0
 
   # it would be cleaner to do this from the distro down
   # and the server.update calls would then be unneeded.
   server.remove_system("system1", token)
   server.update()
   server.remove_profile("profile1", token)
   server.update()
   server.remove_distro("distro1", token)
   server.remove_repo("repo1", token)
   server.remove_image("image1", token)

   server.remove_system("system2", token)
   # again, calls are needed because we're deleting in the wrong
   # order.  A fix is probably warranted for this.
   server.update()
   server.remove_profile("profile2", token)
   server.update()
   server.remove_distro("distro2", token)
   server.remove_repo("repo2", token)
   server.remove_image("image2", token)

   # have to update the API as it has changed
   api.update()
   d1 = api.find_distro("distro1")
   assert d1 is None
   assert api.find_profile("profile1") is None
   assert api.find_repo("repo1") is None
   assert api.find_image("image1") is None
   assert api.find_system("system1") is None

   for x in api.distros():
      print "DISTRO REMAINING: %s" % x.name

   assert api.find_distro("distro2") is None
   assert api.find_profile("profile2") is None
   assert api.find_repo("repo2") is None
   assert api.find_image("image2") is None
   assert api.find_system("system2") is None

   # FIXME: should not need cleanup as we've done it above 
   _test_remove_objects()

