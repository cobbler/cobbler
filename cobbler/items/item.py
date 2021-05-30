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
import copy
import enum
import fnmatch
import logging
import pprint
import re
import uuid
from typing import Union

import yaml

from cobbler import utils, enums
from cobbler.cexceptions import CX


RE_OBJECT_NAME = re.compile(r'[a-zA-Z0-9_\-.:]*$')


class Item:
    """
    An Item is a serializable thing that can appear in a Collection
    """
    # Constants
    TYPE_NAME = "generic"
    COLLECTION_TYPE = "generic"
    # Class instance variables
    converted_cache = {}

    @classmethod
    def get_from_cache(cls, ref):
        """
        Get an object from the cache. This may potentially contain not persisted changes.

        :param ref: The object which is in the cache.
        :return: The object if present or an empty dict.
        """
        return cls.converted_cache.get(ref.COLLECTION_TYPE, {}).get(ref.uid)

    @classmethod
    def set_cache(cls, ref, value):
        """
        Add an object to the cache.

        :param ref: An object to identify where to add the item to the cache.
        :param value: The object to add to the cache.
        """
        if ref.COLLECTION_TYPE not in cls.converted_cache:
            cls.converted_cache[ref.COLLECTION_TYPE] = {}
        cls.converted_cache[ref.COLLECTION_TYPE][ref.uid] = value

    @classmethod
    def remove_from_cache(cls, ref):
        """
        Remove an item from the cache.

        :param ref: The object reference id to identify the object.
        """
        cls.converted_cache.get(ref.COLLECTION_TYPE, {}).pop(ref.uid, None)

    @classmethod
    def __find_compare(cls, from_search, from_obj):
        """
        Only one of the two parameters shall be given in this method. If you give both ``from_obj`` will be preferred.

        :param from_search: Tries to parse this str in the format as a search result string.
        :param from_obj: Tries to parse this str in the format of an obj str.
        :return: True if the comparison succeeded, False otherwise.
        :raises CX
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

            raise TypeError("find cannot compare type: %s" % type(from_obj))

    def __init__(self, api, is_subobject: bool = False):
        """
        Constructor.  Requires a back reference to the CollectionManager object.

        NOTE: is_subobject is used for objects that allow inheritance in their trees. This inheritance refers to
        conceptual inheritance, not Python inheritance. Objects created with is_subobject need to call their
        setter for parent immediately after creation and pass in a value of an object of the same type. Currently this
        is only supported for profiles. Subobjects blend their data with their parent objects and only require a valid
        parent name and a name for themselves, so other required options can be gathered from items further up the
        Cobbler tree.

                           distro
                               profile
                                    profile  <-- created with is_subobject=True
                                         system   <-- created as normal

        For consistency, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.

        :param api: The Cobbler API object which is used for resolving information.
        :param is_subobject: See above extensive description.
        """
        self._parent = ''
        self._depth = 0.0
        self._children = {}
        self._ctime = 0
        self._mtime = 0.0
        self._uid = uuid.uuid4().hex
        self._name = ""
        self._comment = ""
        self._kernel_options = {}
        self._kernel_options_post = {}
        self._autoinstall_meta = {}
        self._fetchable_files = {}
        self._boot_files = {}
        self._template_files = {}
        self._last_cached_mtime = 0
        self._owners = []
        self._cached_dict = ""
        self._mgmt_classes = []
        self._mgmt_parameters = {}
        self._conceptual_parent = None
        self._is_subobject = is_subobject

        self.logger = logging.getLogger()
        self.api = api

    def __eq__(self, other):
        """
        Comparison based on the uid for our items.

        :param other: The other Item to compare.
        :return: True if uid is equal, otherwise false.
        """
        if isinstance(other, Item):
            return self._uid == other.uid
        return False

    @property
    def uid(self) -> str:
        """
        The uid is the internal unique representation of a Cobbler object. It should never be used twice, even after an
        object was deleted.

        :return:
        """
        return self._uid

    @uid.setter
    def uid(self, uid: str):
        """
        Setter for the uid of the item.

        :param uid: The new uid.
        """
        self._uid = uid

    @property
    def ctime(self):
        """
        TODO

        :return:
        """
        return self._ctime

    @ctime.setter
    def ctime(self, value):
        """
        TODO

        :param value:
        :return:
        """
        self._ctime = value

    @property
    def name(self):
        """
        The objects name.

        :return: The name of the object
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """
        The objects name.

        :param name: object name string
        """
        if not isinstance(name, str):
            raise TypeError("name must of be type str")
        if not RE_OBJECT_NAME.match(name):
            raise ValueError("Invalid characters in name: '%s'" % name)
        self._name = name

    @property
    def comment(self) -> str:
        """
        For every object you are able to set a unique comment which will be persisted on the object.

        :return: The comment or an emtpy string.
        """
        return self._comment

    @comment.setter
    def comment(self, comment: str):
        """
        Setter for the comment of the item.

        :param comment: The new comment. If ``None`` the comment will be set to an emtpy string.
        """
        self._comment = comment

    @property
    def owners(self):
        """
        TODO

        :return:
        """
        return self._owners

    @owners.setter
    def owners(self, owners: list):
        """
        TODO

        :param owners:
        :return:
        """
        self._owners = utils.input_string_or_list(owners)

    @property
    def kernel_options(self) -> dict:
        """
        TODO

        :return:
        """
        return self._kernel_options

    @kernel_options.setter
    def kernel_options(self, options):
        """
        Kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        :param options: The new kernel options as a space delimited list.
        :raises CX
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise ValueError("invalid kernel options")
        else:
            self._kernel_options = value

    @property
    def kernel_options_post(self) -> dict:
        """
        TODO

        :return:
        """
        return self._kernel_options_post

    @kernel_options_post.setter
    def kernel_options_post(self, options):
        """
        Post kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        :param options: The new kernel options as a space delimited list.
        :raises CX
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise ValueError("invalid post kernel options")
        else:
            self._kernel_options_post = value

    @property
    def autoinstall_meta(self) -> dict:
        """
        TODO

        :return:
        """
        return self._autoinstall_meta

    @autoinstall_meta.setter
    def autoinstall_meta(self, options):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system to preprocess automatic installation template files.

        :param options: The new options for the automatic installation meta options.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise ValueError("invalid options given for autoinstall meta")
        else:
            self._autoinstall_meta = value

    @property
    def mgmt_classes(self):
        """
        TODO

        :return:
        """
        return self._mgmt_classes

    @mgmt_classes.setter
    def mgmt_classes(self, mgmt_classes):
        """
        Assigns a list of configuration management classes that can be assigned to any object, such as those used by
        Puppet's external_nodes feature.

        :param mgmt_classes: The new options for the management classes of an item.
        """
        mgmt_classes_split = utils.input_string_or_list(mgmt_classes)
        self._mgmt_classes = utils.input_string_or_list(mgmt_classes_split)

    @property
    def mgmt_parameters(self):
        """
        TODO

        :return:
        """
        return self._mgmt_parameters

    @mgmt_parameters.setter
    def mgmt_parameters(self, mgmt_parameters: Union[str, dict]):
        """
        A YAML string which can be assigned to any object, this is used by Puppet's external_nodes feature.

        :param mgmt_parameters: The management parameters for an item.
        :raises TypeError: In case the parsed yaml isn't of type dict afterwards.
        """
        if not isinstance(mgmt_parameters, (str, dict)):
            raise TypeError("mgmt_parameters must be of type str or dict")
        if isinstance(mgmt_parameters, str):
            if mgmt_parameters == enums.VALUE_INHERITED:
                self._mgmt_parameters = enums.VALUE_INHERITED
            else:
                mgmt_parameters = yaml.safe_load(mgmt_parameters)
                if not isinstance(mgmt_parameters, dict):
                    raise TypeError("Input YAML in Puppet Parameter field must evaluate to a dictionary.")
        self._mgmt_parameters = mgmt_parameters

    @property
    def template_files(self) -> dict:
        """
        TODO

        :return:
        """
        return self._template_files

    @template_files.setter
    def template_files(self, template_files: dict):
        """
        A comma seperated list of source=destination templates that should be generated during a sync.

        :param template_files: The new value for the template files which are used for the item.
        :return: False if this does not succeed.
        """
        (success, value) = utils.input_string_or_dict(template_files, allow_multiples=False)
        if not success:
            raise ValueError("template_files should be of type dict")
        else:
            self._template_files = value

    @property
    def boot_files(self):
        """
        TODO

        :return:
        """
        return self._boot_files

    @boot_files.setter
    def boot_files(self, boot_files: dict):
        """
        A comma separated list of req_name=source_file_path that should be fetchable via tftp.

        :param boot_files: The new value for the boot files used by the item.
        :return: False if this does not succeed.
        """
        if not isinstance(boot_files, dict):
            raise TypeError("boot_files needs to be of type list")
        self._boot_files = boot_files

    @property
    def fetchable_files(self):
        """
        TODO

        :return:
        """
        return self._fetchable_files

    @fetchable_files.setter
    def fetchable_files(self, fetchable_files):
        """
        A comma seperated list of virt_name=path_to_template that should be fetchable via tftp or a webserver

        :param fetchable_files: Files which will be made available to external users.
        """
        (success, value) = utils.input_string_or_dict(fetchable_files, allow_multiples=False)
        if not success:
            raise TypeError("fetchable_files were handed wrong values")
        else:
            self._fetchable_files = value

    @property
    def depth(self) -> float:
        """
        TODO

        :return:
        """
        return self._depth

    @depth.setter
    def depth(self, depth: float):
        """
        Setter for depth.

        :param depth: The new value for depth.
        """
        if not isinstance(depth, float):
            raise TypeError("depth needs to be of type float")
        self._depth = depth

    @property
    def mtime(self) -> float:
        """
        TODO

        :return:
        """
        return self._mtime

    @mtime.setter
    def mtime(self, mtime: float):
        """
        Setter for the modification time of the object.

        :param mtime: The new modification time.
        """
        if not isinstance(mtime, float):
            raise TypeError("mtime needs to be of type float")
        self._mtime = mtime

    @property
    def parent(self):
        """
        TODO

        :return:
        """
        return None

    @parent.setter
    def parent(self, parent: str):
        """
        Set the parent object for this object.

        :param parent: The new parent object. This needs to be a descendant in the logical inheritance chain.
        """
        pass

    @property
    def children(self) -> dict:
        """
        TODO

        :return:
        """
        return self._children

    @children.setter
    def children(self, value: dict):
        """
        TODO

        :param value:
        """
        if not isinstance(value, dict):
            raise TypeError("children needs to be of type dict")
        self._children = value

    def get_children(self, sort_list: bool = False) -> list:
        """
        TODO

        :return:
        """
        keys = list(self._children.keys())
        if sort_list:
            keys.sort()
        results = []
        for k in keys:
            results.append(self.children[k])
        return results

    @property
    def descendants(self) -> list:
        """
        Get objects that depend on this object, i.e. those that would be affected by a cascading delete, etc.

        :return: This is a list of all descendants. May be empty if none exist.
        """
        results = []
        kids = self.children
        for kid in kids:
            grandkids = kid.descendants
            results.extend(grandkids)
        return results

    @property
    def is_subobject(self) -> bool:
        """
        TODO

        :return:
        """
        return self._is_subobject

    @is_subobject.setter
    def is_subobject(self, value: bool):
        """
        TODO

        :param value:
        """
        self._is_subobject = value

    def get_conceptual_parent(self):
        """
        The parent may just be a superclass for something like a subprofile. Get the first parent of a different type.

        :return: The first item which is conceptually not from the same type.
        """
        mtype = type(self)
        parent = self.parent
        while parent is not None:
            ptype = type(parent)
            if mtype != ptype:
                self._conceptual_parent = parent
                return parent
            parent = parent.parent
        return None

    def sort_key(self, sort_fields: list = None):
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
                if value is not None:  # FIXME: new?
                    return False

        if value is None:
            return True
        else:
            return self.__find_compare(value, data[key])

    def dump_vars(self, format: bool = True):
        """
        Dump all variables.

        :param format: Whether to format the output or not.
        :return: The raw or formatted data.
        """
        raw = utils.blender(self.api, False, self)
        if format:
            return pprint.pformat(raw)
        else:
            return raw

    def check_if_valid(self):
        """
        Raise exceptions if the object state is inconsistent

        :raises CX
        """
        if not self.name:
            raise CX("Name is required")

    def make_clone(self):
        """
        Must be defined in any subclass
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @staticmethod
    def _remove_depreacted_dict_keys(dictionary: dict):
        """
        This method does remove keys which should not be deserialized and are only there for API compability in
        ``to_dict()``.

        :param dictionary: The dict to update
        """
        if "ks_meta" in dictionary:
            dictionary.pop("ks_meta")
        if "kickstart" in dictionary:
            dictionary.pop("kickstart")

    def from_dict(self, dictionary: dict):
        """
        Modify this object to take on values in ``dictionary``.

        :param dictionary: This should contain all values which should be updated.
        """
        result = dictionary.copy()
        for key in dictionary:
            lowered_key = key.lower()
            if hasattr(self, "_" + lowered_key):
                setattr(self, lowered_key, dictionary[key])
                result.pop(key)
        if len(result) > 0:
            raise KeyError("The following keys supplied could not be set: %s" % dictionary.keys())

    def to_dict(self) -> dict:
        """
        This converts everything in this object to a dictionary.

        :return: A dictionary with all values present in this object.
        """
        value = Item.get_from_cache(self)
        if value is None:
            value = {}
            for key in self.__dict__:
                if key.startswith("_") and not key.startswith("__"):
                    if key in ("_conceptual_parent", "_last_cached_mtime", "_cached_dict", "_supported_boot_loaders"):
                        continue
                    new_key = key[1:].lower()
                    if isinstance(self.__dict__[key], enum.Enum):
                        value[new_key] = self.__dict__[key].value
                    elif new_key == "interfaces":
                        # This is the special interfaces dict. Lets fix it before it gets to the normal process.
                        serialized_interfaces = {}
                        interfaces = self.__dict__[key]
                        for interface_key in interfaces:
                            serialized_interfaces[interface_key] = interfaces[interface_key].to_dict()
                        value[new_key] = serialized_interfaces
                    elif isinstance(self.__dict__[key], (list, dict)):
                        value[new_key] = copy.deepcopy(self.__dict__[key])
                    else:
                        value[new_key] = self.__dict__[key]
        self.set_cache(self, value)
        if "autoinstall" in value:
            value.update({"kickstart": value["autoinstall"]})
        if "autoinstall_meta" in value:
            value.update({"ks_meta": value["autoinstall_meta"]})
        return value
