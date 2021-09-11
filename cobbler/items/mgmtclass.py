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

from cobbler.items import item
from cobbler import utils
from cobbler.cexceptions import CX


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
        self._is_definition = False
        self._params = {}
        self._class_name = ""
        self._files = []
        self._packages = []

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

    def check_if_valid(self):
        """
        Check if this object is in a valid state. This currently checks only if the name is present.

        :raises CX: Raised in case no name is given.
        """
        if not self.name:
            raise CX("name is required")

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
        self._packages = utils.input_string_or_list(packages)

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
        self._files = utils.input_string_or_list(files)

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
        (success, value) = utils.input_string_or_dict(params, allow_multiples=True)
        if not success:
            raise TypeError("invalid parameters")
        self._params = value

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
        isdef = utils.input_boolean(isdef)
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
        for x in name:
            if not x.isalnum() and x not in ["_", "-", ".", ":", "+"]:
                raise ValueError("invalid characters in class name: '%s'" % name)
        self._class_name = name
