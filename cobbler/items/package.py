"""
Cobbler module that contains the code for a Cobbler package object.

Changelog:

V3.4.0 (unreleased):
    * Changes:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``from_dict()``: The method was moved to the base class.
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``check_if_valid()``: Now present in base class (Item).
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``from_dict()``
    * Moved to base classes (Resource & Item):
        * ctime: float
        * depth: float
        * mtime: float
        * uid: str
        * action: str
        * comment: str
        * name: str
        * owners: Union[list, SETTINGS:default_ownership]
    * Removed:
        * ``get_fields()``
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
    * File was moved from ``cobbler/item_package.py`` to ``cobbler/items/package.py``.
V3.0.0:
    * Added:
        * ``set_installer()``
        * ``set_version()``
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added:
        * ctime: float
        * depth: float
        * mtime: float
        * uid: str
        * action: str
        * comment: str
        * installer: str
        * name: str
        * owners: Union[list, SETTINGS:default_ownership]
        * version: str
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Kelsey Hightower <kelsey.hightower@gmail.com>

import copy
from typing import TYPE_CHECKING, Any

from cobbler.decorator import LazyProperty
from cobbler.items import resource

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Package(resource.Resource):
    """
    This class represents a package which is being installed on a system.
    """

    TYPE_NAME = "package"
    COLLECTION_TYPE = "package"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        :param item_dict: Dictionary of properties to initialize the object.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._installer = ""
        self._version = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this package object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Package(self.api, **_dict)

    #
    # specific methods for item.Package
    #

    @LazyProperty
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
        if not isinstance(installer, str):  # type: ignore
            raise TypeError(
                "Field installer of package object needs to be of type str!"
            )
        self._installer = installer.lower()

    @LazyProperty
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
        if not isinstance(version, str):  # type: ignore
            raise TypeError("Field version of package object needs to be of type str!")
        self._version = version
