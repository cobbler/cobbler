"""
Copyright 2010, Kelsey Hightower
Kelsey Hightower <kelsey.hightower@gmail.com>

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
import uuid
from typing import Union
from cobbler.decorator import LazyProperty

from cobbler.items import item
from cobbler import utils


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

    #
    # specific methods for item.Mgmtclass
    #

    @LazyProperty
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
        self._packages = utils.input_string_or_list(packages)

    @LazyProperty
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
        self._files = utils.input_string_or_list(files)

    @LazyProperty
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
            self._params = utils.input_string_or_dict(params, allow_multiples=True)
        except TypeError as e:
            raise TypeError("invalid value for params") from e

    @LazyProperty
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
        isdef = utils.input_boolean(isdef)
        if not isinstance(isdef, bool):
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
    def class_name(self, name: str):
        """
        Setter for the name of the management class.

        :param name: The new name of the class. This must not contain "_", "-", ".", ":" or "+".
        :raises TypeError: Raised in case ``name`` is not a string.
        :raises ValueError: Raised in case ``name`` contains invalid characters.
        """
        if not isinstance(name, str):
            raise TypeError("class name must be a string")
        for x in name:
            if not x.isalnum() and x not in ["_", "-", ".", ":", "+"]:
                raise ValueError("invalid characters in class name: '%s'" % name)
        self._class_name = name
