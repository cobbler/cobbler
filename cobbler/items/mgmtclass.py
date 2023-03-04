"""
Cobbler module that contains the code for a Cobbler mgmtclass object.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

import uuid
from typing import Union

from cobbler.items import item
from cobbler.utils import input_converters


class Mgmtclass(item.Item):
    """
    This represents a group of systems which are related in Puppet through ``Classes``.
    """

    TYPE_NAME = "mgmtclass"
    COLLECTION_TYPE = "mgmtclass"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        :param args: The arguments which should be passed additionally to the base Item class constructor.
        :param kwargs: The keyword arguments which should be passed additionally to the base Item class constructor.
        """
        super().__init__(api, *args, **kwargs)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._is_definition = False
        self._params = {}
        self._class_name = ""
        self._files = []
        self._packages = []
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """

        _dict = self.to_dict()
        cloned = Mgmtclass(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        self._remove_depreacted_dict_keys(dictionary)
        super().from_dict(dictionary)

    #
    # specific methods for item.Mgmtclass
    #

    @property
    def packages(self) -> list:
        """
        Packages property.

        :getter: Returns the value for ``packages``.
        :setter: Sets the value for the property ``packagges``.
        """
        return self._packages

    @packages.setter
    def packages(self, packages: list):
        """
        Setter for the packages of the management class.

        :param packages: A string or list which contains the new packages.
        """
        self._packages = input_converters.input_string_or_list(packages)

    @property
    def files(self) -> list:
        """
        Files property.

        :getter: Returns the value for ``files``.
        :setter: Sets the value for the property ``files``.
        """
        return self._files

    @files.setter
    def files(self, files: Union[str, list]):
        """
        Setter for the files of the object.

        :param files: A string or list which contains the new files.
        """
        self._files = input_converters.input_string_or_list(files)

    @property
    def params(self) -> dict:
        """
        Params property.

        :getter: Returns the value for ``params``.
        :setter: Sets the value for the property ``params``. Raises a TypeError in case of invalid parameters.
        """
        return self._params

    @params.setter
    def params(self, params: dict):
        """
        Setter for the params of the management class.

        :param params: The new params for the object.
        :raises TypeError: Raised in case ``params`` is invalid.
        """
        try:
            self._params = input_converters.input_string_or_dict(
                params, allow_multiples=True
            )
        except TypeError as error:
            raise TypeError("invalid value for params") from error

    @property
    def is_definition(self) -> bool:
        """
        Is_definition property.

        :getter: Returns the value for ``is_definition``.
        :setter: Sets the value for property ``is_defintion``. Raises a TypeError if not from type boolean.
        """
        return self._is_definition

    @is_definition.setter
    def is_definition(self, isdef: bool):
        """
        Setter for property ``is_defintion``.

        :param isdef: The new value for the property.
        :raises TypeError: Raised in case ``isdef`` is not a boolean.
        """
        isdef = input_converters.input_boolean(isdef)
        if not isinstance(isdef, bool):
            raise TypeError("Field is_defintion from mgmtclass must be of type bool.")
        self._is_definition = isdef

    @property
    def class_name(self) -> str:
        """
        The name of the management class.

        :getter: Returns the class name.
        :setter: Sets the name of the management class. Raises a TypeError or a Value Error.
        """
        return self._class_name

    @class_name.setter
    def class_name(self, name: str):
        """
        Setter for the name of the management class.

        :param name: The new name of the class. This must not contain "_", "-", ".", ":" or "+".
        :raises TypeError: Raised in case ``name`` is not a string.
        :raises ValueError: Raised in case ``name`` contains invalid characters.
        """
        if not isinstance(name, str):
            raise TypeError("class name must be a string")
        for letter in name:
            if not letter.isalnum() and letter not in ["_", "-", ".", ":", "+"]:
                raise ValueError(f"invalid characters in class name: '{name}'")
        self._class_name = name
