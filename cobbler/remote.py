"""
Code for Cobbler's XMLRPC API

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
 
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

import sys, socket, time, os, errno, re, random, stat, string
import base64
import SimpleXMLRPCServer
from SocketServer import ThreadingMixIn
import xmlrpclib
import base64
import fcntl
import traceback
import glob
from threading import Thread

import api as cobbler_api
import utils
from cexceptions import *
import item_distro
import item_profile
import item_system
import item_repo
import item_image
import item_mgmtclass
import item_package
import item_file
import clogger
import pxegen
import utils
#from utils import * # BAD!
from utils import _
import configgen

EVENT_TIMEOUT = 7*24*60*60 # 1 week
CACHE_TIMEOUT = 10*60 # 10 minutes

# task codes
EVENT_RUNNING   = "running"
EVENT_COMPLETE  = "complete"
EVENT_FAILED    = "failed"
# normal events
EVENT_INFO      = "notification"

# for backwards compatibility with 1.6 and prev XMLRPC
# do not remove!
REMAP_COMPAT = {
   "ksmeta"          : "ks_meta",
   "kopts"           : "kernel_options",
   "kopts_post"      : "kernel_options_post",
   "netboot-enabled" : "netboot_enabled"
}

class CobblerThread(Thread):
    def __init__(self,event_id,remote,logatron,options):
        Thread.__init__(self)
        self.event_id        = event_id
        self.remote          = remote
        self.logger          = logatron
        if options is None:
            options = {}
        self.options         = options

    def on_done(self):
        pass

    def run(self):
        time.sleep(1)
        try:
            rc = self._run(self)
            if not rc:
                self.remote._set_task_state(self,self.event_id,EVENT_FAILED)
            else:
                self.remote._set_task_state(self,self.event_id,EVENT_COMPLETE)
            self.on_done()
            return rc
        except:
            utils.log_exc(self.logger)
            self.remote._set_task_state(self,self.event_id,EVENT_FAILED)
            return False  
 
# *********************************************************************
# *********************************************************************

class CobblerXMLRPCInterface:
    """
    This is the interface used for all XMLRPC methods, for instance,
    as used by koan or CobblerWeb.
   
    Most read-write operations require a token returned from "login". 
    Read operations do not.
    """

    def __init__(self,api):
        """
        Constructor.  Requires a Cobbler API handle.
        """
        self.api = api
        self.logger = self.api.logger
        self.token_cache = {}
        self.object_cache = {}
        self.timestamp = self.api.last_modified_time()
        self.events = {}
        self.shared_secret = utils.get_shared_secret()
        random.seed(time.time())
        self.translator = utils.Translator(keep=string.printable)
        self.pxegen = pxegen.PXEGen(api._config,self.logger)

    def check(self, token):
        """
        Returns a list of all the messages/warnings that are things
        that admin may want to correct about the configuration of 
        the cobbler server.  This has nothing to do with "check_access"
        which is an auth/authz function in the XMLRPC API.
        """
        self.check_access(token, "check")
        return self.api.check(logger=self.logger)

    def background_buildiso(self, options, token):
        """
        Generates an ISO in /var/www/cobbler/pub that can be used to install
        profiles without using PXE.
        """
        # FIXME: better use webdir from the settings?
        webdir = "/var/www/cobbler/"
        if os.path.exists("/srv/www"):
            webdir = "/srv/www/cobbler/"

        def runner(self):
            return self.remote.api.build_iso(
                self.options.get("iso",webdir+"/pub/generated.iso"),
                self.options.get("profiles",None),
                self.options.get("systems",None),
                self.options.get("buildisodir",None),
                self.options.get("distro",None),
                self.options.get("standalone",False),
                self.options.get("source",None),
                self.options.get("exclude_dns",False),
                self.options.get("mkisofs_opts",None),
                self.logger
            )
        def on_done(self):
            if self.options.get("iso","") == webdir+"/pub/generated.iso":
                msg = "ISO now available for <A HREF=\"/cobbler/pub/generated.iso\">download</A>"
                self.remote._new_event(msg)
        return self.__start_task(runner, token, "buildiso", "Build Iso", options, on_done)

    def background_aclsetup(self, options, token):
        def runner(self):
            return self.remote.api.acl_config(
                self.options.get("adduser",None),
                self.options.get("addgroup",None),
                self.options.get("removeuser",None),
                self.options.get("removegroup",None),
                self.logger
            )
        return self.__start_task(runner, token, "aclsetup", "(CLI) ACL Configuration", options)

    def background_dlcontent(self, options, token):
        """
        Download bootloaders and other support files.
        """
        def runner(self):
            return self.remote.api.dlcontent(self.options.get("force",False), self.logger)
        return self.__start_task(runner, token, "get_loaders", "Download Bootloader Content", options)

    def background_sync(self, options, token):
        def runner(self):
            return self.remote.api.sync(self.options.get("verbose",False),logger=self.logger)
        return self.__start_task(runner, token, "sync", "Sync", options) 

    def background_hardlink(self, options, token):
        def runner(self):
            return self.remote.api.hardlink(logger=self.logger)
        return self.__start_task(runner, token, "hardlink", "Hardlink", options)

    def background_validateks(self, options, token):
        def runner(self):
            return self.remote.api.validateks(logger=self.logger)
        return self.__start_task(runner, token, "validateks", "Kickstart Validation", options)

    def background_replicate(self, options, token):
        def runner(self):
            # FIXME: defaults from settings here should come from views, fix in views.py
            return self.remote.api.replicate(
                self.options.get("master", None),
                self.options.get("distro_patterns", ""),
                self.options.get("profile_patterns", ""),
                self.options.get("system_patterns", ""),
                self.options.get("repo_patterns", ""),
                self.options.get("image_patterns", ""),
                self.options.get("mgmtclass_patterns", ""),
                self.options.get("package_patterns", ""),
                self.options.get("file_patterns", ""),
                self.options.get("prune", False),
                self.options.get("omit_data", False),
                self.options.get("sync_all", False),
                self.logger
            )
        return self.__start_task(runner, token, "replicate", "Replicate", options)

    def background_import(self, options, token):
        def runner(self):
            return self.remote.api.import_tree(
                self.options.get("path", None),
                self.options.get("name", None),
                self.options.get("available_as", None),
                self.options.get("kickstart_file", None),
                self.options.get("rsync_flags",None),
                self.options.get("arch",None),
                self.options.get("breed", None),
                self.options.get("os_version", None),
                self.logger
            ) 
        return self.__start_task(runner, token, "import", "Media import", options)
                     
    def background_reposync(self, options, token):
        def runner(self):
            # NOTE: WebUI passes in repos here, CLI passes only:
            repos = options.get("repos", [])
            only = options.get("only", None)
            if only is not None:
                repos = [ only ] 
            nofail = options.get("nofail", len(repos) > 0)

            if len(repos) > 0:
                for name in repos:
                    self.remote.api.reposync(tries=self.options.get("tries",
                        3), name=name, nofail=nofail, logger=self.logger)
            else:
                self.remote.api.reposync(tries=self.options.get("tries",3),
                        name=None, nofail=nofail, logger=self.logger)
            return True
        return self.__start_task(runner, token, "reposync", "Reposync", options)

    def background_power_system(self, options, token):
        def runner(self):
            for x in self.options.get("systems",[]):
                try:
                    object_id = self.remote.get_system_handle(x,token)
                    self.remote.power_system(object_id,self.options.get("power",""),token,logger=self.logger)
                except:
                    self.logger.warning("failed to execute power task on %s" % str(x))
            return True
        self.check_access(token, "power")
        return self.__start_task(runner, token, "power", "Power management (%s)" % options.get("power",""), options)

    def background_signature_update(self, options, token):
        def runner(self):
            return self.remote.api.signature_update(self.logger)
        self.check_access(token, "sigupdate")
        return self.__start_task(runner, token, "sigupdate", "Updating Signatures", options)

    def get_events(self, for_user=""):
        """
        Returns a hash(key=event id) = [ statetime, name, state, [read_by_who] ]
        If for_user is set to a string, it will only return events the user
        has not seen yet.  If left unset, it will return /all/ events.
        """

        # return only the events the user has not seen
        self.events_filtered = {}
        for (k,x) in self.events.iteritems():
           if for_user in x[3]:
              pass
           else:
              self.events_filtered[k] = x

        # mark as read so user will not get events again
        if for_user is not None and for_user != "":
           for (k,x) in self.events.iteritems():
               if for_user in x[3]:
                  pass
               else:
                  self.events[k][3].append(for_user)

        return self.events_filtered

    def get_event_log(self,event_id):
        """
        Returns the contents of a task log.
        Events that are not task-based do not have logs.
        """
        event_id = str(event_id).replace("..","").replace("/","")
        path = "/var/log/cobbler/tasks/%s.log" % event_id
        self._log("getting log for %s" % event_id)
        if os.path.exists(path):
           fh = open(path, "r")
           data = str(fh.read())
           data = self.translator(data)
           fh.close()
           return data
        else:
           return "?"

    def __generate_event_id(self,optype):
        t = time.time()
        (year, month, day, hour, minute, second, weekday, julian, dst) = time.localtime()
        return "%04d-%02d-%02d_%02d%02d%02d_%s" % (year,month,day,hour,minute,second,optype)

    def _new_event(self, name):
        event_id = self.__generate_event_id("event")
        event_id = str(event_id)
        self.events[event_id] = [ float(time.time()), str(name), EVENT_INFO, [] ]

    def __start_task(self, thr_obj_fn, token, role_name, name, args, on_done=None):
        """
        Starts a new background task.
            token      -- token from login() call, all tasks require tokens
            role_name  -- used to check token against authn/authz layers
            thr_obj_fn -- function handle to run in a background thread
            name       -- display name to show in logs/events
            args       -- usually this is a single hash, containing options
            on_done    -- an optional second function handle to run after success (and only success)
        Returns a task id.
        """
        self.check_access(token, role_name)
        event_id = self.__generate_event_id(role_name) # use short form for logfile suffix
        event_id = str(event_id)
        self.events[event_id] = [ float(time.time()), str(name), EVENT_RUNNING, [] ]
        
        self._log("start_task(%s); event_id(%s)"%(name,event_id))
        logatron = clogger.Logger("/var/log/cobbler/tasks/%s.log" % event_id)

        thr_obj = CobblerThread(event_id,self,logatron,args)
        on_done_type = type(thr_obj.on_done)

        thr_obj._run = thr_obj_fn
        if on_done is not None:
           thr_obj.on_done = on_done_type(on_done, thr_obj, CobblerThread)
        thr_obj.start()
        return event_id

    def _set_task_state(self,thread_obj,event_id,new_state):
        event_id = str(event_id)
        if self.events.has_key(event_id):
            self.events[event_id][2] = new_state
            self.events[event_id][3] = [] # clear the list of who has read it
        if thread_obj is not None:
            if new_state == EVENT_COMPLETE: 
                thread_obj.logger.info("### TASK COMPLETE ###")
            if new_state == EVENT_FAILED: 
                thread_obj.logger.error("### TASK FAILED ###")

    def get_task_status(self, event_id):
        event_id = str(event_id)
        if self.events.has_key(event_id):
            return self.events[event_id]
        else:
            raise CX("no event with that id")

    def __sorter(self,a,b):
        """
        Helper function to sort two datastructure representations of
        cobbler objects by name.
        """
        return cmp(a["name"],b["name"])

    def last_modified_time(self, token=None):
        """
        Return the time of the last modification to any object.
        Used to verify from a calling application that no cobbler
        objects have changed since last check.
        """
        return self.api.last_modified_time()

    def update(self, token=None):
        """
        Deprecated method.  Now does nothing.
        """
        return True

    def ping(self):
        """
        Deprecated method.  Now does nothing.
        """
        return True

    def get_user_from_token(self,token):
        """
        Given a token returned from login, return the username
        that logged in with it.
        """
        if not self.token_cache.has_key(token):
            raise CX("invalid token: %s" % token)
        else:
            return self.token_cache[token][1]

    def _log(self,msg,user=None,token=None,name=None,object_id=None,attribute=None,debug=False,error=False):
        """
        Helper function to write data to the log file from the XMLRPC remote implementation.
        Takes various optional parameters that should be supplied when known.
        """

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
        msg = "REMOTE %s; user(%s)" % (msg, m_user)
 
        if name is not None:
            msg = "%s; name(%s)" % (msg, name)

        if object_id is not None:
            msg = "%s; object_id(%s)" % (msg, object_id)

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

    def __sort(self,data,sort_field=None):
        """
        Helper function used by the various find/search functions to return
        object representations in order.
        """
        sort_fields=["name"]
        sort_rev=False
        if sort_field is not None:
            if sort_field.startswith("!"):
                sort_field=sort_field[1:]
                sort_rev=True
            sort_fields.insert(0,sort_field)
        sortdata=[(x.sort_key(sort_fields),x) for x in data]
        if sort_rev:
            sortdata.sort(lambda a,b:cmp(b,a))
        else:
            sortdata.sort()
        return [x for (key, x) in sortdata]
            
    def __paginate(self,data,page=None,items_per_page=None,token=None):
        """
        Helper function to support returning parts of a selection, for
        example, for use in a web app where only a part of the results
        are to be presented on each screen.
        """
        default_page = 1
        default_items_per_page = 25

        try:
            page = int(page)
            if page < 1:
                page = default_page
        except:
            page = default_page
        try:
            items_per_page = int(items_per_page)
            if items_per_page <= 0:
                items_per_page = default_items_per_page
        except:
            items_per_page = default_items_per_page

        num_items = len(data)
        num_pages = ((num_items-1)/items_per_page)+1
        if num_pages==0:
            num_pages=1
        if page>num_pages:
            page=num_pages
        start_item = (items_per_page * (page-1))
        end_item   = start_item + items_per_page
        if start_item > num_items:
            start_item = num_items - 1
        if end_item > num_items:
            end_item = num_items
        data = data[start_item:end_item]

        if page > 1:
            prev_page = page - 1
        else:
            prev_page = None
        if page < num_pages:
            next_page = page + 1
        else:
            next_page = None
                        
        return (data,{
                'page'        : page,
                'prev_page'   : prev_page,
                'next_page'   : next_page,
                'pages'       : range(1,num_pages+1),
                'num_pages'   : num_pages,
                'num_items'   : num_items,
                'start_item'  : start_item,
                'end_item'    : end_item,
                'items_per_page' : items_per_page,
                'items_per_page_list' : [10,20,50,100,200,500],
        })

    def __get_object(self, object_id):
        """
        Helper function. Given an object id, return the actual object.
        """
        if object_id.startswith("___NEW___"):
           return self.object_cache[object_id][1]
        (otype, oname) = object_id.split("::",1)
        return self.api.get_item(otype,oname)

    def get_item(self, what, name, flatten=False):
        """
        Returns a hash describing a given object.
        what -- "distro", "profile", "system", "image", "repo", etc
        name -- the object name to retrieve
        flatten -- reduce hashes to string representations (True/False)
        """
        self._log("get_item(%s,%s)"%(what,name))
        item=self.api.get_item(what,name)
        if item is not None:
            item=item.to_datastruct()
        if flatten:
            item = utils.flatten(item)
        return self.xmlrpc_hacks(item)

    def get_distro(self,name,flatten=False,token=None,**rest):
        return self.get_item("distro",name,flatten=flatten)
    def get_profile(self,name,flatten=False,token=None,**rest):
        return self.get_item("profile",name,flatten=flatten)
    def get_system(self,name,flatten=False,token=None,**rest):
        return self.get_item("system",name,flatten=flatten)
    def get_repo(self,name,flatten=False,token=None,**rest):
        return self.get_item("repo",name,flatten=flatten)
    def get_image(self,name,flatten=False,token=None,**rest):
        return self.get_item("image",name,flatten=flatten)
    def get_mgmtclass(self,name,flatten=False,token=None,**rest):
        return self.get_mgmtclass("mgmtclass",name,flatten=flatten)
    def get_package(self,name,flatten=False,token=None,**rest):
        return self.get_package("package",name,flatten=flatten)
    def get_file(self,name,flatten=False,token=None,**rest):
        return self.get_file("file",name,flatten=flatten)

    def get_items(self, what):
        """
        Returns a list of hashes.  
        what is the name of a cobbler object type, as described for get_item.
        Individual list elements are the same for get_item.
        """
        # FIXME: is the xmlrpc_hacks method still required ?
        item = [x.to_datastruct() for x in self.api.get_items(what)]
        return self.xmlrpc_hacks(item)

    def get_item_names(self, what):
        """
        Returns a list of object names (keys) for the given object type.
        This is just like get_items, but transmits less data.
        """
        return [x.name for x in self.api.get_items(what)]

    def get_distros(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("distro")
    def get_profiles(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("profile")
    def get_systems(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("system")
    def get_repos(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("repo")
    def get_images(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("image")
    def get_mgmtclasses(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("mgmtclass")
    def get_packages(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("package")
    def get_files(self,page=None,results_per_page=None,token=None,**rest):
        return self.get_items("file")

    def find_items(self, what, criteria=None,sort_field=None,expand=True):
        """
        Returns a list of hashes.
        Works like get_items but also accepts criteria as a hash to search on.
        Example:  { "name" : "*.example.org" }
        Wildcards work as described by 'pydoc fnmatch'.
        """
        self._log("find_items(%s); criteria(%s); sort(%s)" % (what,criteria,sort_field))
        items = self.api.find_items(what,criteria=criteria)
        items = self.__sort(items,sort_field)
        if not expand:     
            items = [x.name for x in items]
        else:
            items = [x.to_datastruct() for x in items]
        return self.xmlrpc_hacks(items)

    def find_distro(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("distro",criteria,expand=expand)
    def find_profile(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("profile",criteria,expand=expand)
    def find_system(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("system",criteria,expand=expand)
    def find_repo(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("repo",criteria,expand=expand)
    def find_image(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("image",criteria,expand=expand)
    def find_mgmtclass(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("mgmtclass",criteria,expand=expand)
    def find_package(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("package",criteria,expand=expand)
    def find_file(self,criteria={},expand=False,token=None,**rest):
        return self.find_items("file",criteria,expand=expand)

    def find_items_paged(self, what, criteria=None, sort_field=None, page=None, items_per_page=None, token=None):
        """
        Returns a list of hashes as with find_items but additionally supports
        returning just a portion of the total list, for instance in supporting
        a web app that wants to show a limited amount of items per page.
        """
        # FIXME: make token required for all logging calls
        self._log("find_items_paged(%s); criteria(%s); sort(%s)" % (what,criteria,sort_field), token=token)
        items = self.api.find_items(what,criteria=criteria)
        items = self.__sort(items,sort_field)
        (items,pageinfo) = self.__paginate(items,page,items_per_page)
        items = [x.to_datastruct() for x in items]
        return self.xmlrpc_hacks({
            'items'    : items,
            'pageinfo' : pageinfo
        })

    def has_item(self,what,name,token=None):
        """
        Returns True if a given collection has an item with a given name,
        otherwise returns False.
        """
        self._log("has_item(%s)"%what,token=token,name=name)
        found = self.api.get_item(what,name)
        if found is None:
            return False
        else:
            return True

    def get_item_handle(self,what,name,token=None):
        """
        Given the name of an object (or other search parameters), return a
        reference (object id) that can be used with modify_* functions or save_* functions
        to manipulate that object.
        """
        found = self.api.get_item(what,name)
        if found is None:
            raise CX("internal error, unknown %s name %s" % (what,name))
        return "%s::%s" % (what,found.name)

    def get_distro_handle(self,name,token):
        return self.get_item_handle("distro",name,token)
    def get_profile_handle(self,name,token):
        return self.get_item_handle("profile",name,token)
    def get_system_handle(self,name,token):
        return self.get_item_handle("system",name,token)
    def get_repo_handle(self,name,token):
        return self.get_item_handle("repo",name,token)
    def get_image_handle(self,name,token):
        return self.get_item_handle("image",name,token)
    def get_mgmtclass_handle(self,name,token):
        return self.get_item_handle("mgmtclass",name,token)
    def get_package_handle(self,name,token):
        return self.get_item_handle("package",name,token)
    def get_file_handle(self,name,token):
        return self.get_item_handle("file",name,token)
        
    def remove_item(self,what,name,token,recursive=True):
        """
        Deletes an item from a collection.  
        Note that this requires the name of the distro, not an item handle.
        """
        self._log("remove_item (%s, recursive=%s)" % (what,recursive),name=name,token=token)
        self.check_access(token, "remove_item", name)
        return self.api.remove_item(what,name,delete=True,with_triggers=True,recursive=recursive)
    
    def remove_distro(self,name,token,recursive=1):
        return self.remove_item("distro",name,token,recursive)
    def remove_profile(self,name,token,recursive=1):
        return self.remove_item("profile",name,token,recursive)
    def remove_system(self,name,token,recursive=1):
        return self.remove_item("system",name,token,recursive)
    def remove_repo(self,name,token,recursive=1):
        return self.remove_item("repo",name,token,recursive)
    def remove_image(self,name,token,recursive=1):
        return self.remove_item("image",name,token,recursive)
    def remove_mgmtclass(self,name,token,recursive=1):
        return self.remove_item("mgmtclass",name,token,recursive)
    def remove_package(self,name,token,recursive=1):
        return self.remove_item("package",name,token,recursive)
    def remove_file(self,name,token,recursive=1):
        return self.remove_item("file",name,token,recursive)

    def copy_item(self,what,object_id,newname,token=None):
        """
        Creates a new object that matches an existing object, as specified by an id.
        """
        self._log("copy_item(%s)" % what,object_id=object_id,token=token)
        self.check_access(token,"copy_%s" % what)
        obj = self.__get_object(object_id)
        return self.api.copy_item(what,obj,newname)
    
    def copy_distro(self,object_id,newname,token=None):
        return self.copy_item("distro",object_id,newname,token)
    def copy_profile(self,object_id,newname,token=None):
        return self.copy_item("profile",object_id,newname,token)
    def copy_system(self,object_id,newname,token=None):
        return self.copy_item("system",object_id,newname,token)
    def copy_repo(self,object_id,newname,token=None):
        return self.copy_item("repo",object_id,newname,token)
    def copy_image(self,object_id,newname,token=None):
        return self.copy_item("image",object_id,newname,token)
    def copy_mgmtclass(self,object_id,newname,token=None):
        return self.copy_item("mgmtclass",object_id,newname,token)
    def copy_package(self,object_id,newname,token=None):
        return self.copy_item("package",object_id,newname,token)
    def copy_file(self,object_id,newname,token=None):
        return self.copy_item("file",object_id,newname,token)
    
    def rename_item(self,what,object_id,newname,token=None):
        """
        Renames an object specified by object_id to a new name.
        """
        self._log("rename_item(%s)" % what,object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        return self.api.rename_item(what,obj,newname)
    
    def rename_distro(self,object_id,newname,token=None):
        return self.rename_item("distro",object_id,newname,token)
    def rename_profile(self,object_id,newname,token=None):
        return self.rename_item("profile",object_id,newname,token)
    def rename_system(self,object_id,newname,token=None):
        return self.rename_item("system",object_id,newname,token)
    def rename_repo(self,object_id,newname,token=None):
        return self.rename_item("repo",object_id,newname,token)
    def rename_image(self,object_id,newname,token=None):
        return self.rename_item("image",object_id,newname,token)
    def rename_mgmtclass(self,object_id,newname,token=None):
        return self.rename_item("mgmtclass",object_id,newname,token)
    def rename_package(self,object_id,newname,token=None):
        return self.rename_item("package",object_id,newname,token)
    def rename_file(self,object_id,newname,token=None):
        return self.rename_item("file",object_id,newname,token)
    
    def new_item(self,what,token,is_subobject=False):
        """
        Creates a new (unconfigured) object, returning an object
        handle that can be used with modify_* methods and then finally
        save_* methods.  The handle only exists in memory until saved.
        "what" specifies the type of object: 
            distro, profile, system, repo, or image
        """      
        self._log("new_item(%s)"%what,token=token)
        self.check_access(token,"new_%s"%what)
        if what == "distro":
            d = item_distro.Distro(self.api._config,is_subobject=is_subobject)
        elif what == "profile":
            d = item_profile.Profile(self.api._config,is_subobject=is_subobject)
        elif what == "system":
            d = item_system.System(self.api._config,is_subobject=is_subobject)
        elif what == "repo":
            d = item_repo.Repo(self.api._config,is_subobject=is_subobject)
        elif what == "image":
            d = item_image.Image(self.api._config,is_subobject=is_subobject)
        elif what == "mgmtclass":
            d = item_mgmtclass.Mgmtclass(self.api._config,is_subobject=is_subobject)
        elif what == "package":
            d = item_package.Package(self.api._config,is_subobject=is_subobject)
        elif what == "file":
            d = item_file.File(self.api._config,is_subobject=is_subobject)
        else:
            raise CX("internal error, collection name is %s" % what)
        key = "___NEW___%s::%s" % (what,self.__get_random(25))
        self.object_cache[key] = (time.time(), d) 
        return key

    def new_distro(self,token):
        return self.new_item("distro",token)
    def new_profile(self,token):
        return self.new_item("profile",token)
    def new_subprofile(self,token):
        return self.new_item("profile",token,is_subobject=True)
    def new_system(self,token):
        return self.new_item("system",token)
    def new_repo(self,token):
        return self.new_item("repo",token)
    def new_image(self,token):
        return self.new_item("image",token)
    def new_mgmtclass(self,token):
        return self.new_item("mgmtclass",token)
    def new_package(self,token):
        return self.new_item("package",token)
    def new_file(self,token):
        return self.new_item("file",token)

    def modify_item(self,what,object_id,attribute,arg,token):
        """
        Adjusts the value of a given field, specified by 'what' on a given object id.
        Allows modification of certain attributes on newly created or
        existing distro object handle.
        """
        self._log("modify_item(%s)" % what,object_id=object_id,attribute=attribute,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token, "modify_%s"%what, obj, attribute)
        # support 1.6 field name exceptions for backwards compat
        attribute = REMAP_COMPAT.get(attribute,attribute)
        method = obj.remote_methods().get(attribute, None)
        if method == None:
            # it's ok, the CLI will send over lots of junk we can't process
            # (like newname or in-place) so just go with it.
            return False
            # raise CX("object has no method: %s" % attribute)
        return method(arg)
    
    def modify_distro(self,object_id,attribute,arg,token):
        return self.modify_item("distro",object_id,attribute,arg,token)
    def modify_profile(self,object_id,attribute,arg,token):
        return self.modify_item("profile",object_id,attribute,arg,token)
    def modify_system(self,object_id,attribute,arg,token):
        return self.modify_item("system",object_id,attribute,arg,token)
    def modify_image(self,object_id,attribute,arg,token):
        return self.modify_item("image",object_id,attribute,arg,token)
    def modify_repo(self,object_id,attribute,arg,token):
        return self.modify_item("repo",object_id,attribute,arg,token)
    def modify_mgmtclass(self,object_id,attribute,arg,token):
        return self.modify_item("mgmtclass",object_id,attribute,arg,token)
    def modify_package(self,object_id,attribute,arg,token):
        return self.modify_item("package",object_id,attribute,arg,token)
    def modify_file(self,object_id,attribute,arg,token):
        return self.modify_item("file",object_id,attribute,arg,token)
    def modify_setting(self,setting_name,value,token):
        try:
            self.api.settings().set(setting_name, value)
            return 0
        except:
            return 1
   
    def __is_interface_field(self,f):
        if f in ("delete_interface","rename_interface"):
           return True

        k = "*%s" % f
        for x in item_system.FIELDS:
           if k == x[0]:
              return True
        return False

    def xapi_object_edit(self,object_type,object_name,edit_type,attributes,token):
        """
        Extended API:  New style object manipulations, 2.0 and later
        Prefered over using new_, modify_, save_ directly.
        Though we must preserve the old ways for backwards compatibility these 
        cause much less XMLRPC traffic.

        edit_type - One of 'add', 'rename', 'copy', 'remove'

        Ex: xapi_object_edit("distro","el5","add",{"kernel":"/tmp/foo","initrd":"/tmp/foo"},token)
        """
        if object_name.strip() == "":
            raise CX("xapi_object_edit() called without an object name")

        self.check_access(token,"xedit_%s" % object_type, token)

        if edit_type == "add" and not attributes.has_key("clobber"):
            handle = 0
            try:
                handle = self.get_item_handle(object_type, object_name)
            except:
                pass
            if handle != 0:
                raise CX("it seems unwise to overwrite this object, try 'edit'")

        if edit_type == "add":
            is_subobject = object_type == "profile" and "parent" in attributes
            if object_type == "system":
                if "profile" not in attributes and "image" not in attributes:
                    raise CX("You must specify a --profile or --image for new systems")
            handle = self.new_item(object_type, token, is_subobject=is_subobject)
        else:
            handle = self.get_item_handle(object_type, object_name)

        if edit_type == "rename":
            self.rename_item(object_type, handle, attributes["newname"], token)
            handle = self.get_item_handle(object_type, attributes["newname"], token)
        if edit_type == "copy":
            self.copy_item(object_type, handle, attributes["newname"], token)
            handle = self.get_item_handle(object_type, attributes["newname"], token)
        if edit_type in [ "copy", "rename" ]:
            del attributes["name"] 
            del attributes["newname"] 

        if edit_type != "remove":
            # FIXME: this doesn't know about interfaces yet!
            # if object type is system and fields add to hash and then
            # modify when done, rather than now.
            imods = {}
            # FIXME: needs to know about how to delete interfaces too!
            for (k,v) in attributes.iteritems():
                if object_type != "system" or not self.__is_interface_field(k):
                    # in place modifications allow for adding a key/value pair while keeping other k/v
                    # pairs intact.
                    if k in ["ks_meta","kernel_options","kernel_options_post","template_files","boot_files","fetchable_files","params"] and attributes.has_key("in_place") and attributes["in_place"]:
                        details = self.get_item(object_type,object_name)
                        v2 = details[k]
                        (ok, input) = utils.input_string_or_hash(v)
                        for (a,b) in input.iteritems():
                            if a.startswith("~") and len(a) > 1:
                                del v2[a[1:]]
                            else:
                                v2[a] = b
                        v = v2

                    self.modify_item(object_type,handle,k,v,token)

                else:
                    modkey = "%s-%s" % (k, attributes.get("interface",""))
                    imods[modkey] = v

            if object_type == "system":
                if not attributes.has_key("delete_interface") and not attributes.has_key("rename_interface"):
                    self.modify_system(handle, 'modify_interface', imods, token)
                elif attributes.has_key("delete_interface"):
                    self.modify_system(handle, 'delete_interface', attributes.get("interface", ""), token)
                elif attributes.has_key("rename_interface"):
                    ifargs = [attributes.get("interface",""),attributes.get("rename_interface","")]
                    self.modify_system(handle, 'rename_interface', ifargs, token)
        else:
           recursive = attributes.get("recursive",False)
           return self.remove_item(object_type, object_name, token, recursive=recursive)

        # FIXME: use the bypass flag or not?
        return self.save_item(object_type, handle, token)
        
 
    def save_item(self,what,object_id,token,editmode="bypass"):
        """
        Saves a newly created or modified object to disk.
        Calling save is required for any changes to persist.
        """
        self._log("save_item(%s)" % what,object_id=object_id,token=token)
        obj = self.__get_object(object_id)
        self.check_access(token,"save_%s"%what,obj)
        if editmode == "new":
            rc = self.api.add_item(what,obj,check_for_duplicate_names=True)
        else:
            rc = self.api.add_item(what,obj)
        return rc

    def save_distro(self,object_id,token,editmode="bypass"):
        return self.save_item("distro",object_id,token,editmode=editmode)
    def save_profile(self,object_id,token,editmode="bypass"):
        return self.save_item("profile",object_id,token,editmode=editmode)
    def save_system(self,object_id,token,editmode="bypass"):
        return self.save_item("system",object_id,token,editmode=editmode)
    def save_image(self,object_id,token,editmode="bypass"):
        return self.save_item("image",object_id,token,editmode=editmode)
    def save_repo(self,object_id,token,editmode="bypass"):
        return self.save_item("repo",object_id,token,editmode=editmode)
    def save_mgmtclass(self,object_id,token,editmode="bypass"):
        return self.save_item("mgmtclass",object_id,token,editmode=editmode)
    def save_package(self,object_id,token,editmode="bypass"):
        return self.save_item("package",object_id,token,editmode=editmode)
    def save_file(self,object_id,token,editmode="bypass"):
        return self.save_item("file",object_id,token,editmode=editmode)

    def get_kickstart_templates(self,token=None,**rest):
        """
        Returns all of the kickstarts that are in use by the system.
        """
        self._log("get_kickstart_templates",token=token)
        #self.check_access(token, "get_kickstart_templates")
        return utils.get_kickstart_templates(self.api)

    def get_snippets(self,token=None,**rest):
        """
        Returns all the kickstart snippets.
        """
        self._log("get_snippets",token=token)

        # FIXME: settings.snippetsdir should be used here
        return self.__get_sub_snippets("/var/lib/cobbler/snippets")

    def __get_sub_snippets(self, path):
        results = []
        files = glob.glob(os.path.join(path,"*"))
        for f in files:
           if os.path.isdir(f) and not os.path.islink(f):
              results += self.__get_sub_snippets(f)
           elif not os.path.islink(f):
              results.append(f)
        results.sort()
        return results

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
        try:
            return self.api.generate_kickstart(profile,system)
        except Exception, e:
            utils.log_exc(self.logger)
            return "# This kickstart had errors that prevented it from being rendered correctly.\n# The cobbler.log should have information relating to this failure."

    def generate_gpxe(self,profile=None,system=None,**rest):
        self._log("generate_gpxe")
        return self.api.generate_gpxe(profile,system)

    def generate_bootcfg(self,profile=None,system=None,**rest):
        self._log("generate_bootcfg")
        return self.api.generate_bootcfg(profile,system)

    def generate_script(self,profile=None,system=None,name=None,**rest):
        self._log("generate_script, name is %s" % str(name))
        return self.api.generate_script(profile,system,name)

    def get_blended_data(self,profile=None,system=None):
        if profile is not None and profile != "":
            obj = self.api.find_profile(profile)
            if obj is None:
                raise CX("profile not found: %s" % profile)
        elif system is not None and system != "":
            obj = self.api.find_system(system)
            if obj is None:
                raise CX("system not found: %s" % system)
        else:
            raise CX("internal error, no system or profile specified")
        return self.xmlrpc_hacks(utils.blender(self.api, True, obj))

    def get_settings(self,token=None,**rest):
        """
        Return the contents of /etc/cobbler/settings, which is a hash.
        """
        self._log("get_settings",token=token)
        results = self.api.settings().to_datastruct()
        self._log("my settings are: %s" % results, debug=True)
        return self.xmlrpc_hacks(results)

    def get_signatures(self,token=None,**rest):
        """
        Return the contents of the API signatures
        """
        self._log("get_signatures",token=token)
        results = self.api.get_signatures()
        return self.xmlrpc_hacks(results)

    def get_valid_breeds(self,token=None,**rest):
        """
        Return the list of valid breeds as read in
        from the distro signatures data
        """
        self._log("get_valid_breeds",token=token)
        results = utils.get_valid_breeds()
        results.sort()
        return self.xmlrpc_hacks(results)

    def get_valid_os_versions(self,token=None,**rest):
        """
        Return the list of valid os_versions as read
        in from the distro signatures data
        """
        self._log("get_valid_os_versions",token=token)
        results = utils.get_valid_os_versions()
        results.sort()
        return self.xmlrpc_hacks(results)

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

    def register_new_system(self,info,token=None,**rest):
        """
        If register_new_installs is enabled in settings, this allows
        /usr/bin/cobbler-register (part of the koan package) to add 
        new system records remotely if they don't already exist.
        There is a cobbler_register snippet that helps with doing
        this automatically for new installs but it can also be used
        for existing installs.  See "AutoRegistration" on the Wiki.
        """
   
        enabled = self.api.settings().register_new_installs
        if not str(enabled) in [ "1", "y", "yes", "true" ]:
            raise CX("registration is disabled in cobbler settings")
  
        # validate input
        name     = info.get("name","")
        profile  = info.get("profile","")
        hostname = info.get("hostname","")
        interfaces = info.get("interfaces",{})
        ilen       = len(interfaces.keys())

        if name == "":
            raise CX("no system name submitted")
        if profile == "":
            raise CX("profile not submitted")
        if ilen == 0:
            raise CX("no interfaces submitted")
        if ilen >= 64:
            raise CX("too many interfaces submitted")

        # validate things first
        name = info.get("name","")
        inames = interfaces.keys()
        if self.api.find_system(name=name):
            raise CX("system name conflicts")
        if hostname != "" and self.api.find_system(hostname=hostname):
            raise CX("hostname conflicts")

        for iname in inames:
            mac      = info["interfaces"][iname].get("mac_address","")
            ip       = info["interfaces"][iname].get("ip_address","")
            if ip.find("/") != -1:
                raise CX("no CIDR ips are allowed")
            if mac == "":
                raise CX("missing MAC address for interface %s" % iname) 
            if mac != "":
                system = self.api.find_system(mac_address=mac)
                if system is not None: 
                   raise CX("mac conflict: %s" % mac)
            if ip != "":
                system = self.api.find_system(ip_address=ip)
                if system is not None:
                   raise CX("ip conflict: %s"%  ip)

        # looks like we can go ahead and create a system now
        obj = self.api.new_system()
        obj.set_profile(profile)
        obj.set_name(name)
        if hostname != "":
           obj.set_hostname(hostname)
        obj.set_netboot_enabled(False)
        for iname in inames:
            if info["interfaces"][iname].get("bridge","") == 1:
               # don't add bridges
               continue
            #if info["interfaces"][iname].get("module","") == "":
            #   # don't attempt to add wireless interfaces
            #   continue
            mac      = info["interfaces"][iname].get("mac_address","")
            ip       = info["interfaces"][iname].get("ip_address","")
            netmask  = info["interfaces"][iname].get("netmask","")
            if mac == "?":
                # see koan/utils.py for explanation of network info discovery
                continue;
            obj.set_mac_address(mac, iname)
            if hostname != "":
                obj.set_dns_name(hostname, iname)
            if ip != "" and ip != "?":
                obj.set_ip_address(ip, iname)
            if netmask != "" and netmask != "?":
                obj.set_netmask(netmask, iname)
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
        # re-generate dhcp configuration
        self.api.sync_dhcp()
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
            self._log("upload_log_data - WARNING - system '%s' not found in cobbler" % sys_name, token=token, name=sys_name)

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
            raise CX("invalid filename used: %s" % fn)

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
                raise CX("destination not a file: %s" % fn)

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

        if mode != "pre" and mode != "post" and mode != "firstboot":
            return False
        if objtype != "system" and objtype !="profile":
            return False

        # the trigger script is called with name,mac, and ip as arguments 1,2, and 3
        # we do not do API lookups here because they are rather expensive at install
        # time if reinstalling all of a cluster all at once.
        # we can do that at "cobbler check" time.

        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/install/%s/*" % mode, additional=[objtype,name,ip],logger=self.logger)


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
    
    def get_mgmtclasses_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_mgmtclasses_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)
    
    def get_packages_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_packages_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)
    
    def get_files_since(self,mtime):
        """
        See documentation for get_distros_since
        """
        data = self.api.get_files_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)
    
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
        return self.get_system_for_koan(name)

    def get_system_for_koan(self,name,token=None,**rest):
        """
        Same as get_system_as_rendered.
        """
        self._log("get_system_as_rendered",name=name,token=token)
        obj = self.api.find_system(name=name)
        if obj is not None:
            hash = utils.blender(self.api,True,obj)
            # Generate a pxelinux.cfg?
            image_based = False
            profile = obj.get_conceptual_parent()
            distro  = profile.get_conceptual_parent()
            arch = distro.arch

            # the management classes stored in the system are just a list 
            # of names, so we need to turn it into a full list of hashes 
            # (right now we just use the params field)
            mcs = hash["mgmt_classes"]
            hash["mgmt_classes"] = {}
            for m in mcs:
                c = self.api.find_mgmtclass(name=m)
                if c:
                    hash["mgmt_classes"][m] = c.to_datastruct()

            if distro is None and profile.COLLECTION_TYPE == "image":
                image_based = True
                arch = profile.arch
            else:
                arch = distro.arch

            if obj.is_management_supported():
                if not image_based:
                    hash["pxelinux.cfg"] = self.pxegen.write_pxe_file(
                        None, obj, profile, distro, arch)
                else:
                    hash["pxelinux.cfg"] = self.pxegen.write_pxe_file(
                        None, obj,None,None,arch,image=profile)

            return self.xmlrpc_hacks(hash)
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
    
    def get_mgmtclass_as_rendered(self,name,token=None,**rest):
        """
        Return the mgmtclass as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_mgmtclass_for_koan(self,name)

    def get_mgmtclass_for_koan(self,name,token=None,**rest):
        """
        Same as get_mgmtclass_as_rendered.
        """
        self._log("get_mgmtclass_as_rendered",name=name,token=token)
        obj = self.api.find_mgmtclass(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})
    
    def get_package_as_rendered(self,name,token=None,**rest):
        """
        Return the package as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_package_for_koan(self,name)

    def get_package_for_koan(self,name,token=None,**rest):
        """
        Same as get_package_as_rendered.
        """
        self._log("get_package_as_rendered",name=name,token=token)
        obj = self.api.find_package(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})
    
    def get_file_as_rendered(self,name,token=None,**rest):
        """
        Return the file as passed through cobbler's
        inheritance/graph engine.  Shows what would be installed, not
        the input data.
        """
        return self.get_file_for_koan(self,name)

    def get_file_for_koan(self,name,token=None,**rest):
        """
        Same as get_file_as_rendered.
        """
        self._log("get_file_as_rendered",name=name,token=token)
        obj = self.api.find_file(name=name)
        if obj is not None:
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_random_mac(self,virt_type="xenpv",token=None,**rest):
        """
        Wrapper for utils.get_random_mac
        Used in the webui
        """
        self._log("get_random_mac",token=None)
        return utils.get_random_mac(self.api,virt_type)

    def xmlrpc_hacks(self,data):
        """
        Convert None in XMLRPC to just '~' to make extra sure a client
        that can't allow_none can deal with this.  ALSO: a weird hack ensuring
        that when dicts with integer keys (or other types) are transmitted
        with string keys.
        """
        return utils.strip_none(data)

    def get_status(self,mode="normal",token=None,**rest):
        """
        Returns the same information as `cobbler status`
        While a read-only operation, this requires a token because it's potentially a fair amount of I/O
        """
        self.check_access(token,"sync")
        return self.api.status(mode=mode)

   ######
   # READ WRITE METHODS REQUIRE A TOKEN, use login()
   # TO OBTAIN ONE
   ######

    def __get_random(self,length):
        urandom = open("/dev/urandom")
        b64 = base64.encodestring(urandom.read(length))
        urandom.close()
        b64 = b64.replace("\n","")
        return b64 

    def __make_token(self,user):
        """
        Returns a new random token.
        """
        b64 = self.__get_random(25)
        self.token_cache[b64] = (time.time(), user)
        return b64

    def __invalidate_expired_tokens(self):
        """
        Deletes any login tokens that might have expired.
        Also removes expired events
        """
        timenow = time.time()
        for token in self.token_cache.keys():
            (tokentime, user) = self.token_cache[token]
            if (timenow > tokentime + self.api.settings().auth_token_expiration):
                self._log("expiring token",token=token,debug=True)
                del self.token_cache[token]
        # and also expired objects
        for oid in self.object_cache.keys():
            (tokentime, entry) = self.object_cache[oid]
            if (timenow > tokentime + CACHE_TIMEOUT):
                del self.object_cache[oid]
        for tid in self.events.keys():
            (eventtime, name, status, who) = self.events[tid]
            if (timenow > eventtime + EVENT_TIMEOUT):
                del self.events[tid]
            # logfile cleanup should be dealt w/ by logrotate

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

        if self.token_cache.has_key(token):
            user = self.get_user_from_token(token)
            if user == "<system>":
               # system token is only valid over Unix socket
               return False
            self.token_cache[token] = (time.time(), user) # update to prevent timeout
            return True
        else:
            self._log("invalid token",token=token)
            return False

    def __name_to_object(self,resource,name):
        if resource.find("distro") != -1:
            return self.api.find_distro(name)
        if resource.find("profile") != -1:
            return self.api.find_profile(name)
        if resource.find("system") != -1:
            return self.api.find_system(name)
        if resource.find("repo") != -1:
            return self.api.find_repo(name)
        if resource.find("mgmtclass") != -1:
            return self.api.find_mgmtclass(name)
        if resource.find("package") != -1:
            return self.api.find_package(name)
        if resource.find("file") != -1:
            return self.api.find_file(name)
        return None

    def check_access_no_fail(self,token,resource,arg1=None,arg2=None):
        """
        This is called by the WUI to decide whether an element
        is editable or not. It differs form check_access in that
        it is supposed to /not/ log the access checks (TBA) and does
        not raise exceptions.
        """

        need_remap = False
        for x in [ "distro", "profile", "system", "repo", "image", "mgmtclass", "package", "file" ]:
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
        if user == "<DIRECT>":
            self._log("CLI Authorized", debug=True)
            return True
        rc = self.api.authorize(user,resource,arg1,arg2)
        self._log("%s authorization result: %s" % (user,rc),debug=True)
        if not rc:
            raise CX("authorization failure for user %s" % user) 
        return rc

    def get_authn_module_name(self, token):
        validated = self.__validate_token(token)
        user = self.get_user_from_token(token)
        if user != "<DIRECT>":
          raise CX("authorization failure for user %s attempting to access authn module name" %user)
        return self.api.get_module_name_from_file("authentication", "module")

    def login(self,login_user,login_password):
        """
        Takes a username and password, validates it, and if successful
        returns a random login token which must be used on subsequent
        method calls.  The token will time out after a set interval if not
        used.  Re-logging in permitted.
        """
       
        # if shared secret access is requested, don't bother hitting the auth
        # plugin
        if login_user == "":
            if login_password == self.shared_secret:
                return self.__make_token("<DIRECT>")
            else:
                utils.die(self.logger, "login failed")

        # this should not log to disk OR make events as we're going to
        # call it like crazy in CobblerWeb.  Just failed attempts.
        if self.__validate_user(login_user,login_password):
            token = self.__make_token(login_user)
            return token
        else:
            utils.die(self.logger, "login failed (%s)" % login_user)

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
        Checks to make sure a token is valid or not
        """
        return self.__validate_token(token)

    def sync_dhcp(self,token):
        """
        Run sync code, which should complete before XMLRPC timeout.  We can't
        do reposync this way.  Would be nice to send output over AJAX/other
        later.
        """
        self._log("sync_dhcp",token=token)
        self.check_access(token,"sync")
        return self.api.sync_dhcp()

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

    def read_or_write_kickstart_template(self,kickstart_file,is_read,new_data,token):
        """
        Allows the web app to be used as a kickstart file editor.  For security
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
            utils.die(self.logger,"tainted file location")

        if not kickstart_file.startswith("/etc/cobbler/") and not kickstart_file.startswith("/var/lib/cobbler/kickstarts"):
            utils.die(self.logger, "unable to view or edit kickstart in this location")
        
        if kickstart_file.startswith("/etc/cobbler/"):
           if not kickstart_file.endswith(".ks") and not kickstart_file.endswith(".cfg"):
              # take care to not allow config files to be altered.
              utils.die(self.logger, "this does not seem to be a kickstart file")
           if not is_read and not os.path.exists(kickstart_file):
              utils.die(self.logger, "new files must go in /var/lib/cobbler/kickstarts")
        
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
                    utils.die(self.logger, "attempt to delete in-use file")
            else:
                fileh = open(kickstart_file,"w+")
                fileh.write(new_data)
                fileh.close()
            return True

    def read_or_write_snippet(self,snippet_file,is_read,new_data,token):
        """
        Allows the WebUI to be used as a snippet file editor.  For security
        reasons we will only allow snippet files to be edited if they reside in
        /var/lib/cobbler/snippets.
        """
        # FIXME: duplicate code with kickstart view/edit
        # FIXME: need to move to API level functions

        if is_read:
           what = "read_snippet"
        else:
           what = "write_snippet"

        self._log(what,name=snippet_file,token=token)
        self.check_access(token,what,snippet_file,is_read)
 
        if snippet_file.find("..") != -1 or not snippet_file.startswith("/"):
            utils.die(self.logger, "tainted file location")

        # FIXME: shouldn't we get snippetdir from the settings?
        if not snippet_file.startswith("/var/lib/cobbler/snippets"):
            utils.die(self.logger, "unable to view or edit snippet in this location")
        
        if is_read:
            fileh = open(snippet_file,"r")
            data = fileh.read()
            fileh.close()
            return data
        else:
            if new_data == -1:
                # FIXME: no way to check if something is using it
                os.remove(snippet_file)
            else:
                # path_part(a,b) checks for the path b to be inside path a. It is
                # guaranteed to return either an empty string (meaning b is NOT inside
                # a), or a path starting with '/'. If the path ends with '/' the sub-path 
                # is a directory so we don't write to it.

                # FIXME: shouldn't we get snippetdir from the settings?
                path_part = utils.path_tail("/var/lib/cobbler/snippets",snippet_file)
                if path_part != "" and path_part[-1] != "/":
                    try:
                        utils.mkdir(os.path.dirname(snippet_file))
                    except:
                        utils.die(self.logger, "unable to create directory for snippet file: '%s'" % snippet_file)
                    fileh = open(snippet_file,"w+")
                    fileh.write(new_data)
                    fileh.close()
                else:
                    utils.die(self.logger, "invalid snippet file specified: '%s'" % snippet_file)
            return True


    def power_system(self,object_id,power=None,token=None,logger=None):
        """
        Internal implementation used by background_power, do not call
        directly if possible.  
        Allows poweron/poweroff/powerstatus/reboot of a system specified by object_id.
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "power_system", obj)
        if power=="on":
            rc=self.api.power_on(obj, user=None, password=None, logger=logger)
        elif power=="off":
            rc=self.api.power_off(obj, user=None, password=None, logger=logger)
        elif power=="status":
            rc=self.api.power_status(obj, user=None, password=None, logger=logger)
        elif power=="reboot":
            rc=self.api.reboot(obj, user=None, password=None, logger=logger)
        else:
            utils.die(self.logger, "invalid power mode '%s', expected on/off/status/reboot" % power)
        return rc

    def get_config_data(self,hostname):
        """
        Generate configuration data for the system specified by hostname.
        """
        self._log("get_config_data for %s" % hostname)
        obj = configgen.ConfigGen(hostname)
        return obj.gen_config_data_for_koan()

    def clear_system_logs(self, object_id, token=None, logger=None):
        """
        clears console logs of a system
        """
        obj = self.__get_object(object_id)
        self.check_access(token, "clear_system_logs", obj)
        rc=self.api.clear_logs(obj, logger=logger)
        return rc

