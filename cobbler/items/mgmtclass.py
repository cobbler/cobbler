"""
Cobbler module that contains the code for a Cobbler mgmtclass object.

Changelog:

V3.4.0 (unreleased):
    * Changed:
        * ``from_dict()``: The method was moved to the base class (Item)
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``check_if_valid()``: The method was moved to the base class (Item)
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Moved to base class (Item):
        * ``ctime``: int
        * ``depth``: float
        * ``mtime``: int
        * ``uid``: str
        * ``comment``: str
        * ``name``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
    * Removed:
        * ``get_fields()``
        * ``set_packages()`` - Please use the property ``packages``
        * ``set_files()`` - Please use the property ``files``
        * ``set_params()`` - Please use the property ``params``
        * ``set_is_definition()`` - Please use the property ``is_definition``
        * ``set_class_name()`` - Please use the property ``class_name``
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
    * No changes
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added:
        * ``ctime``: int
        * ``depth``: float
        * ``is_definition``: bool
        * ``mtime``: int
        * ``uid``: str
        * ``class_name``: str
        * ``comment``: str
        * ``files``: list
        * ``name``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
        * ``packages``: list
        * ``params``: dict
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler.decorator import LazyProperty
from cobbler.items import item
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Mgmtclass(item.Item):
    """
    This represents a group of systems which are related in Puppet through ``Classes``.
    """

    TYPE_NAME = "mgmtclass"
    COLLECTION_TYPE = "mgmtclass"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._is_definition = False
        self._params: Dict[str, Any] = {}
        self._class_name = ""
        self._files: List[str] = []
        self._packages: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self) -> "Mgmtclass":
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """

        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Mgmtclass(self.api, **_dict)

    #
    # specific methods for item.Mgmtclass
    #

    @LazyProperty
    def packages(self) -> List[str]:
        """
        Packages property.

        :getter: Returns the value for ``packages``.
        :setter: Sets the value for the property ``packagges``.
        """
        return self._packages

    @packages.setter
    def packages(self, packages: List[str]) -> None:
        """
        Setter for the packages of the management class.

        :param packages: A string or list which contains the new packages.
        """
        self._packages = input_converters.input_string_or_list_no_inherit(packages)

    @LazyProperty
    def files(self) -> List[str]:
        """
        Files property.

        :getter: Returns the value for ``files``.
        :setter: Sets the value for the property ``files``.
        """
        return self._files

    @files.setter
    def files(self, files: Union[str, List[str]]) -> None:
        """
        Setter for the files of the object.

        :param files: A string or list which contains the new files.
        """
        self._files = input_converters.input_string_or_list_no_inherit(files)

    @LazyProperty
    def params(self) -> Dict[str, Any]:
        """
        Params property.

        :getter: Returns the value for ``params``.
        :setter: Sets the value for the property ``params``. Raises a TypeError in case of invalid parameters.
        """
        return self._params

    @params.setter
    def params(self, params: Dict[str, Any]) -> None:
        """
        Setter for the params of the management class.

        :param params: The new params for the object.
        :raises TypeError: Raised in case ``params`` is invalid.
        """
        try:
            self._params = input_converters.input_string_or_dict_no_inherit(
                params, allow_multiples=True
            )
        except TypeError as error:
            raise TypeError("invalid value for params") from error

    @LazyProperty
    def is_definition(self) -> bool:
        """
        Is_definition property.

        :getter: Returns the value for ``is_definition``.
        :setter: Sets the value for property ``is_defintion``. Raises a TypeError if not from type boolean.
        """
        return self._is_definition

    @is_definition.setter
    def is_definition(self, isdef: bool) -> None:
        """
        Setter for property ``is_defintion``.

        :param isdef: The new value for the property.
        :raises TypeError: Raised in case ``isdef`` is not a boolean.
        """
        isdef = input_converters.input_boolean(isdef)
        if not isinstance(isdef, bool):  # type: ignore
            raise TypeError("Field is_defintion from mgmtclass must be of type bool.")
        self._is_definition = isdef

    @LazyProperty
    def class_name(self) -> str:
        """
        The name of the management class.

        :getter: Returns the class name.
        :setter: Sets the name of the management class. Raises a TypeError or a Value Error.
        """
        return self._class_name

    @class_name.setter
    def class_name(self, name: str) -> None:
        """
        Setter for the name of the management class.

        :param name: The new name of the class. This must not contain "_", "-", ".", ":" or "+".
        :raises TypeError: Raised in case ``name`` is not a string.
        :raises ValueError: Raised in case ``name`` contains invalid characters.
        """
        if not isinstance(name, str):  # type: ignore
            raise TypeError("class name must be a string")
        for letter in name:
            if not letter.isalnum() and letter not in ["_", "-", ".", ":", "+"]:
                raise ValueError(f"invalid characters in class name: '{name}'")
        self._class_name = name
