"""
Base class for any serializable list of things...

Copyright 2006-2008, Red Hat, Inc
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

import exceptions
from cexceptions import *
import serializable
import utils
import glob
import time
import sub_process
import random

import action_litesync
import item_system
import item_profile
import item_distro
import item_repo
import item_image
from utils import _

class Collection(serializable.Serializable):

    def __init__(self,config):
        """
        Constructor.
        """
        self.config = config
        self.clear()
        self.api = self.config.api
        self.log_func = self.api.log
        self.lite_sync = None

    def factory_produce(self,config,seed_data):
        """
        Must override in subclass.  Factory_produce returns an Item object
        from datastructure seed_data
        """
        raise exceptions.NotImplementedError

    def clear(self):
        """
        Forget about objects in the collection.
        """
        self.listing = {}

    def find(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Return first object in the collection that maches all item='value'
        pairs passed, else return None if no objects can be found.
        When return_list is set, can also return a list.  Empty list
        would be returned instead of None in that case.
        """

        matches = []

        # support the old style innovation without kwargs
        if name is not None:
            kargs["name"] = name

        kargs = self.__rekey(kargs)

        # no arguments is an error, so we don't return a false match
        if len(kargs) == 0:
            raise CX(_("calling find with no arguments"))

        # performance: if the only key is name we can skip the whole loop
        if len(kargs) == 1 and kargs.has_key("name") and not return_list:
            return self.listing.get(kargs["name"].lower(), None)

        for (name, obj) in self.listing.iteritems():
            if obj.find_match(kargs, no_errors=no_errors):
                matches.append(obj)

        if not return_list:
            if len(matches) == 0:
                return None
            return matches[0]
        else:
            return matches


    SEARCH_REKEY = {
           'kopts'           : 'kernel_options',
           'kopts_post'      : 'kernel_options_post',
           'ksmeta'          : 'ks_meta',
           'inherit'         : 'parent',
           'ip'              : 'ip_address',
           'mac'             : 'mac_address',
           'virt-file-size'  : 'virt_file_size',
           'virt-ram'        : 'virt_ram',
           'virt-path'       : 'virt_path',
           'virt-type'       : 'virt_type',
           'virt-bridge'     : 'virt_bridge',
           'virt-cpus'       : 'virt_cpus',
           'dhcp-tag'        : 'dhcp_tag',
           'netboot-enabled' : 'netboot_enabled'
    }

    def __rekey(self,hash):
        """
        Find calls from the command line ("cobbler system find") 
        don't always match with the keys from the datastructs and this
        makes them both line up without breaking compatibility with either.
        Thankfully we don't have a LOT to remap.
        """
        newhash = {}
        for x in hash.keys():
           if self.SEARCH_REKEY.has_key(x):
              newkey = self.SEARCH_REKEY[x]
              newhash[newkey] = hash[x]
           else:
              newhash[x] = hash[x]   
        return newhash

    def to_datastruct(self):
        """
        Serialize the collection
        """
        datastruct = [x.to_datastruct() for x in self.listing.values()]
        return datastruct

    def from_datastruct(self,datastruct):
        if datastruct is None:
            return
        for seed_data in datastruct:
            item = self.factory_produce(self.config,seed_data)
            self.add(item)

    def copy(self,ref,newname):
        ref.name = newname
        ref.uid = self.config.generate_uid()
        if ref.COLLECTION_TYPE == "system":
            # this should only happen for systems
            for iname in ref.interfaces.keys():
                # clear all these out to avoid DHCP/DNS conflicts
                ref.set_dns_name("",iname)
                ref.set_mac_address("",iname)
                ref.set_ip_address("",iname)
        return self.add(ref,save=True,with_copy=True,with_triggers=True,with_sync=True,check_for_duplicate_names=True,check_for_duplicate_netinfo=False)

    def rename(self,ref,newname,with_sync=True,with_triggers=True):
        """
        Allows an object "ref" to be given a newname without affecting the rest
        of the object tree. 
        """

        # make a copy of the object, but give it a new name.
        oldname = ref.name
        newref = ref.make_clone()
        newref.set_name(newname)

        self.add(newref, with_triggers=with_triggers,save=True)

        # now descend to any direct ancestors and point them at the new object allowing
        # the original object to be removed without orphanage.  Direct ancestors
        # will either be profiles or systems.  Note that we do have to care as
        # set_parent is only really meaningful for subprofiles. We ideally want a more
        # generic set_parent.
        kids = ref.get_children()
        for k in kids:
            if k.COLLECTION_TYPE == "distro":
               raise CX(_("internal error, not expected to have distro child objects"))
            elif k.COLLECTION_TYPE == "profile":
               if k.parent != "":
                  k.set_parent(newname)
               else:
                  k.set_distro(newname)
               self.api.profiles().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif k.COLLECTION_TYPE == "system":
               k.set_profile(newname)
               self.api.systems().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif k.COLLECTION_TYPE == "repo":
               raise CX(_("internal error, not expected to have repo child objects"))
            else:
               raise CX(_("internal error, unknown child type (%s), cannot finish rename" % k.COLLECTION_TYPE))
       
        # now delete the old version
        self.remove(oldname, with_delete=True, with_triggers=with_triggers)
        return True


    def add(self,ref,save=False,with_copy=False,with_triggers=True,with_sync=True,quick_pxe_update=False,check_for_duplicate_names=False,check_for_duplicate_netinfo=False):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).

        with_copy is a bit of a misnomer, but lots of internal add operations
        can run with "with_copy" as False. True means a real final commit, as if
        entered from the command line (or basically, by a user).  
 
        With with_copy as False, the particular add call might just be being run 
        during deserialization, in which case extra semantics around the add don't really apply.
        So, in that case, don't run any triggers and don't deal with any actual files.

        """
    
        if ref.uid == '':
           ref.uid = self.config.generate_uid()
        
        if save is True:
            now = time.time()
            if ref.ctime == 0:
                ref.ctime = now
            ref.mtime = now

        if self.lite_sync is None:
            self.lite_sync = action_litesync.BootLiteSync(self.config)

        # migration path for old API parameter that I've renamed.
        if with_copy and not save:
            save = with_copy

        if not save:
            # for people that aren't quite aware of the API
            # if not saving the object, you can't run these features
            with_triggers = False
            with_sync = False
        
        # Avoid adding objects to the collection
        # if an object of the same/ip/mac already exists.
        self.__duplication_checks(ref,check_for_duplicate_names,check_for_duplicate_netinfo)


        if ref is None or not ref.is_valid():
            raise CX(_("insufficient or invalid arguments supplied"))

        if ref.COLLECTION_TYPE != self.collection_type():
            raise CX(_("API error: storing wrong data type in collection"))

        if not save:
            # don't need to run triggers, so add it already ...
            self.listing[ref.name.lower()] = ref


        # perform filesystem operations
        if save:
            self.log_func("saving %s %s" % (self.collection_type(), ref.name))
            # failure of a pre trigger will prevent the object from being added
            if with_triggers:
                self._run_triggers(ref,"/var/lib/cobbler/triggers/add/%s/pre/*" % self.collection_type())
            self.listing[ref.name.lower()] = ref

            # save just this item if possible, if not, save
            # the whole collection
            self.config.serialize_item(self, ref)

            if with_sync:
                if isinstance(ref, item_system.System):
                    self.lite_sync.add_single_system(ref.name)
                elif isinstance(ref, item_profile.Profile):
                    self.lite_sync.add_single_profile(ref.name) 
                elif isinstance(ref, item_distro.Distro):
                    self.lite_sync.add_single_distro(ref.name)
                elif isinstance(ref, item_image.Image):
                    self.lite_sync.add_single_image(ref.name)
                elif isinstance(ref, item_repo.Repo):
                    pass
                else:
                    print _("Internal error. Object type not recognized: %s") % type(ref)
            if not with_sync and quick_pxe_update:
                if isinstance(ref, item_system.System):
                    self.lite_sync.update_system_netboot_status(ref.name)

            # save the tree, so if neccessary, scripts can examine it.
            if with_triggers:
                self._run_triggers(ref,"/var/lib/cobbler/triggers/add/%s/post/*" % self.collection_type())
        
        # update children cache in parent object
        parent = ref.get_parent()
        if parent != None:
            parent.children[ref.name] = ref

        return True

    def _run_triggers(self,ref,globber):
        return utils.run_triggers(ref,globber)

    def __duplication_checks(self,ref,check_for_duplicate_names,check_for_duplicate_netinfo):
        """
        Prevents adding objects with the same name.
        Prevents adding or editing to provide the same IP, or MAC.
        Enforcement is based on whether the API caller requests it.
        """

        # always protect against duplicate names
        if check_for_duplicate_names:
            match = None
            if isinstance(ref, item_system.System):
                match = self.api.find_system(ref.name)
            elif isinstance(ref, item_profile.Profile):
                match = self.api.find_profile(ref.name)
            elif isinstance(ref, item_distro.Distro):
                match = self.api.find_distro(ref.name)
            elif isinstance(ref, item_repo.Repo):
                match = self.api.find_repo(ref.name)

            if match:
                raise CX(_("An object already exists with that name.  Try 'edit'?"))
        
        # the duplicate mac/ip checks can be disabled.
        if not check_for_duplicate_netinfo:
            return
       
        if isinstance(ref, item_system.System):
           for (name, intf) in ref.interfaces.iteritems():
               match_ip    = []
               match_mac   = []
               match_hosts = []
               input_mac   = intf["mac_address"] 
               input_ip    = intf["ip_address"]
               input_dns   = intf["dns_name"]
               if not self.api.settings().allow_duplicate_macs and input_mac is not None and input_mac != "":
                   match_mac = self.api.find_system(mac_address=input_mac,return_list=True)   
               if not self.api.settings().allow_duplicate_ips and input_ip is not None and input_ip != "":
                   match_ip  = self.api.find_system(ip_address=input_ip,return_list=True) 
               # it's ok to conflict with your own net info.

               if not self.api.settings().allow_duplicate_hostnames and input_dns is not None and input_dns != "":
                   match_hosts = self.api.find_system(dns_name=input_dns,return_list=True)

               for x in match_mac:
                   if x.name != ref.name:
                       raise CX(_("Can't save system %s. The MAC address (%s) is already used by system %s (%s)") % (ref.name, intf["mac_address"], x.name, name))
               for x in match_ip:
                   if x.name != ref.name:
                       raise CX(_("Can't save system %s. The IP address (%s) is already used by system %s (%s)") % (ref.name, intf["ip_address"], x.name, name))
               for x in match_hosts:
                   if x.name != ref.name:
                       raise CX(_("Can't save system %s.  The dns name (%s) is already used by system %s (%s)") % (ref.name, intf["dns_name"], x.name, name))
 
    def printable(self):
        """
        Creates a printable representation of the collection suitable
        for reading by humans or parsing from scripts.  Actually scripts
        would be better off reading the YAML in the config files directly.
        """
        values = self.listing.values()[:] # copy the values
        values.sort() # sort the copy (2.3 fix)
        results = []
        for i,v in enumerate(values):
           results.append(v.printable())
        if len(values) > 0:
           return "\n\n".join(results)
        else:
           return _("No objects found")

    def __iter__(self):
        """
	Iterator for the collection.  Allows list comprehensions, etc
	"""
        for a in self.listing.values():
	    yield a

    def __len__(self):
        """
	Returns size of the collection
	"""
        return len(self.listing.values())

    def collection_type(self):
        """
        Returns the string key for the name of the collection (for use in messages for humans)
        """
        return exceptions.NotImplementedError