# *********************************************************************************
# *********************************************************************************

class CobblerXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)

# *********************************************************************************
# *********************************************************************************


class ProxiedXMLRPCInterface:

    def __init__(self,api,proxy_class):
        self.proxied = proxy_class(api)
        self.logger = self.proxied.api.logger

    def _dispatch(self, method, params, **rest):

        if not hasattr(self.proxied, method):
            raise CX("unknown remote method")

        method_handle = getattr(self.proxied, method)

        # FIXME: see if this works without extra boilerplate
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
    fh = open(DEFAULTS)
    data = yaml.safe_load(fh.read())
    fh.close()
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
    fh = open(DEFAULTS)
    data = yaml.safe_load(fh.read())
    fh.close()
    data["pxe_once"] = pxe_once

    t = Template.Template(file=MODULES_TEMPLATE, searchList=[data])
    open("/etc/cobbler/settings","w+").write(t.respond())

    

def _test_bootstrap_restart():

   rc1 = utils.subprocess_call(None,"/sbin/service cobblerd restart",shell=False)
   assert rc1 == 0
   rc2 = utils.subprocess.call(None,"/sbin/service httpd restart",shell=False)
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
   rc = utils.subprocess_call(None,"cp rpm-build/*.rpm /tmp/empty",shell=True)
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
   server.modify_distro(did, "redhat_management_server", "rhn.example.com", token)
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
   server.modify_profile(pid, "kopts_post", "noapic", token)
   server.modify_profile(pid, "virt_auto_boot", 0, token)
   server.modify_profile(pid, "virt_file_size", 20, token)
   server.modify_profile(pid, "virt_disk_driver", "raw", token)
   server.modify_profile(pid, "virt_ram", 2048, token)
   server.modify_profile(pid, "repos", [], token)
   server.modify_profile(pid, "template-files", {}, token)
   server.modify_profile(pid, "virt_path", "VolGroup00", token)
   server.modify_profile(pid, "virt_bridge", "virbr1", token)
   server.modify_profile(pid, "virt_cpus", 2, token)
   server.modify_profile(pid, "owners", [ "sam", "dave" ], token)
   server.modify_profile(pid, "mgmt_classes", "one two three", token)
   server.modify_profile(pid, "comment", "...", token)
   server.modify_profile(pid, "name_servers", ["one","two"], token)
   server.modify_profile(pid, "name_servers_search", ["one","two"], token)
   server.modify_profile(pid, "redhat_management_key", "BETA", token)
   server.modify_distro(did, "redhat_management_server", "sat.example.com", token)
   server.save_profile(pid, token)

   api.deserialize() 
   assert api.find_profile("profile1") != None

   sid = server.new_system(token)
   server.modify_system(sid, 'name', 'system1', token)
   server.modify_system(sid, 'hostname', 'system1', token)
   server.modify_system(sid, 'gateway', '127.0.0.1', token)
   server.modify_system(sid, 'profile', 'profile1', token)
   server.modify_system(sid, 'kopts', { "dog" : "fido" }, token)
   server.modify_system(sid, 'kopts_post', { "cat" : "fluffy" }, token)
   server.modify_system(sid, 'kickstart', '/var/lib/cobbler/kickstarts/sample.ks', token)
   server.modify_system(sid, 'netboot_enabled', True, token)
   server.modify_system(sid, 'virt_path', "/opt/images", token)
   server.modify_system(sid, 'virt_type', 'qemu', token)
   server.modify_system(sid, 'name_servers', 'one two three four', token)
   server.modify_system(sid, 'name_servers_search', 'one two three four', token)
   server.modify_system(sid, 'modify_interface', { 
       "macaddress-eth0"   : "AA:BB:CC:EE:EE:EE",
       "ipaddress-eth0"    : "192.168.10.50",
       "gateway-eth0"      : "192.168.10.1",
       "virtbridge-eth0"   : "virbr0",
       "dnsname-eth0"      : "foo.example.com",
       "static-eth0"       : False,
       "dhcptag-eth0"      : "section2",
       "staticroutes-eth0" : "a:b:c d:e:f"
   }, token)
   server.modify_system(sid, 'modify_interface', {
       "static-eth1"     : False,
       "staticroutes-eth1" : [ "g:h:i", "j:k:l" ]
   }, token)
   server.modify_system(sid, "mgmt_classes", [ "one", "two", "three"], token)
   server.modify_system(sid, "template_files", {}, token)
   server.modify_system(sid, "boot_files",     {}, token)
   server.modify_system(sid, "fetchable_files", {}, token)
   server.modify_system(sid, "comment", "...", token)
   server.modify_system(sid, "power_address", "power.example.org", token)
   server.modify_system(sid, "power_type", "ipmitool", token)
   server.modify_system(sid, "power_user", "Admin", token)
   server.modify_system(sid, "power_pass", "magic", token)
   server.modify_system(sid, "power_id", "7", token)
   server.modify_system(sid, "redhat_management_key", "GAMMA", token)
   server.modify_distro(did, "redhat_management_server", "spacewalk.example.com", token)

   server.save_system(sid,token)
   
   api.deserialize() 
   assert api.find_system("system1") != None
   # FIXME: add some checks on object contents

   iid = server.new_image(token)
   server.modify_image(iid, "name", "image1", token)
   server.modify_image(iid, "image_type", "iso", token)
   server.modify_image(iid, "breed", "redhat", token)
   server.modify_image(iid, "os_version", "rhel5", token)
   server.modify_image(iid, "arch", "x86_64", token)
   server.modify_image(iid, "file", "nfs://server/path/to/x.iso", token)
   server.modify_image(iid, "owners", [ "alex", "michael" ], token)
   server.modify_image(iid, "virt_auto_boot", 0, token)
   server.modify_image(iid, "virt_cpus", 1, token)
   server.modify_image(iid, "virt_file_size", 5, token)
   server.modify_image(iid, "virt_disk_driver", "raw", token)
   server.modify_image(iid, "virt_bridge", "virbr0", token)
   server.modify_image(iid, "virt_path", "VolGroup01", token)
   server.modify_image(iid, "virt_ram", 1024, token)
   server.modify_image(iid, "virt_type", "xenpv", token)
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
   server.modify_repo(rid, "keep_updated", True, token)
   server.modify_repo(rid, "priority", "50", token)
   server.modify_repo(rid, "rpm_list", [], token)
   server.modify_repo(rid, "createrepo_flags", "--verbose", token)
   server.modify_repo(rid, "yumopts", {}, token)
   server.modify_repo(rid, "owners", [ "slash", "axl" ], token)
   server.modify_repo(rid, "mirror_locally", True, token)
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

