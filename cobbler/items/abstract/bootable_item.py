"""
Cobbler module that contains the code for a generic Cobbler item.

Changelog:

V3.4.0 (unreleased):
    * Renamed to BootableItem
    * (Re-)Added Cache implementation with the following new methods and properties:
        * ``cache``
        * ``inmemory``
        * ``clean_cache()``
    * Overhauled the parent/child system:
        * ``children`` is now inside ``item.py``.
        * ``tree_walk()`` was added.
        * ``logical_parent`` was added.
        * ``get_parent()`` was added which returns the internal reference that is used to return the object of the
          ``parent`` property.
    * Removed:
        * mgmt_classes
        * mgmt_parameters
        * last_cached_mtime
        * fetchable_files
        * boot_files
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Added:
        * ``grab_tree``
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``depth``: int
        * ``comment``: str
        * ``owners``: Union[list, str]
        * ``mgmt_classes``: Union[list, str]
        * ``mgmt_classes``: Union[dict, str]
        * ``conceptual_parent``: Union[distro, profile]
    * Removed:
        * collection_mgr: collection_mgr
        * Remove unreliable caching:
            * ``get_from_cache()``
            * ``set_cache()``
            * ``remove_from_cache()``
    * Changed:
        * Constructor: Takes an instance of ``CobblerAPI`` instead of ``CollectionManager``.
        * ``children``: dict -> list
        * ``ctime``: int -> float
        * ``mtime``: int -> float
        * ``uid``: str
        * ``kernel_options``: dict -> Union[dict, str]
        * ``kernel_options_post``: dict -> Union[dict, str]
        * ``autoinstall_meta``: dict -> Union[dict, str]
        * ``fetchable_files``: dict -> Union[dict, str]
        * ``boot_files``: dict -> Union[dict, str]
V3.2.2:
    * No changes
V3.2.1:
    * No changes
V3.2.0:
    * No changes
V3.1.2:
    * No changes
V3.1.1:
    * No changes
V3.1.0:
    * No changes
V3.0.1:
    * No changes
V3.0.0:
    * Added:
        * ``collection_mgr``: collection_mgr
        * ``kernel_options``: dict
        * ``kernel_options_post``: dict
        * ``autoinstall_meta``: dict
        * ``fetchable_files``: dict
        * ``boot_files``: dict
        * ``template_files``: dict
        * ``name``: str
        * ``last_cached_mtime``: int
    * Changed:
        * Rename: ``cached_datastruct`` -> ``cached_dict``
    * Removed:
        * ``config``
V2.8.5:
    * Added:
        * ``config``: ?
        * ``settings``: settings
        * ``is_subobject``: bool
        * ``parent``: Union[distro, profile]
        * ``children``: dict
        * ``log_func``: collection_mgr.api.log
        * ``ctime``: int
        * ``mtime``: int
        * ``uid``: str
        * ``last_cached_mtime``: int
        * ``cached_datastruct``: str
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import pprint
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union

from cobbler import enums, utils
from cobbler.decorator import InheritableDictProperty, InheritableProperty, LazyProperty
from cobbler.items.abstract.inheritable_item import InheritableItem
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


T = TypeVar("T")


class BootableItem(InheritableItem, ABC):
    """
    A BootableItem is a serializable thing that can appear in a Collection
    """

    # Constants
    TYPE_NAME = "bootable_abstract"
    COLLECTION_TYPE = "bootable_abstract"

    def __init__(
        self, api: "CobblerAPI", *args: Any, is_subobject: bool = False, **kwargs: Any
    ):
        """
        Constructor. This is a legacy class that will be phased out with the 3.4.0 release.

        :param api: The Cobbler API object which is used for resolving information.
        :param is_subobject: See above extensive description.
        """
        super().__init__(api, *args, **kwargs)

        self._kernel_options: Union[Dict[Any, Any], str] = {}
        self._kernel_options_post: Union[Dict[Any, Any], str] = {}
        self._autoinstall_meta: Union[Dict[Any, Any], str] = {}
        self._template_files: Dict[str, str] = {}
        self._inmemory = True

        if len(kwargs) > 0:
            kwargs.update({"is_subobject": is_subobject})
            self.from_dict(kwargs)

        if not self._has_initialized:
            self._has_initialized = True

    def __setattr__(self, name: str, value: Any):
        """
        Intercepting an attempt to assign a value to an attribute.

        :name: The attribute name.
        :value: The attribute value.
        """
        if (
            BootableItem._is_dict_key(name)
            and self._has_initialized
            and hasattr(self, name)
            and value != getattr(self, name)
        ):
            self.clean_cache(name)
        super().__setattr__(name, value)

    def __common_resolve(self, property_name: str):
        settings_name = property_name
        if property_name.startswith("proxy_url_"):
            property_name = "proxy"
        if property_name == "owners":
            settings_name = "default_ownership"
        attribute = "_" + property_name

        return getattr(self, attribute), settings_name

    def __resolve_get_parent_or_settings(self, property_name: str, settings_name: str):
        settings = self.api.settings()
        conceptual_parent = self.get_conceptual_parent()

        if hasattr(self.parent, property_name):
            return getattr(self.parent, property_name)
        elif hasattr(conceptual_parent, property_name):
            return getattr(conceptual_parent, property_name)
        elif hasattr(settings, settings_name):
            return getattr(settings, settings_name)
        elif hasattr(settings, f"default_{settings_name}"):
            return getattr(settings, f"default_{settings_name}")
        return None

    def _resolve(self, property_name: str) -> Any:
        """
        Resolve the ``property_name`` value in the object tree. This function traverses the tree from the object to its
        topmost parent and returns the first value that is not inherited. If the tree does not contain a value the
        settings are consulted.

        :param property_name: The property name to resolve.
        :raises AttributeError: In case one of the objects try to inherit from a parent that does not have
                                ``property_name``.
        :return: The resolved value.
        """
        attribute_value, settings_name = self.__common_resolve(property_name)

        if attribute_value == enums.VALUE_INHERITED:
            possible_return = self.__resolve_get_parent_or_settings(
                property_name, settings_name
            )
            if possible_return is not None:
                return possible_return
            raise AttributeError(
                f'{type(self)} "{self.name}" inherits property "{property_name}", but neither its parent nor'
                f" settings have it"
            )

        return attribute_value

    def _resolve_enum(
        self, property_name: str, enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        """
        See :meth:`~cobbler.items.abstract.bootable_item.BootableItem._resolve`
        """
        attribute_value, settings_name = self.__common_resolve(property_name)
        unwrapped_value = getattr(attribute_value, "value", "")
        if unwrapped_value == enums.VALUE_INHERITED:
            possible_return = self.__resolve_get_parent_or_settings(
                unwrapped_value, settings_name
            )
            if possible_return is not None:
                return enum_type(possible_return)
            raise AttributeError(
                f'{type(self)} "{self.name}" inherits property "{property_name}", but neither its parent nor'
                f" settings have it"
            )

        return attribute_value

    def _resolve_dict(self, property_name: str) -> Dict[str, Any]:
        """
        Merge the ``property_name`` dictionary of the object with the ``property_name`` of all its parents. The value
        of the child takes precedence over the value of the parent.

        :param property_name: The property name to resolve.
        :return: The merged dictionary.
        :raises AttributeError: In case the the the object had no attribute with the name :py:property_name: .
        """
        attribute = "_" + property_name

        attribute_value = getattr(self, attribute)
        settings = self.api.settings()

        merged_dict: Dict[str, Any] = {}

        conceptual_parent = self.get_conceptual_parent()
        if hasattr(conceptual_parent, property_name):
            merged_dict.update(getattr(conceptual_parent, property_name))
        elif hasattr(settings, property_name):
            merged_dict.update(getattr(settings, property_name))

        if attribute_value != enums.VALUE_INHERITED:
            merged_dict.update(attribute_value)

        utils.dict_annihilate(merged_dict)
        return merged_dict

    def _deduplicate_dict(
        self, property_name: str, value: Dict[str, T]
    ) -> Dict[str, T]:
        """
        Filter out the key:value pair may come from parent and global settings.
        Note: we do not know exactly which resolver does key:value belongs to, what we did is just deduplicate them.

        :param property_name: The property name to deduplicated.
        :param value: The value that should be deduplicated.
        :returns: The deduplicated dictionary
        """
        _, settings_name = self.__common_resolve(property_name)
        settings = self.api.settings()
        conceptual_parent = self.get_conceptual_parent()

        if hasattr(self.parent, property_name):
            parent_value = getattr(self.parent, property_name)
        elif hasattr(conceptual_parent, property_name):
            parent_value = getattr(conceptual_parent, property_name)
        elif hasattr(settings, settings_name):
            parent_value = getattr(settings, settings_name)
        elif hasattr(settings, f"default_{settings_name}"):
            parent_value = getattr(settings, f"default_{settings_name}")
        else:
            parent_value = {}

        # Because we use getattr pyright cannot correctly check this.
        for key in parent_value:  # type: ignore
            if key in value and parent_value[key] == value[key]:  # type: ignore
                value.pop(key)  # type: ignore

        return value

    @InheritableDictProperty
    def kernel_options(self) -> Dict[Any, Any]:
        """
        Kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The parsed kernel options.
        :setter: The new kernel options as a space delimited list. May raise ``ValueError`` in case of parsing problems.
        """
        return self._resolve_dict("kernel_options")

    @kernel_options.setter  # type: ignore[no-redef]
    def kernel_options(self, options: Dict[str, Any]):
        """
        Setter for ``kernel_options``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the values set could not be parsed successfully.
        """
        try:
            value = input_converters.input_string_or_dict(options, allow_multiples=True)
            if value == enums.VALUE_INHERITED:
                self._kernel_options = enums.VALUE_INHERITED
                return
            # pyright doesn't understand that the only valid str return value is this constant.
            self._kernel_options = self._deduplicate_dict("kernel_options", value)  # type: ignore
        except TypeError as error:
            raise TypeError("invalid kernel value") from error

    @InheritableDictProperty
    def kernel_options_post(self) -> Dict[str, Any]:
        """
        Post kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The dictionary with the parsed values.
        :setter: Accepts str in above mentioned format or directly a dict.
        """
        return self._resolve_dict("kernel_options_post")

    @kernel_options_post.setter  # type: ignore[no-redef]
    def kernel_options_post(self, options: Union[Dict[Any, Any], str]) -> None:
        """
        Setter for ``kernel_options_post``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the options could not be split successfully.
        """
        try:
            self._kernel_options_post = input_converters.input_string_or_dict(
                options, allow_multiples=True
            )
        except TypeError as error:
            raise TypeError("invalid post kernel options") from error

    @InheritableDictProperty
    def autoinstall_meta(self) -> Dict[Any, Any]:
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system to preprocess automatic installation template files.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The metadata or an empty dict.
        :setter: Accepts anything which can be split by :meth:`~cobbler.utils.input_converters.input_string_or_dict`.
        """
        return self._resolve_dict("autoinstall_meta")

    @autoinstall_meta.setter  # type: ignore[no-redef]
    def autoinstall_meta(self, options: Dict[Any, Any]):
        """
        Setter for the ``autoinstall_meta`` property.

        :param options: The new options for the automatic installation meta options.
        :raises ValueError: If splitting the value does not succeed.
        """
        value = input_converters.input_string_or_dict(options, allow_multiples=True)
        if value == enums.VALUE_INHERITED:
            self._autoinstall_meta = enums.VALUE_INHERITED
            return
        # pyright doesn't understand that the only valid str return value is this constant.
        self._autoinstall_meta = self._deduplicate_dict("autoinstall_meta", value)  # type: ignore

    @LazyProperty
    def template_files(self) -> Dict[str, str]:
        """
        File mappings for built-in configuration management. The keys are the template source files and the value is the
        destination. The destination must be inside the bootloc (most of the time TFTP server directory).

        This property took over the duties of boot_files additionaly. During signature import the values of "boot_files"
        will be added to "template_files".

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by
                 :meth:`~cobbler.utils.input_converters.input_string_or_dict`. Raises ``TypeError`` otherwise.
        """
        return self._template_files

    @template_files.setter
    def template_files(self, template_files: Union[str, Dict[str, str]]) -> None:
        """
        A comma seperated list of source=destination templates that should be generated during a sync.

        :param template_files: The new value for the template files which are used for the item.
        :raises ValueError: In case the conversion from non dict values was not successful.
        """
        try:
            self._template_files = input_converters.input_string_or_dict_no_inherit(
                template_files, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid template files specified") from error

    def dump_vars(
        self, formatted_output: bool = True, remove_dicts: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        Dump all variables.

        :param formatted_output: Whether to format the output or not.
        :param remove_dicts: If True the dictionaries will be put into str form.
        :return: The raw or formatted data.
        """
        raw = utils.blender(self.api, remove_dicts, self)  # type: ignore
        if formatted_output:
            return pprint.pformat(raw)
        return raw

    def deserialize(self) -> None:
        """
        Deserializes the object itself and, if necessary, recursively all the objects it depends on.
        """

        def deserialize_ancestor(ancestor_item_type: str, ancestor_name: str):
            if ancestor_name not in {"", enums.VALUE_INHERITED}:
                ancestor = self.api.get_items(ancestor_item_type).get(ancestor_name)
                if ancestor is not None and not ancestor.inmemory:
                    ancestor.deserialize()

        if not self._has_initialized:
            return

        item_dict = self.api.deserialize_item(self)
        if item_dict["inmemory"]:
            for (
                ancestor_item_type,
                ancestor_deps,
            ) in InheritableItem.TYPE_DEPENDENCIES.items():
                for ancestor_dep in ancestor_deps:
                    if self.TYPE_NAME == ancestor_dep.dependant_item_type:
                        attr_name = ancestor_dep.dependant_type_attribute
                        if attr_name not in item_dict:
                            continue
                        attr_val = item_dict[attr_name]
                        if isinstance(attr_val, str):
                            deserialize_ancestor(ancestor_item_type, attr_val)
                        elif isinstance(attr_val, list):  # type: ignore
                            attr_val: List[str]
                            for ancestor_name in attr_val:
                                deserialize_ancestor(ancestor_item_type, ancestor_name)
        self.from_dict(item_dict)

    def _clean_dict_cache(self, name: Optional[str]):
        """
        Clearing the Item dict cache.

        :param name: The name of Item attribute or None.
        """
        if not self.api.settings().cache_enabled:
            return

        if name is not None and self._inmemory:
            attr = getattr(type(self), name[1:])
            if (
                isinstance(attr, (InheritableProperty, InheritableDictProperty))
                and self.api.get_items(self.COLLECTION_TYPE).get(self.name) is not None
            ):
                # Invalidating "resolved" caches
                for dep_item in self.tree_walk(name):
                    dep_item.cache.set_dict_cache(None, True)

        # Invalidating the cache of the object itself.
        self.cache.clean_dict_cache()
