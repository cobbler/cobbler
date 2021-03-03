"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

import fnmatch
import pprint
from typing import Optional

from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX, NotImplementedException

# the fields has controls what data elements are part of each object.  To add a new field, just add a new
# entry to the list following some conventions to be described later.  You must also add a method called
# set_$fieldname.  Do not write a method called get_$fieldname, that will not be called.
#
# name | default | subobject default | display name | editable? | tooltip | values ? | type
#
# name -- what the filed should be called.   For the command line, underscores will be replaced with
#         a hyphen programatically, so use underscores to seperate things that are seperate words
#
# default value -- when a new object is created, what is the default value for this field?
#
# subobject default -- this applies ONLY to subprofiles, and is most always set to <<inherit>>.  If this
#                      is not item_profile.py it does not matter.
#
# display name -- how the field shows up in the web application and the "cobbler report" command
#
# editable -- should the field be editable in the CLI and web app?  Almost always yes unless
#                it is an internalism.  Fields that are not editable are "hidden"
#
# tooltip -- the caption to be shown in the web app or in "commandname --help" in the CLI
#
# values -- for fields that have a limited set of valid options and those options are always fixed
#           (such as architecture type), the list of valid options goes in this field.
#
# type -- the type of the field.  Used to determine which HTML form widget is used in the web interface
#
#
# the order in which the fields appear in the web application (for all non-hidden
# fields) is defined in field_ui_info.py. The CLI sorts fields alphabetically.
#
# field_ui_info.py also contains a set of "Groups" that describe what other fields
# are associated with what other fields.  This affects color coding and other
# display hints.  If you add a field, please edit field_ui_info.py carefully to match.
#
# additional:  see field_ui_info.py for some display hints.  By default, in the
# web app, all fields are text fields unless field_ui_info.py lists the field in
# one of those dictionaries.
#
# hidden fields should not be added without just cause, explanations about these are:
#
#   ctime, mtime -- times the object was modified, used internally by Cobbler for API purposes
#   uid -- also used for some external API purposes
#   source_repos -- an artifiact of import, this is too complicated to explain on IRC so we just hide it
#                   for RHEL split repos, this is a list of each of them in the install tree, used to generate
#                   repo lines in the automatic installation file to allow installation of x>=RHEL5.  Otherwise unimportant.
#   depth -- used for "cobbler list" to print the tree, makes it easier to load objects from disk also
#   tree_build_time -- loaded from import, this is not useful to many folks so we just hide it.  Avail over API.
#
# so to add new fields
#   (A) understand the above
#   (B) add a field below
#   (C) add a set_fieldname method
#   (D) if field must be viewable/editable via web UI, add a entry in
#       corresponding *_UI_FIELDS_MAPPING dictionary in field_ui_info.py.
#       If field must not be displayed in a text field in web UI, also add
#       an entry in corresponding USES_* list in field_ui_info.py.
#
# in general the set_field_name method should raise exceptions on invalid fields, always.   There are adtl
# validation fields in is_valid to check to see that two seperate fields do not conflict, but in general
# design issues that require this should be avoided forever more, and there are few exceptions.  Cobbler
# must operate as normal with the default value for all fields and not choke on the default values.


