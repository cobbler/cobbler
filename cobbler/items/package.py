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

from cobbler.items import resource

from cobbler.cexceptions import CX


class Package(resource.Resource):
    """
    This class represents a package which is being installed on a system.
    """

    TYPE_NAME = "package"
    COLLECTION_TYPE = "package"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        :param args: The arguments which should be passed additionally to a Resource.
        :param kwargs: The keyword arguments which should be passed additionally to a Resource.
        """
        super().__init__(api, *args, **kwargs)
        self._installer = ""
        self._version = ""

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this package object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Package(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def check_if_valid(self):
        """
        Checks if the object is in a valid state. This only checks currently if the name is present.

        :raises CX: Raised in case name is not given.
        """
        if not self.name:
            raise CX("name is required")

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        self._remove_depreacted_dict_keys(dictionary)
        super().from_dict(dictionary)

    #
    # specific methods for item.Package
    #

    @property
    def installer(self) -> str:
        """
        Installer property.

        :getter: Returns the value for ``installer``.
        :setter: Sets the value for property ``installer``. Raises a TypeError if ``installer`` is no string.
        """
        return self._installer

    @installer.setter
    def installer(self, installer: str):
        """
        Setter for the installer parameter.

        :param installer: This parameter will be lowercased regardless of what string you give it.
        :raises TypeError: Raised in case ``installer`` is no string.
        """
        if not isinstance(installer, str):
            raise TypeError("Field installer of package object needs to be of type str!")
        self._installer = installer.lower()

    @property
    def version(self) -> str:
        """
        Version property.

        :getter: Returns the value for ``version``.
        :setter: Sets the value for property ``version``. Raises a TypeError in case ``version`` is no string.
        """
        return self._version

    @version.setter
    def version(self, version: str):
        """
        Setter for the package version.

        :param version: They may be anything which is suitable for describing the version of a package. Internally this
                        is a string.
        :raises TypeError: Raised in case ``version`` is no string.
        """
        if not isinstance(version, str):
            raise TypeError("Field version of package object needs to be of type str!")
        self._version = version
