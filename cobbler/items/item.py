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
from typing import Any, Dict, List, Tuple, Type, Union

import yaml

from cobbler import utils, enums
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, InheritableDictProperty, LazyProperty

RE_OBJECT_NAME = re.compile(r'[a-zA-Z0-9_\-.:]*$')


class Item:
    """
    An Item is a serializable thing that can appear in a Collection
    """
    # Constants
    TYPE_NAME = "generic"
    COLLECTION_TYPE = "generic"

    # Item types dependencies.
    # Used to determine descendants and cache invalidation.
    # Format: {"Item Type": [("Dependent Item Type", "Dependent Type attribute"), ..], [..]}
    TYPE_DEPENDENCIES: Dict[str, List[Tuple[str, str]]] = {
        "package": [
            ("mgmtclass", "packages"),
        ],
        "file": [
            ("mgmtclass", "files"),
            ("image", "file"),
        ],
        "mgmtclass": [
            ("distro", "mgmt_classes"),
            ("profile", "mgmt_classes"),
            ("system", "mgmt_classes"),
        ],
        "repo": [
            ("profile", "repos"),
        ],
        "distro": [
            ("profile", "distro"),
        ],
        "menu": [
            ("menu", "parent"),
            ("image", "menu"),
            ("profile", "menu"),
        ],
        "profile": [
            ("profile", "parent"),
            ("system", "profile"),
        ],
        "image": [
            ("system", "image"),
        ],
        "system": [],
    }


    @classmethod
    def __find_compare(cls, from_search: Union[str, list, dict, bool], from_obj: Union[str, list, dict, bool]):
        """
        Only one of the two parameters shall be given in this method. If you give both ``from_obj`` will be preferred.

        :param from_search: Tries to parse this str in the format as a search result string.
        :param from_obj: Tries to parse this str in the format of an obj str.
        :return: True if the comparison succeeded, False otherwise.
        :raises TypeError: In case the type of one of the two variables is wrong or could not be converted
                           intelligently.
        """
        if isinstance(from_obj, str):
            # FIXME: fnmatch is only used for string to string comparisons which should cover most major usage, if
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
                    from_search = utils.input_string_or_dict(
                        from_search, allow_multiples=True
                    )
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

    def __init__(self, api, is_subobject: bool = False, *args, **kwargs):
        """
        Constructor.  Requires a back reference to the CobblerAPI object.

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
        # Prevent attempts to deserialize again before the object is initialized.
        self._has_initialized = False

        self._parent = ''
        self._depth = 0
        self._children = []
        self._ctime = 0.0
        self._mtime = 0.0
        self._uid = uuid.uuid4().hex
        self._name = ""
        self._comment = ""
        self._kernel_options: Union[dict, str] = {}
        self._kernel_options_post: Union[dict, str] = {}
        self._autoinstall_meta: Union[dict, str] = {}
        self._fetchable_files: Union[dict, str] = {}
        self._boot_files: Union[dict, str] = {}
        self._template_files = {}
        self._last_cached_mtime = 0
        self._owners: Union[list, str] = enums.VALUE_INHERITED
        self._cached_dict = ""
        self._mgmt_classes: Union[list, str] = []
        self._mgmt_parameters: Union[dict, str] = {}
        self._conceptual_parent = None
        self._is_subobject = is_subobject
        self._inmemory: bool = kwargs.get("inmemory", True)

        self.logger = logging.getLogger()
        self.api = api

        if not self._has_initialized:
            self._has_initialized = True

    def __eq__(self, other):
        """
        Comparison based on the uid for our items.

        :param other: The other Item to compare.
        :return: True if uid is equal, otherwise false.
        """
        if isinstance(other, Item):
            return self._uid == other.uid
        return False

    def _resolve(self, property_name: str) -> Any:
        """
        Resolve the ``property_name`` value in the object tree. This function traverses the tree from the object to its
        topmost parent and returns the first value that is not inherited. If the the tree does not contain a value the
        settings are consulted.

        :param property_name: The property name to resolve.
        :raises AttributeError: In case one of the objects try to inherit from a parent that does not have
                                ``property_name``.
        :return: The resolved value.
        """
        settings_name = property_name
        if property_name.startswith("proxy_url_"):
            property_name = "proxy"
        if property_name == "owners":
            settings_name = "default_ownership"
        attribute = "_" + property_name

        if not hasattr(self, attribute):
            raise AttributeError("%s \"%s\" does not have property \"%s\"" % (type(self), self.name, property_name))

        attribute_value = getattr(self, attribute)
        settings = self.api.settings()

        if attribute_value == enums.VALUE_INHERITED:
            if self.parent is not None and hasattr(self.parent, property_name):
                return getattr(self.parent, property_name)
            elif hasattr(settings, settings_name):
                return getattr(settings, settings_name)
            elif hasattr(settings, "default_%s" % settings_name):
                return getattr(settings, "default_%s" % settings_name)
            else:
                AttributeError(
                    '%s "%s" inherits property "%s", but neither its parent nor settings have it'
                    % (type(self), self.name, property_name)
                )

        return attribute_value

    def _resolve_enum(
            self, property_name: str, enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        """
        See :meth:`~cobbler.items.item.Item._resolve`
        """
        settings_name = property_name
        attribute = "_" + property_name

        if not hasattr(self, attribute):
            raise AttributeError(
                '%s "%s" does not have property "%s"'
                % (type(self), self.name, property_name)
            )

        attribute_value = getattr(self, attribute)
        settings = self.api.settings()

        if (
                isinstance(attribute_value, enums.ConvertableEnum)
                and attribute_value.value == enums.VALUE_INHERITED
        ):
            if self.parent is not None and hasattr(self.parent, property_name):
                return getattr(self.parent, property_name)
            elif hasattr(settings, settings_name):
                return enum_type.to_enum(getattr(settings, settings_name))
            elif hasattr(settings, "default_%s" % settings_name):
                return enum_type.to_enum(
                    getattr(settings, "default_%s" % settings_name)
                )
            else:
                AttributeError("%s \"%s\" inherits property \"%s\", but neither its parent nor settings have it"
                               % (type(self), self.name, property_name))

        return attribute_value

    def _resolve_dict(self, property_name: str) -> dict:
        """
        Merge the ``property_name`` dictionary of the object with the ``property_name`` of all its parents. The value
        of the child takes precedence over the value of the parent.

        :param property_name: The property name to resolve.
        :return: The merged dictionary.
        :raises AttributeError: In case the the the object had no attribute with the name :py:property_name: .
        """
        attribute = "_" + property_name

        if not hasattr(self, attribute):
            raise AttributeError("%s \"%s\" does not have property \"%s\""
                                 % (type(self), self.name, property_name))

        attribute_value = getattr(self, attribute)
        settings = self.api.settings()

        merged_dict = {}

        if self.parent is not None and hasattr(self.parent, property_name):
            merged_dict.update(getattr(self.parent, property_name))
        elif hasattr(settings, property_name):
            merged_dict.update(getattr(settings, property_name))

        if attribute_value != enums.VALUE_INHERITED:
            merged_dict.update(attribute_value)

        utils.dict_annihilate(merged_dict)

        return merged_dict

    @property
    def uid(self) -> str:
        """
        The uid is the internal unique representation of a Cobbler object. It should never be used twice, even after an
        object was deleted.

        :getter: The uid for the item. Should be unique across a running Cobbler instance.
        :setter: The new uid for the object. Should only be used by the Cobbler Item Factory.
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
    def ctime(self) -> float:
        """
        Property which represents the creation time of the object.

        :getter: The float which can be passed to Python time stdlib.
        :setter: Should only be used by the Cobbler Item Factory.
        """
        return self._ctime

    @ctime.setter
    def ctime(self, ctime: float):
        """
        Setter for the ctime property.

        :param ctime: The time the object was created.
        :raises TypeError: In case ``ctime`` was not of type float.
        """
        if not isinstance(ctime, float):
            raise TypeError("ctime needs to be of type float")
        self._ctime = ctime

    @property
    def name(self):
        """
        Property which represents the objects name.

        :getter: The name of the object.
        :setter: Updating this has broad implications. Please try to use the ``rename()`` functionality from the
                 corresponding collection.
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """
        The objects name.

        :param name: object name string
        :raises TypeError: In case ``name`` was not of type str.
        :raises ValueError: In case there were disallowed characters in the name.
        """
        if not isinstance(name, str):
            raise TypeError("name must of be type str")
        if not RE_OBJECT_NAME.match(name):
            raise ValueError("Invalid characters in name: '%s'" % name)
        self._name = name

    @LazyProperty
    def comment(self) -> str:
        """
        For every object you are able to set a unique comment which will be persisted on the object.

        :getter: The comment or an emtpy string.
        :setter: The new comment for the item.
        """
        return self._comment

    @comment.setter
    def comment(self, comment: str):
        """
        Setter for the comment of the item.

        :param comment: The new comment. If ``None`` the comment will be set to an emtpy string.
        """
        self._comment = comment

    @InheritableProperty
    def owners(self) -> list:
        """
        This is a feature which is related to the ownership module of Cobbler which gives only specific people access
        to specific records. Otherwise this is just a cosmetic feature to allow assigning records to specific users.

        .. warning:: This is never validated against a list of existing users. Thus you can lock yourself out of a
                     record.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Return the list of users which are currently assigned to the record.
        :setter: The list of people which should be new owners. May lock you out if you are using the ownership
                 authorization module.
        """
        return self._resolve("owners")

    @owners.setter
    def owners(self, owners: Union[str, list]):
        """
        Setter for the ``owners`` property.

        :param owners: The new list of owners. Will not be validated for existence.
        """
        if not isinstance(owners, (str, list)):
            raise TypeError("owners must be str or list!")
        self._owners = utils.input_string_or_list(owners)

    @InheritableDictProperty
    def kernel_options(self) -> dict:
        """
        Kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The parsed kernel options.
        :setter: The new kernel options as a space delimited list. May raise ``ValueError`` in case of parsing problems.
        """
        return self._resolve_dict("kernel_options")

    @kernel_options.setter
    def kernel_options(self, options):
        """
        Setter for ``kernel_options``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the values set could not be parsed successfully.
        """
        try:
            self._kernel_options = utils.input_string_or_dict(
                options, allow_multiples=True
            )
        except TypeError as e:
            raise TypeError("invalid kernel options") from e

    @InheritableDictProperty
    def kernel_options_post(self) -> dict:
        """
        Post kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The dictionary with the parsed values.
        :setter: Accepts str in above mentioned format or directly a dict.
        """
        return self._resolve_dict("kernel_options_post")

    @kernel_options_post.setter
    def kernel_options_post(self, options):
        """
        Setter for ``kernel_options_post``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the options could not be split successfully.
        """
        try:
            self._kernel_options_post = utils.input_string_or_dict(
                options, allow_multiples=True
            )
        except TypeError as e:
            raise TypeError("invalid post kernel options") from e

    @InheritableDictProperty
    def autoinstall_meta(self) -> dict:
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system to preprocess automatic installation template files.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The metadata or an empty dict.
        :setter: Accepts anything which can be split by :meth:`~cobbler.utils.input_string_or_dict`.
        """
        return self._resolve_dict("autoinstall_meta")

    @autoinstall_meta.setter
    def autoinstall_meta(self, options: dict):
        """
        Setter for the ``autoinstall_meta`` property.

        :param options: The new options for the automatic installation meta options.
        :raises ValueError: If splitting the value does not succeed.
        """
        value = utils.input_string_or_dict(options, allow_multiples=True)
        self._autoinstall_meta = value

    @InheritableProperty
    def mgmt_classes(self) -> list:
        """
        Assigns a list of configuration management classes that can be assigned to any object, such as those used by
        Puppet's external_nodes feature.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: An empty list or the list of mgmt_classes.
        :setter: Will split this according to :meth:`~cobbler.utils.input_string_or_list`.
        """
        return self._resolve("mgmt_classes")

    @mgmt_classes.setter
    def mgmt_classes(self, mgmt_classes: Union[list, str]):
        """
        Setter for the ``mgmt_classes`` property.

        :param mgmt_classes: The new options for the management classes of an item.
        """
        if not isinstance(mgmt_classes, (str, list)):
            raise TypeError("mgmt_classes has to be either str or list")
        self._mgmt_classes = utils.input_string_or_list(mgmt_classes)

    @InheritableDictProperty
    def mgmt_parameters(self) -> dict:
        """
        Parameters which will be handed to your management application (Must be a valid YAML dictionary)

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The mgmt_parameters or an empty dict.
        :setter: A YAML string which can be assigned to any object, this is used by Puppet's external_nodes feature.
        """
        return self._resolve_dict("mgmt_parameters")

    @mgmt_parameters.setter
    def mgmt_parameters(self, mgmt_parameters: Union[str, dict]):
        """
        A YAML string which can be assigned to any object, this is used by Puppet's external_nodes feature.

        :param mgmt_parameters: The management parameters for an item.
        :raises TypeError: In case the parsed YAML isn't of type dict afterwards.
        """
        if not isinstance(mgmt_parameters, (str, dict)):
            raise TypeError("mgmt_parameters must be of type str or dict")
        if isinstance(mgmt_parameters, str):
            if mgmt_parameters == enums.VALUE_INHERITED:
                self._mgmt_parameters = enums.VALUE_INHERITED
                return
            elif mgmt_parameters == "":
                self._mgmt_parameters = {}
                return
            else:
                mgmt_parameters = yaml.safe_load(mgmt_parameters)
                if not isinstance(mgmt_parameters, dict):
                    raise TypeError("Input YAML in Puppet Parameter field must evaluate to a dictionary.")
        self._mgmt_parameters = mgmt_parameters

    @LazyProperty
    def template_files(self) -> dict:
        """
        File mappings for built-in configuration management

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by :meth:`~cobbler.utils.input_string_or_dict`.
                 Raises ``TypeError`` otherwise.
        """
        return self._template_files

    @template_files.setter
    def template_files(self, template_files: dict):
        """
        A comma seperated list of source=destination templates that should be generated during a sync.

        :param template_files: The new value for the template files which are used for the item.
        :raises ValueError: In case the conversion from non dict values was not successful.
        """
        try:
            self._template_files = utils.input_string_or_dict(
                template_files, allow_multiples=False
            )
        except TypeError as e:
            raise TypeError("invalid template files specified") from e

    @LazyProperty
    def boot_files(self) -> dict:
        """
        Files copied into tftpboot beyond the kernel/initrd

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by :meth:`~cobbler.utils.input_string_or_dict`.
                 Raises ``TypeError`` otherwise.
        """
        return self._resolve_dict("boot_files")

    @boot_files.setter
    def boot_files(self, boot_files: dict):
        """
        A comma separated list of req_name=source_file_path that should be fetchable via tftp.

        :param boot_files: The new value for the boot files used by the item.
        """
        try:
            self._boot_files = utils.input_string_or_dict(
                boot_files, allow_multiples=False
            )
        except TypeError as e:
            raise TypeError("invalid boot files specified") from e

    @InheritableDictProperty
    def fetchable_files(self) -> dict:
        """
        A comma seperated list of ``virt_name=path_to_template`` that should be fetchable via tftp or a webserver

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by :meth:`~cobbler.utils.input_string_or_dict`.
                 Raises ``TypeError`` otherwise.
        """
        return self._resolve_dict("fetchable_files")

    @fetchable_files.setter
    def fetchable_files(self, fetchable_files: Union[str, dict]):
        """
        Setter for the fetchable files.

        :param fetchable_files: Files which will be made available to external users.
        """
        try:
            self._fetchable_files = utils.input_string_or_dict(
                fetchable_files, allow_multiples=False
            )
        except TypeError as e:
            raise TypeError("invalid fetchable files specified") from e

    @LazyProperty
    def depth(self) -> int:
        """
        This represents the logical depth of an object in the category of the same items. Important for the order of
        loading items from the disk and other related features where the alphabetical order is incorrect for sorting.

        :getter: The logical depth of the object.
        :setter: The new int for the logical object-depth.
        """
        return self._depth

    @depth.setter
    def depth(self, depth: int):
        """
        Setter for depth.

        :param depth: The new value for depth.
        """
        if not isinstance(depth, int):
            raise TypeError("depth needs to be of type int")
        self._depth = depth

    @property
    def mtime(self) -> float:
        """
        Represents the last modification time of the object via the API. This is not updated automagically.

        :getter: The float which can be fed into a Python time object.
        :setter: The new time something was edited via the API.
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

    @LazyProperty
    def parent(self):
        """
        This property contains the name of the logical parent of an object. In case there is not parent this return
        None.

        :getter: Returns the parent object or None if it can't be resolved via the Cobbler API.
        :setter: The name of the new logical parent.
        """
        return None

    @parent.setter
    def parent(self, parent: str):
        """
        Set the parent object for this object.

        :param parent: The new parent object. This needs to be a descendant in the logical inheritance chain.
        """

    @property
    def children(self) -> List[str]:
        """
        The list of logical children of any depth.

        :getter: An empty list in case of items which don't have logical children.
        :setter: Replace the list of children completely with the new provided one.
        """
        return []

    @children.setter
    def children(self, value):
        """
        This is an empty setter to not throw on setting it accidentally.

        :param value: The list with children names to replace the current one with.
        """
        self.logger.warning("Tried to set the children property on object \"%s\" without logical children.", self.name)

    def get_children(self, sort_list: bool = False) -> List[str]:
        """
        Get the list of children names.

        :param sort_list: If the list should be sorted alphabetically or not.
        :return: A copy of the list of children names.
        """
        result = copy.deepcopy(self.children)
        if sort_list:
            result.sort()
        return result

    @property
    def descendants(self) -> list:
        """
        Get objects that depend on this object, i.e. those that would be affected by a cascading delete, etc.

        .. note:: This is a read only property.

        :getter: This is a list of all descendants. May be empty if none exist.
        """
        results = []
        kids = self.children
        for kid in kids:
            # FIXME: Get kid objects
            grandkids = kid.descendants
            results.extend(grandkids)
        return results

    @LazyProperty
    def is_subobject(self) -> bool:
        """
        Weather the object is a subobject of another object or not.

        :getter: True in case the object is a subobject, False otherwise.
        :setter: Sets the value. If this is not a bool, this will raise a ``TypeError``.
        """
        return self._is_subobject

    @is_subobject.setter
    def is_subobject(self, value: bool):
        """
        Setter for the property ``is_subobject``.

        :param value: The boolean value whether this is a subobject or not.
        :raises TypeError: In case the value was not of type bool.
        """
        if not isinstance(value, bool):
            raise TypeError("Field is_subobject of object item needs to be of type bool!")
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

    def sort_key(self, sort_fields: list):
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
            if key in [
                "cnames",
                "connected_mode",
                "if_gateway",
                "ipv6_default_gateway",
                "ipv6_mtu",
                "ipv6_prefix",
                "ipv6_secondaries",
                "ipv6_static_routes",
                "management",
                "mtu",
                "static",
                "mac_address",
                "ip_address",
                "ipv6_address",
                "netmask",
                "virt_bridge",
                "dhcp_tag",
                "dns_name",
                "static_routes",
                "interface_type",
                "interface_master",
                "bonding_opts",
                "bridge_opts",
                "interface",
            ]:
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

    def dump_vars(
        self, formatted_output: bool = True, remove_dicts: bool = False
    ) -> Union[dict, str]:
        """
        Dump all variables.

        :param formatted_output: Whether to format the output or not.
        :param remove_dicts: If True the dictionaries will be put into str form.
        :return: The raw or formatted data.
        """
        raw = utils.blender(self.api, remove_dicts, self)
        if formatted_output:
            return pprint.pformat(raw)
        else:
            return raw

    def check_if_valid(self):
        """
        Raise exceptions if the object state is inconsistent.

        :raises CX: In case the name of the item is not set.
        """
        if not self.name:
            raise CX("Name is required")

    def make_clone(self):
        """
        Must be defined in any subclass
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: dict):
        """
        This method does remove keys which should not be deserialized and are only there for API compatibility in
        :meth:`~cobbler.items.item.Item.to_dict`.

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
        :raises AttributeError: In case during the process of setting a value for an attribute an error occurred.
        :raises KeyError: In case there were keys which could not be set in the item dictionary.
        """
        self._remove_depreacted_dict_keys(dictionary)
        if len(dictionary) == 0:
            return
        old_has_initialized = self._has_initialized
        self._has_initialized = False
        result = copy.deepcopy(dictionary)
        for key in dictionary:
            lowered_key = key.lower()
            # The following also works for child classes because self is a child class at this point and not only an
            # Item.
            if hasattr(self, "_" + lowered_key):
                try:
                    setattr(self, lowered_key, dictionary[key])
                except AttributeError as error:
                    raise AttributeError("Attribute \"%s\" could not be set!" % lowered_key) from error
                result.pop(key)
        self._has_initialized = old_has_initialized
        if len(result) > 0:
            raise KeyError("The following keys supplied could not be set: %s" % result.keys())

    def to_dict(self, resolved: bool = False) -> dict:
        """
        This converts everything in this object to a dictionary.

        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                     objects raw value.
        :return: A dictionary with all values present in this object.
        """
        if not self.inmemory:
            self.deserialize()
        value = {}
        keys_to_skip = ("_conceptual_parent", "_last_cached_mtime", "_cached_dict", "_supported_boot_loaders", "_inmemory")
        for key in self.__dict__:
            if key.startswith("_") and not key.startswith("__"):
                if key in keys_to_skip:
                    continue
                new_key = key[1:].lower()
                key_value = self.__dict__[key]
                if isinstance(key_value, enum.Enum):
                    value[new_key] = key_value.value
                elif new_key == "interfaces":
                    # This is the special interfaces dict. Lets fix it before it gets to the normal process.
                    serialized_interfaces = {}
                    interfaces = key_value
                    for interface_key in interfaces:
                        serialized_interfaces[interface_key] = interfaces[interface_key].to_dict(resolved=resolved)
                    value[new_key] = serialized_interfaces
                elif isinstance(key_value, list):
                    value[new_key] = copy.deepcopy(key_value)
                elif isinstance(key_value, dict):
                    if resolved:
                        value[new_key] = getattr(self, new_key)
                    else:
                        value[new_key] = copy.deepcopy(key_value)
                elif (
                    isinstance(key_value, str)
                    and key_value == enums.VALUE_INHERITED
                    and resolved
                ):
                    value[new_key] = getattr(self, key[1:])
                else:
                    value[new_key] = self.__dict__[key]
        if "autoinstall" in value:
            value.update({"kickstart": value["autoinstall"]})
        if "autoinstall_meta" in value:
            value.update({"ks_meta": value["autoinstall_meta"]})
        return value

    def serialize(self) -> dict:
        """
        This method is a proxy for :meth:`~cobbler.items.item.Item.to_dict` and contains additional logic for
        serialization to a persistent location.

        :return: The dictionary with the information for serialization.
        """
        keys_to_drop = ["kickstart", "ks_meta", "remote_grub_kernel", "remote_grub_initrd"]
        result = self.to_dict()
        for key in keys_to_drop:
            result.pop(key, "")
        return result

    def deserialize(self):
        """
        This is currently a proxy for :py:meth:`~cobbler.items.item.Item.from_dict` .
        """
        def deserialize_ancestor(ancestor_item_type: str, ancestor_name: str):
            if ancestor_name not in {"", enums.VALUE_INHERITED}:
                ancestor = self.api.get_items(ancestor_item_type).get(ancestor_name)
                if ancestor is not None and not ancestor.inmemory:
                    ancestor.deserialize()

        item_dict = self.api.deserialize_item(self)
        if item_dict["inmemory"]:
            for ancestor_item_type, ancestor_deps in Item.TYPE_DEPENDENCIES.items():
                for ancestor_dep in ancestor_deps:
                    if self.TYPE_NAME == ancestor_dep[0]:
                        attr_name = ancestor_dep[1]
                        if attr_name not in item_dict:
                            continue
                        attr_val = item_dict[attr_name]
                        if isinstance(attr_val, str):
                            deserialize_ancestor(ancestor_item_type, attr_val)
                        elif isinstance(attr_val, list):
                            for ancestor_name in attr_val:
                                deserialize_ancestor(ancestor_item_type, ancestor_name)
        
        self.from_dict(item_dict)

    def grab_tree(self) -> list:
        """
        Climb the tree and get every node.

        :return: The list of items with all parents from that object upwards the tree. Contains at least the item
                 itself and the settings of Cobbler.
        """
        results = [self]
        parent = self.parent
        while parent is not None:
            results.append(parent)
            parent = parent.parent
            # FIXME: Now get the object and check its existence
        results.append(self.api.settings())
        self.logger.debug(
            "grab_tree found %s children (including settings) of this object",
            len(results),
        )
        return results

    @property
    def inmemory(self) -> bool:
        r"""
        If set to ``false``, only the Item name is in memory. The rest of the Item's properties can be retrieved
        either on demand or as a result of the ``load_items`` background task.
        :getter: The inmemory for the item.
        :setter: The new inmemory value for the object. Should only be used by the Cobbler serializers.
        """
        return self._inmemory

    @inmemory.setter
    def inmemory(self, inmemory: bool):
        """
        Setter for the inmemory of the item.
        :param inmemory: The new inmemory value.
        """
        self._inmemory = inmemory
