"""
Copyright 2006-2009, MadHatter
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

from cobbler import utils
from cobbler.items import resource

from cobbler.cexceptions import CX


class File(resource.Resource):
    """
    A Cobbler file object.
    """

    TYPE_NAME = "file"
    COLLECTION_TYPE = "file"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        :param args: The arguments which should be passed additionally to a Resource.
        :param kwargs: The keyword arguments which should be passed additionally to a Resource.
        """
        super().__init__(api, *args, **kwargs)
        self._is_dir = False

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all values yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = File(self.api)
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
        Checks if the object is valid. This is the case if name, path, owner, group, and mode are set.
        Templates are only required for files if ``is_dir`` is true then template is not required.

        :raises CX: Raised in case a required argument is missing
        """
        if not self.name:
            raise CX("name is required")
        if not self.path:
            raise CX("path is required")
        if not self.owner:
            raise CX("owner is required")
        if not self.group:
            raise CX("group is required")
        if not self.mode:
            raise CX("mode is required")
        if not self.is_dir and self.template == "":
            raise CX("Template is required when not a directory")

    #
    # specific methods for item.File
    #

    @property
    def is_dir(self):
        """
        Is this a directory or not.

        :getter: Returns the value of ``is_dir``
        :setter: Sets the value of ``is_dir``. Raises a TypeError in case value is not a boolean.
        """
        return self._is_dir

    @is_dir.setter
    def is_dir(self, is_dir: bool):
        """
        If true, treat file resource as a directory. Templates are ignored.

        :param is_dir: This is the path to check if it is a directory.
        :raises TypeError: Raised in case ``is_dir`` is not a boolean.
        """
        is_dir = utils.input_boolean(is_dir)
        if not isinstance(is_dir, bool):
            raise TypeError("Field is_dir in object file needs to be of type bool!")
        self._is_dir = is_dir
