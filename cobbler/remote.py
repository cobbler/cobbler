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
import logging
import ConfigParser
import random
import base64

import api as cobbler_api
import utils
from cexceptions import *
import item_distro
import item_profile
import item_system
import item_repo

config_parser = ConfigParser.ConfigParser()
auth_conf = open("/etc/cobbler/auth.conf")
config_parser.readfp(auth_conf)
auth_conf.close()

user_database = config_parser.items("xmlrpc_service_users")


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
        self.logger = logger

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def ping(self):
        return True

    def __get_all(self,collection_name,page=-1,results_per_page=50):
        """
        Helper method to return all data to the WebUI or another caller
        without going through the process of loading all the data into
        objects and recalculating.  This does require that the cobbler
        data in the files is up-to-date in terms of serialized formats.
        """
        # FIXME: this method, and those that use it, need to allow page, and per_page
        data = self.api.deserialize_raw(collection_name)
        data.sort(self.__sorter)
        return self._fix_none(data)

    def get_settings(self,token=None):
        """
        Return the contents of /var/lib/cobbler/settings, which is a hash.
        """
        return self.__get_all("settings")
 
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
        return self.api.version()

    def get_distros(self,token=None):
        """
        Returns all cobbler distros as an array of hashes.
        """
        return self.__get_all("distro")

    def get_profiles(self,token=None):
        """
        Returns all cobbler profiles as an array of hashes.
        """
        return self.__get_all("profile")

    def get_systems(self,token=None):
        """
        Returns all cobbler systems as an array of hashes.
        """
        return self.__get_all("system")

    def get_repos(self,token=None):
        """
        Returns all cobbler repos as an array of hashes.
        """
        return self.__get_all("repo")

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
        return self.__get_specific(self.api.distros,name,flatten=flatten)

    def get_profile(self,name,flatten=False,token=None):
        """
        Returns the profile named "name" as a hash.
        """
        return self.__get_specific(self.api.profiles,name,flatten=flatten)

    def get_system(self,name,flatten=False,token=None):
        """
        Returns the system named "name" as a hash.
        """
        return self.__get_specific(self.api.systems,name,flatten=flatten)

    def get_repo(self,name,flatten=False,token=None):
        """
        Returns the repo named "name" as a hash.
        """
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
        self._refresh()
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
        self._refresh()
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
        return self.get_system_for_koan(self,name)

    def get_system_for_koan(self,name,token=None):
        """
        Same as get_system_as_rendered.
        """
        self._refresh()
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
        return self.get_repo_for_koan(self,name)

    def get_repo_for_koan(self,name,token=None):
        """
        Same as get_repo_as_rendered.
        """
        self._refresh()
        obj = self.api.repos().find(name=name)
        if obj is not None:
            return self._fix_none(utils.blender(True, obj))
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

    def __make_token(self):
        """
        Returns a new random token.
        """
        b64 = self.__get_random(25)
        self.token_cache[b64] = time.time()
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
            tokentime = self.token_cache[token]
            if (timenow > tokentime + TOKEN_TIMEOUT):
                self.logger.debug("expiring token: %s" % token)
                del self.token_cache[token]

    def __validate_user(self,user,password):
        """
        Returns whether this user/pass combo should be given
        access to the cobbler read-write API.

        FIXME: currently looks for users in /etc/cobbler/auth.conf
        Would be very nice to allow for PAM and/or just Kerberos.
        """
        for x in user_database:
            (db_user,db_password) = x
            db_user     = db_user.strip()
            db_password = db_password.strip()
            if db_user == user and db_password == password and db_password.lower() != "disabled":
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
        self.__invalidate_expired_tokens()
        self.__invalidate_expired_objects()
        if self.token_cache.has_key(token):
            self.token_cache[token] = time.time() # update to prevent timeout
            return True
        else:
            self.logger.debug("invalid token: %s" % token)
            raise CX(_("invalid token: %s" % token))

    def login(self,user,password):
        """
        Takes a username and password, validates it, and if successful
        returns a random login token which must be used on subsequent
        method calls.  The token will time out after a set interval if not
        used.  Re-logging in permitted.
        """
        if self.__validate_user(user,password):
            token = self.__make_token()
            self.logger.info("login succeeded: %s" % user)
            return token
        else:
            self.logger.info("login failed: %s" % user)
            raise CX(_("login failed: %s") % user)

    def logout(self,token):
        """
        Retires a token ahead of the timeout.
        """
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
        self.__validate_token(token)
        return self.__store_object(item_distro.Distro(self.api._config))

    def new_profile(self,token):    
        """
        Creates a new (unconfigured) profile object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.__validate_token(token)
        return self.__store_object(item_profile.Profile(self.api._config))

    def new_subprofile(self,token):
        """
        Creates a new (unconfigured) subprofile object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.__validate_token(token)
        return self.__store_object(item_profile.Profile(self.api._config, is_subobject=True))

    def new_subprofile(self,token):
        """
        A subprofile is a profile that inherits directly from another profile,
        not a distro.  In addition to the normal profile setup, setting
        the parent variable to the name of an existing profile is also
        mandatory.   Systems can be assigned to subprofiles just like they
        were regular profiles.  The same XMLRPC API methods work on them as profiles
        also.
        """
        self.__validate_token(token)
        return self.__store_object(item_profile.Profile(self.api._config,is_subobject=True))

    def new_system(self,token):
        """
        Creates a new (unconfigured) system object.  See the documentation
        for new_distro as it works exactly the same.
        """
        self.__validate_token(token)
        return self.__store_object(item_system.System(self.api._config))
        
    def new_repo(self,token):
        """
        Creates a new (unconfigured) repo object.  See the documentation 
        for new_distro as it works exactly the same.
        """
        self.__validate_token(token)
        return self.__store_object(item_repo.Repo(self.api._config))
       
    def get_distro_handle(self,name,token):
        """
        Given the name of an distro (or other search parameters), return an
        object id that can be passed in to modify_distro() or save_distro()
        commands.  Raises an exception if no object can be matched.
        """
        self.__validate_token(token)
        self._refresh()
        found = self.api.distros().find(name)
        return self.__store_object(found)   

    def get_profile_handle(self,name,token):
        """
        Given the name of a profile  (or other search parameters), return an
        object id that can be passed in to modify_profile() or save_profile()
        commands.  Raises an exception if no object can be matched.
        """
        self.__validate_token(token)
        self._refresh()
        found = self.api.profiles().find(name)
        return self.__store_object(found)   

    def get_system_handle(self,name,token):
        """
        Given the name of an system (or other search parameters), return an
        object id that can be passed in to modify_system() or save_system()
        commands. Raises an exception if no object can be matched.
        """
        self.__validate_token(token)
        self._refresh()
        found = self.api.systems().find(name)
        return self.__store_object(found)   

    def get_repo_handle(self,name,token):
        """
        Given the name of an repo (or other search parameters), return an
        object id that can be passed in to modify_repo() or save_pro()
        commands.  Raises an exception if no object can be matched.
        """
        self.__validate_token(token)
        self._refresh()
        found = self.api.repos().find(name)
        return self.__store_object(found)   

    def save_distro(self,object_id,token):
        """
        Saves a newly created or modified distro object to disk.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.api.distros().add(obj,with_copy=True)

    def save_profile(self,object_id,token):
        """
        Saves a newly created or modified profile object to disk.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.api.profiles().add(obj,with_copy=True)

    def save_system(self,object_id,token):
        """
        Saves a newly created or modified system object to disk.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.api.systems().add(obj,with_copy=True)

    def save_repo(self,object_id,token=None):
        """
        Saves a newly created or modified repo object to disk.
        """
        self.__validate_token(token)
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
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_profile(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing profile object handle.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_system(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing system object handle.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def modify_repo(self,object_id,attribute,arg,token):
        """
        Allows modification of certain attributes on newly created or
        existing repo object handle.
        """
        self.__validate_token(token)
        obj = self.__get_object(object_id)
        return self.__call_method(obj, attribute, arg)

    def distro_remove(self,name,token):
        """
        Deletes a distro from a collection.  Note that this just requires the name
        of the distro, not a handle.
        """
        self.__validate_token(token)
        rc = self.api._config.distros().remove(name)
        return rc

    def profile_remove(self,name,token):
        """
        Deletes a profile from a collection.  Note that this just requires the name
        of the profile, not a handle.
        """
        self.__validate_token(token)
        rc = self.api._config.profiles().remove(name)
        return rc

    def system_remove(self,name,token):
        """
        Deletes a system from a collection.  Note that this just requires the name
        of the system, not a handle.
        """
        self.__validate_token(token)
        rc = self.api._config.systems().remove(name)
        return rc

    def repo_remove(self,name,token):
        """
        Deletes a repo from a collection.  Note that this just requires the name
        of the repo, not a handle.
        """
        self.__validate_token(token)
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
        self.__validate_token(token)
        return self.api.sync() 

    def reposync(self,repos=[],token=None):
        """
        Updates one or more mirrored yum repositories.
        reposync is very slow and probably should not be used
        through the XMLRPC API, setting up reposync on nightly cron is better.
        """
        self.__validate_token(token)
        return self.api.reposync(repos)

    def import_tree(self,mirror_url,mirror_name,network_root=None,token=None):
        """
        I'm exposing this in the XMLRPC API for consistancy but as this
        can be a very long running operation usage is /not/ recommended.
        It would be better to use the CLI.  See documentation in api.py.
        This command may be removed from the API in a future release.
        """
        self.__validate_token(token)
        return self.api.import_tree(mirror_url,mirror_name,network_root)

    def get_kickstart_templates(self,token):
        """
        Returns all of the kickstarts that are in use by the system.
        """
        self.__validate_token(token)
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

        self.__validate_token(token)
 
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



# *********************************************************************************
# *********************************************************************************

class CobblerReadWriteXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """
    This is just a wrapper used for launching the Read/Write XMLRPC Server.
    """

    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************

if __name__ == "__main__":

    # note: this demo requires that
    #  (A) /etc/cobbler/auth.conf has a "testuser/llamas2007" account
    #  (B) xmlrpc_rw_enabled is turned on /var/lib/cobbler/settings
    #  (C) cobblerd is running (and restarted if changing any of the above)
    #  (D) apache is configured as a reverse proxy (see cobbler.conf in /etc/httpd/conf.d)
    # this demo does not use SSL yet -- it /should/ and /can/.

    my_uri = "http://127.0.0.1/cobbler_api_rw"
    remote =  xmlrpclib.Server(my_uri)

    testuser = "admin"
    testpass = "mooses9"

    token = remote.login(testuser,testpass)
    print token

    # just to make things "work"
    os.system("touch /tmp/vmlinuz")
    os.system("touch /tmp/initrd.img")
    os.system("touch /tmp/fake.ks")

    # now add a distro
    distro_id = remote.new_distro(token)
    remote.modify_distro(distro_id, 'name',   'example-distro',token)
    remote.modify_distro(distro_id, 'kernel', '/tmp/vmlinuz',token)
    remote.modify_distro(distro_id, 'initrd', '/tmp/initrd.img',token)
    remote.save_distro(distro_id,token)

    # now add a repository (that's not really mirroring anything useful)
    repo_id = remote.new_repo(token)
    remote.modify_repo(repo_id, 'name',   'example-repo', token)
    remote.modify_repo(repo_id, 'mirror', 'rsync://mirror.example.org/foo', token)
    remote.save_repo(repo_id, token)

    # now add a profile
    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, 'name',      'example-profile', token)
    remote.modify_profile(profile_id, 'distro',    'example-distro', token)
    remote.modify_profile(profile_id, 'kickstart', '/tmp/fake.ks', token)
    remote.modify_profile(profile_id, 'repos',     ['example-repo'], token)
    remote.save_profile(profile_id, token)

    # now add a system
    system_id = remote.new_system(token)
    remote.modify_system(system_id,   'name',      'example-system', token)
    remote.modify_system(system_id,   'profile',   'example-profile', token)
    remote.save_system(system_id, token)

    print remote.get_distros()
    print remote.get_profiles()
    print remote.get_systems()
    print remote.get_repos()

    print remote.get_system("AA:BB:AA:BB:AA:BB",True) # flattened

    # now simulate hitting a "sync" button in a WebUI
    print remote.sync(token)

    # the following code just tests a failed connection:
    #remote = CobblerReadWriteXMLRPCInterface(api,logger)
    #try:
    #    token = remote.login("exampleuser2","examplepass")
    #except:
    #    token = "fake_token"
    #print token
    #rc = remote.test(token)
    #print "test result: %s" % rc
    # print "cache: %s" % remote.token_cache
