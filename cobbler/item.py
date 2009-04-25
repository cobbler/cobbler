"""
An Item is a serializable thing that can appear in a Collection

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import exceptions
import serializable
import utils
from cexceptions import *
from utils import _
import pprint
import fnmatch

class Item(serializable.Serializable):

    TYPE_NAME = "generic"

    def __init__(self,config,is_subobject=False):
        """
        Constructor.  Requires a back reference to the Config management object.
        
        NOTE: is_subobject is used for objects that allow inheritance in their trees.  This
        inheritance refers to conceptual inheritance, not Python inheritance.  Objects created
        with is_subobject need to call their set_parent() method immediately after creation
        and pass in a value of an object of the same type.  Currently this is only supported
        for profiles.  Subobjects blend their data with their parent objects and only require
        a valid parent name and a name for themselves, so other required options can be
        gathered from items further up the cobbler tree.

        Old cobbler:             New cobbler:
        distro                   distro
          profile                   profile
            system                     profile  <-- created with is_subobject=True
                                         system   <-- created as normal

        For consistancy, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.

        """

        self.config = config
        self.settings = self.config._settings
        self.clear(is_subobject)      # reset behavior differs for inheritance cases
        self.parent = ''              # all objects by default are not subobjects
        self.children = {}            # caching for performance reasons, not serialized
        self.log_func = self.config.api.log        
        self.ctime = 0 # to be filled in by collection class
        self.mtime = 0 # to be filled in by collection class
        self.uid = ""  # to be filled in by collection class

        self.last_cached_mtime = 0
        self.cached_datastruct = ""

    def clear(self):
        raise exceptions.NotImplementedError

    def get_children(self,sorted=True):
        """
        Get direct children of this object.
        """
        keys = self.children.keys()
        if sorted:
            keys.sort()
        results = []
        for k in keys:
            results.append(self.children[k])
        return results

    def get_descendants(self):
        """
        Get objects that depend on this object, i.e. those that
        would be affected by a cascading delete, etc.
        """
        results = []
        kids = self.get_children(sorted=False)
        results.extend(kids)
        for kid in kids:
            grandkids = kid.get_descendants()
            results.extend(grandkids)
        return results

    def get_parent(self):
        """
        For objects with a tree relationship, what's the parent object?
        """
        return None

    def get_conceptual_parent(self):
        """
        The parent may just be a superclass for something like a
        subprofile.  Get the first parent of a different type.
        """

        # FIXME: this is a workaround to get the type of an instance var
        # what's a more clean way to do this that's python 2.3 friendly?
        # this returns something like:  cobbler.item_system.System
        mtype = str(self).split(" ")[0][1:]
        parent = self.get_parent()
        while parent is not None:
           ptype = str(parent).split(" ")[0][1:]
           if mtype != ptype:
              self.conceptual_parent = parent
              return parent
           parent = parent.get_parent()
        return None

    def set_name(self,name):
        """
        All objects have names, and with the exception of System
        they aren't picky about it.
        """
        if self.name not in ["",None] and self.parent not in ["",None] and self.name == self.parent:
            raise CX(_("self parentage is weird"))
        if not isinstance(name, basestring):
            raise CX(_("name must be a string"))
        for x in name:
            if not x.isalnum() and not x in [ "_", "-", ".", ":", "+" ] :
                raise CX(_("invalid characters in name: '%s'" % name)) 
        self.name = name
        return True

    def set_comment(self, comment):
        if comment is None:
           comment = ""
        self.comment = comment
        return True

    def set_owners(self,data):
        """
        The owners field is a comment unless using an authz module that pays attention to it,
        like authz_ownership, which ships with Cobbler but is off by default.  Consult the Wiki
        docs for more info on CustomizableAuthorization.
        """
        owners = utils.input_string_or_list(data, delim=" ")
        self.owners = owners
        return True

    def set_kernel_options(self,options,inplace=False):
        """
	Kernel options are a space delimited list,
	like 'a=b c=d e=f g h i=j' or a hash.
	"""
        (success, value) = utils.input_string_or_hash(options,None)
        if not success:
            raise CX(_("invalid kernel options"))
        else:
            if inplace:
                for key in value.keys():
                    if key.startswith("~"):
                        del self.kernel_options[key[1:]]
                    else:
                        self.kernel_options[key] = value[key]
            else:
                self.kernel_options = value
            return True

    def set_kernel_options_post(self,options,inplace=False):
        """
        Post kernel options are a space delimited list,
        like 'a=b c=d e=f g h i=j' or a hash.
        """
        (success, value) = utils.input_string_or_hash(options,None)
        if not success:
            raise CX(_("invalid post kernel options"))
        else:
            if inplace:
                for key in value.keys():
                    if key.startswith("~"):
                        del self.self.kernel_options_post[key[1:]]
                    else:
                        self.kernel_options_post[key] = value[key]
            else:
                self.kernel_options_post = value
            return True

    def set_ksmeta(self,options,inplace=False):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a hash.
        The meta tags are used as input to the templating system
        to preprocess kickstart files
        """
        (success, value) = utils.input_string_or_hash(options,None,allow_multiples=False)
        if not success:
            return False
        else:
            if inplace:
                for key in value.keys():
                    if key.startswith("~"):
                        del self.ks_meta[key[1:]]
                    else:
                        self.ks_meta[key] = value[key]
            else:
                self.ks_meta = value
            return True

    def set_mgmt_classes(self,mgmt_classes):
        """
        Assigns a list of configuration management classes that can be assigned
        to any object, such as those used by Puppet's external_nodes feature.
        """
        mgmt_classes_split = utils.input_string_or_list(mgmt_classes, delim=" ")
        self.mgmt_classes = utils.input_string_or_list(mgmt_classes_split)
        return True

    def set_template_files(self,template_files,inplace=False):
        """
        A comma seperated list of source=destination templates
        that should be generated during a sync.
        """
        (success, value) = utils.input_string_or_hash(template_files,None,allow_multiples=False)
        if not success:
            return False
        else:
            if inplace:
                for key in value.keys():
                    if key.startswith("~"):
                        del self.template_files[key[1:]]
                    else:
                        self.template_files[key] = value[key]
            else:
                self.template_files = value
            return True

    def load_item(self,datastruct,key,default=''):
        """
        Used in subclass from_datastruct functions to load items from
        a hash.  Intented to ease backwards compatibility of config
        files during upgrades.  
        """
        if datastruct.has_key(key):
            return datastruct[key]
        return default

    def to_datastruct_with_cache(self):
        """
        Try to not create or run to_datastruct
        when we the object has not changed so we create
        less Python objects.
        """
        if not (self.mtime == 0) and (self.last_cached_mtime == self.mtime):
            # print "FROM CACHE = %s" % self.last_cached_mtime
            return self.cached_datastruct
        else:
            # print "CACHE STORE = %s" % self.mtime
            self.last_cached_mtime = self.mtime
            self.cached_datastruct = self.to_datastruct()
            return self.cached_datastruct

    def to_datastruct(self):
        """
	Returns an easily-marshalable representation of the collection.
	i.e. dictionaries/arrays/scalars.
	"""
        raise exceptions.NotImplementedError

    def is_valid(self):
        """
	The individual set_ methods will return failure if any set is
	rejected, but the is_valid method is intended to indicate whether
	the object is well formed ... i.e. have all of the important
	items been set, are they free of conflicts, etc.
	"""
        return False

    def sort_key(self,sort_fields=[]):
        data = self.to_datastruct()
        return [data.get(x,"") for x in sort_fields]
        
    def find_match(self,kwargs,no_errors=False):
        # used by find() method in collection.py
        data = self.to_datastruct()
        self.log_func("kwargs: %s" % kwargs)
        for (key, value) in kwargs.iteritems():
            # Allow ~ to negate the compare
            if value is not None and value.startswith("~"):
                res=not self.find_match_single_key(data,key,value[1:],no_errors)
            else:
                res=self.find_match_single_key(data,key,value,no_errors)
            if not res:
                return False
                
        return True
 

    def find_match_single_key(self,data,key,value,no_errors=False):
        # special case for systems
        key_found_already = False
        if data.has_key("interfaces"):
            if key in [ "mac_address", "ip_address", "subnet", "virt_bridge", "dhcp_tag", "dns_name", "static_routes", "bonding", "bonding_opts", "bonding_master" ]:
                key_found_already = True
                for (name, interface) in data["interfaces"].iteritems(): 
                    if value is not None:
                        if self.__find_compare(interface[key], value):
                            return True

        if not data.has_key(key):
            if not key_found_already:
                if not no_errors:
                   raise CX(_("searching for field that does not exist: %s" % key))
            else:
                if value is not None: # FIXME: new?
                   return False

        if value is None:
            return True
        else:
            return self.__find_compare(value, data[key])


    def __find_compare(self, from_search, from_obj):

        if isinstance(from_obj, basestring):
            # FIXME: fnmatch is only used for string to string comparisions
            # which should cover most major usage, if not, this deserves fixing
            if fnmatch.fnmatch(from_obj.lower(), from_search.lower()):
                return True
            else:
                return False    
        
        else:
            if isinstance(from_search, basestring):
                if type(from_obj) == type([]):
                    from_search = utils.input_string_or_list(from_search,delim=',')
                    for x in from_search:
                        if x not in from_obj:
                            return False
                    return True            

                if type(from_obj) == type({}):
                    (junk, from_search) = utils.input_string_or_hash(from_search,delim=" ",allow_multiples=True)
                    for x in from_search.keys():
                        y = from_search[x]
                        if not from_obj.has_key(x):
                            return False
                        if not (y == from_obj[x]):
                            return False
                    return True

                if type(from_obj) == type(True):
                    if from_search.lower() in [ "true", "1", "y", "yes" ]:
                        inp = True
                    else:
                        inp = False
                    if inp == from_obj:
                        return True
                    return False
                
            raise CX(_("find cannot compare type: %s") % type(from_obj)) 


    def dump_vars(self,data,format=True):
        raw = utils.blender(self.config.api, False, self)
        if format:
            return pprint.pformat(raw)
        else:
            return raw


    def to_datastruct(self):
        data={}
        for field_key in self.get_field_info().keys():
            data[field_key]=getattr(self,field_key)
        return data

    def printable(self,nice_headers=False):
        buf=""
        field_info_dict=self.get_field_info()
        field_info_keys=field_info_dict.keys()
        field_info_keys.sort()
        for field_key in field_info_keys:
            field_info=field_info_dict[field_key]
            field_value=getattr(self,field_key)
            if field_info["input_type"]=='dict':
                buf+=_("%s {\n" % (field_info["header"]))
                field_value_keys=field_value.keys()
                field_value_keys.sort()
                for subfield_key in field_value_keys:
                    subfield_dict=field_value[subfield_key]
                    if field_info.has_key("fields"):
                        buf+=_("  %s {\n" % (subfield_key))
                        subfield_keys=field_info["fields"].keys()
                        subfield_keys.sort()
                        for subfield_key in subfield_keys:
                            subfield_info=field_info["fields"][subfield_key]
                            if subfield_key!="key":
                                subfield_value=subfield_dict.get(subfield_key,'')
                                if nice_headers:
                                    prefix=subfield_info["header"]
                                else:
                                    prefix=subfield_key
                                buf+=_("    %-20s : %s\n" % (prefix, subfield_value))
                        buf+=_("  }\n")
                    else:
                        buf+=_("  {%s}\n" % utils.hash_to_string(subfield_dict))
                buf+=_("}\n")
            else:
                if nice_headers:
                    prefix=field_info["header"]
                else:
                    prefix=field_key
                buf+=_("%-30s : %s\n" % (prefix, field_value))
        return buf