class Item:
    """
    An Item is a serializable thing that can appear in a Collection
    """
    converted_cache = {}

    @classmethod
    def get_from_cache(cls, ref):
        """
        Get an object from the cache. This may potentially contain not persisted changes.

        :param ref: The object which is in the cache.
        :return: The object if present or an empty dict.
        """
        return cls.converted_cache.get(ref.COLLECTION_TYPE, {}).get(ref.name)

    @classmethod
    def set_cache(cls, ref, value):
        """
        Add an object to the cache.

        :param ref: An object to identify where to add the item to the cache.
        :param value: The object to add to the cache.
        """
        if ref.COLLECTION_TYPE not in cls.converted_cache:
            cls.converted_cache[ref.COLLECTION_TYPE] = {}
        cls.converted_cache[ref.COLLECTION_TYPE][ref.name] = value

    @classmethod
    def remove_from_cache(cls, ref):
        """
        Remove an item from the cache.

        :param ref: The object reference id to identify the object.
        """
        cls.converted_cache.get(ref.COLLECTION_TYPE, {}).pop(ref.name, None)

    @classmethod
    def __find_compare(cls, from_search, from_obj):
        """
        Only one of the two parameters shall be given in this method. If you give both ``from_obj`` will be preferred.

        :param from_search: Tries to parse this str in the format as a search result string.
        :param from_obj: Tries to parse this str in the format of an obj str.
        :return: True if the comparison succeeded, False otherwise.
        """
        if isinstance(from_obj, str):
            # FIXME: fnmatch is only used for string to string comparisions which should cover most major usage, if
            #        not, this deserves fixing
            from_obj_lower = from_obj.lower()
            from_search_lower = from_search.lower()
            # It's much faster to not use fnmatch if it's not needed
            if '?' not in from_search_lower and '*' not in from_search_lower and '[' not in from_search_lower:
                match = from_obj_lower == from_search_lower
            else:
                match = fnmatch.fnmatch(from_obj_lower, from_search_lower)
            return match
        else:
            if isinstance(from_search, str):
                if isinstance(from_obj, list):
                    from_search = utils.input_string_or_list(from_search)
                    for x in from_search:
                        if x not in from_obj:
                            return False
                    return True
                if isinstance(from_obj, dict):
                    (junk, from_search) = utils.input_string_or_dict(from_search, allow_multiples=True)
                    for x in list(from_search.keys()):
                        y = from_search[x]
                        if x not in from_obj:
                            return False
                        if not (y == from_obj[x]):
                            return False
                    return True
                if isinstance(from_obj, bool):
                    if from_search.lower() in ["true", "1", "y", "yes"]:
                        inp = True
                    else:
                        inp = False
                    if inp == from_obj:
                        return True
                    return False

            raise CX("find cannot compare type: %s" % type(from_obj))

    TYPE_NAME = "generic"

    def __init__(self, collection_mgr, is_subobject: bool = False):
        """
        Constructor.  Requires a back reference to the CollectionManager object.

        NOTE: is_subobject is used for objects that allow inheritance in their trees.  This
        inheritance refers to conceptual inheritance, not Python inheritance.  Objects created
        with is_subobject need to call their set_parent() method immediately after creation
        and pass in a value of an object of the same type.  Currently this is only supported
        for profiles.  Subobjects blend their data with their parent objects and only require
        a valid parent name and a name for themselves, so other required options can be
        gathered from items further up the Cobbler tree.

                           distro
                               profile
                                    profile  <-- created with is_subobject=True
                                         system   <-- created as normal

        For consistancy, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.
        """

        self.collection_mgr = collection_mgr
        self.settings = self.collection_mgr._settings
        self.clear(is_subobject)        # reset behavior differs for inheritance cases
        self.parent = ''                # all objects by default are not subobjects
        self.children = {}              # caching for performance reasons, not serialized
        self.log_func = self.collection_mgr.api.log
        self.ctime = 0                  # to be filled in by collection class
        self.mtime = 0                  # to be filled in by collection class
        self.uid = ""                   # to be filled in by collection class
        self.kernel_options = None
        self.kernel_options_post = None
        self.autoinstall_meta = None
        self.fetchable_files = None
        self.boot_files = None
        self.template_files = None
        self.name = None
        self.last_cached_mtime = 0
        self.cached_dict = ""

    def get_fields(self):
        """
        Get serializable fields
        Must be defined in any subclass
        """
        raise NotImplementedException("Must be implemented in a specific Item")

    def clear(self, is_subobject=False):
        """
        Reset this object.

        :param is_subobject: True if this is a subobject, otherwise the default is enough.
        """
        utils.clear_from_fields(self, self.get_fields(), is_subobject=is_subobject)

    def make_clone(self):
        """
        Must be defined in any subclass
        """
        raise NotImplementedException("Must be implemented in a specific Item")

    def from_dict(self, _dict):
        """
        Modify this object to take on values in ``seed_data``.

        :param _dict: This should contain all values which should be updated.
        """
        utils.from_dict_from_fields(self, _dict, self.get_fields())

    def to_dict(self) -> dict:
        """
        This converts everything in this object to a dictionary.

        :return: A dictionary with all values present in this object.
        """
        if not self.settings.cache_enabled:
            return utils.to_dict_from_fields(self, self.get_fields())

        value = self.get_from_cache(self)
        if value is None:
            value = utils.to_dict_from_fields(self, self.get_fields())
        self.set_cache(self, value)
        if "autoinstall" in value:
            value.update({"kickstart": value["autoinstall"]})
        if "autoinstall_meta" in value:
            value.update({"ks_meta": value["autoinstall_meta"]})
        return value

    def to_string(self) -> str:
        """
        Convert an item into a string.

        :return: The string representation of the object.
        """
        return utils.to_string_from_fields(self, self.get_fields())

    def get_setter_methods(self):
        """
        Get all setter methods which are available in the item.

        :return: A dict with all setter methods.
        """
        return utils.get_setter_methods_from_fields(self, self.get_fields())

    def set_uid(self, uid):
        """
        Setter for the uid of the item.

        :param uid: The new uid.
        """
        self.uid = uid

    def get_children(self, sorted: bool = False) -> list:
        """
        Get direct children of this object.

        :param sorted: If the list has to be sorted or not.
        :return: The list with the children. If no childrens are present an emtpy list is returned.
        """
        keys = list(self.children.keys())
        if sorted:
            keys.sort()
        results = []
        for k in keys:
            results.append(self.children[k])
        return results

    def get_descendants(self, sort: bool = False) -> list:
        """
        Get objects that depend on this object, i.e. those that would be affected by a cascading delete, etc.

        :param sort: If True the list will be a walk of the tree, e.g., distro -> [profile, sys, sys, profile, sys, sys]
        :return: This is a list of all descendants. May be empty if none exist.
        """
        results = []
        kids = self.get_children(sorted=sort)
        if not sort:
            results.extend(kids)
        for kid in kids:
            if sort:
                results.append(kid)
            grandkids = kid.get_descendants(sort=sort)
            results.extend(grandkids)
        return results

    def get_parent(self):
        """
        For objects with a tree relationship, what's the parent object?
        """
        return None

    def get_conceptual_parent(self):
        """
        The parent may just be a superclass for something like a subprofile. Get the first parent of a different type.

        :return: The first item which is conceptually not from the same type.
        """
        mtype = type(self)
        parent = self.get_parent()
        while parent is not None:
            ptype = type(parent)
            if mtype != ptype:
                self.conceptual_parent = parent
                return parent
            parent = parent.get_parent()
        return None

    def set_name(self, name):
        """
        Set the objects name.

        :param name: object name string
        :type name: str
        :return: True or CX
        """
        self.name = validate.object_name(name, self.parent)

    def set_comment(self, comment: str):
        """
        Setter for the comment of the item.

        :param comment: The new comment. If ``None`` the comment will be set to an emtpy string.
        """
        if comment is None:
            comment = ""
        self.comment = comment

    def set_owners(self, data):
        """
        The owners field is a comment unless using an authz module that pays attention to it,
        like authz_ownership, which ships with Cobbler but is off by default.

        :param data: This can be a string or a list which contains all owners.
        """
        self.owners = utils.input_string_or_list(data)

    def set_kernel_options(self, options):
        """
        Kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        :param options: The new kernel options as a space delimited list.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise CX("invalid kernel options")
        else:
            self.kernel_options = value

    def set_kernel_options_post(self, options):
        """
        Post kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        :param options: The new kernel options as a space delimited list.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise CX("invalid post kernel options")
        else:
            self.kernel_options_post = value

    def set_autoinstall_meta(self, options):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system to preprocess automatic installation template files.

        :param options: The new options for the automatic installation meta options.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            return False
        else:
            self.autoinstall_meta = value

    def set_mgmt_classes(self, mgmt_classes):
        """
        Assigns a list of configuration management classes that can be assigned to any object, such as those used by
        Puppet's external_nodes feature.

        :param mgmt_classes: The new options for the management classes of an item.
        """
        mgmt_classes_split = utils.input_string_or_list(mgmt_classes)
        self.mgmt_classes = utils.input_string_or_list(mgmt_classes_split)

    def set_mgmt_parameters(self, mgmt_parameters):
        """
        A YAML string which can be assigned to any object, this is used by Puppet's external_nodes feature.

        :param mgmt_parameters: The management parameters for an item.
        """
        if mgmt_parameters == "<<inherit>>":
            self.mgmt_parameters = mgmt_parameters
        else:
            import yaml
            data = yaml.safe_load(mgmt_parameters)
            if type(data) is not dict:
                raise CX("Input YAML in Puppet Parameter field must evaluate to a dictionary.")
            self.mgmt_parameters = data

    def set_template_files(self, template_files):
        """
        A comma seperated list of source=destination templates that should be generated during a sync.

        :param template_files: The new value for the template files which are used for the item.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(template_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.template_files = value

    def set_boot_files(self, boot_files):
        """
        A comma seperated list of req_name=source_file_path that should be fetchable via tftp.

        :param boot_files: The new value for the boot files used by the item.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(boot_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.boot_files = value

    def set_fetchable_files(self, fetchable_files) -> Optional[bool]:
        """
        A comma seperated list of virt_name=path_to_template that should be fetchable via tftp or a webserver

        :param fetchable_files: Files which will be made available to external users.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(fetchable_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.fetchable_files = value

    def sort_key(self, sort_fields: list = []):
        """
        Convert the item to a dict and sort the data after specific given fields.

        :param sort_fields: The fields to sort the data after.
        :return: The sorted data.
        """
        data = self.to_dict()
        return [data.get(x, "") for x in sort_fields]

    def find_match(self, kwargs, no_errors=False):
        """
        Find from a given dict if the item matches the kv-pairs.

        :param kwargs: The dict to match for in this item.
        :param no_errors: How strict this matching is.
        :return: True if matches or False if the item does not match.
        """
        # used by find() method in collection.py
        data = self.to_dict()
        for (key, value) in list(kwargs.items()):
            # Allow ~ to negate the compare
            if value is not None and value.startswith("~"):
                res = not self.find_match_single_key(data, key, value[1:], no_errors)
            else:
                res = self.find_match_single_key(data, key, value, no_errors)
            if not res:
                return False

        return True

    def find_match_single_key(self, data, key, value, no_errors: bool = False) -> bool:
        """
        Look if the data matches or not. This is an alternative for ``find_match()``.

        :param data: The data to search through.
        :param key: The key to look for int the item.
        :param value: The value for the key.
        :param no_errors: How strict this matching is.
        :return: Whether the data matches or not.
        """
        # special case for systems
        key_found_already = False
        if "interfaces" in data:
            if key in ["mac_address", "ip_address", "netmask", "virt_bridge",
                       "dhcp_tag", "dns_name", "static_routes", "interface_type",
                       "interface_master", "bonding_opts", "bridge_opts",
                       "interface"]:
                key_found_already = True
                for (name, interface) in list(data["interfaces"].items()):
                    if value == name:
                        return True
                    if value is not None and key in interface:
                        if self.__find_compare(interface[key], value):
                            return True

        if key not in data:
            if not key_found_already:
                if not no_errors:
                    # FIXME: removed for 2.0 code, shouldn't cause any problems to not have an exception here?
                    # raise CX("searching for field that does not exist: %s" % key)
                    return False
            else:
                if value is not None:       # FIXME: new?
                    return False

        if value is None:
            return True
        else:
            return self.__find_compare(value, data[key])

    def dump_vars(self, data, format: bool = True):
        """
        Dump all variables.

        :param data: Unused parameter in this method.
        :param format: Whether to format the output or not.
        :return: The raw or formatted data.
        """
        raw = utils.blender(self.collection_mgr.api, False, self)
        if format:
            return pprint.pformat(raw)
        else:
            return raw

    def set_depth(self, depth):
        """
        Setter for depth.

        :param depth: The new value for depth.
        """
        self.depth = depth

    def set_ctime(self, ctime):
        """
        Setter for the creation time of the object.

        :param ctime: The new creation time. Especially usefull for replication Cobbler.
        """
        self.ctime = ctime

    def set_mtime(self, mtime):
        """
        Setter for the modification time of the object.

        :param mtime: The new modification time.
        """
        self.mtime = mtime

    def set_parent(self, parent):
        """
        Set the parent object for this object.

        :param parent: The new parent object. This needs to be a descendant in the logical inheritance chain.
        """
        self.parent = parent

    def check_if_valid(self):
        """
        Raise exceptions if the object state is inconsistent
        """
        if not self.name:
            raise CX("Name is required")
