"""
A Resource is a serializable thing that can appear in a Collection

Changelog:

V3.4.0 (unreleased):
    * No changes
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * No changes
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * File was moved from ``cobbler/resource.py`` to ``cobbler/items/resource.py``.
    * Added:
        * action: enums.ResourceAction
        * mode: str
        * owner: str
        * group: str
        * path: str
        * template: str
    * Removed:
        * ``set_template`` - Please use the property ``template``
        * ``set_path`` - Please use the property ``path``
        * ``set_owner`` - Please use the property ``owner``
        * ``set_mode`` - Please use the property ``mode``
        * ``set_group`` - Please use the property ``group``
        * ``set_action`` - Please use the property ``action``
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

"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Kelsey Hightower <kelsey.hightower@gmail.com>

import copy
from typing import TYPE_CHECKING, Any, Union

from cobbler import enums
from cobbler.decorator import LazyProperty
from cobbler.items import item

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Resource(item.Item):
    """
    Base Class for management resources.
    """

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._action = enums.ResourceAction.CREATE
        self._mode = ""
        self._owner = ""
        self._group = ""
        self._path = ""
        self._template = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self) -> "Resource":
        """
        Clone this file object. Please manually adjust all values yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Resource(self.api, **_dict)

    #
    # specific methods for item.File
    #

    @LazyProperty
    def action(self) -> enums.ResourceAction:
        """
        Action property.

        :getter: Return the value for ``action``.
        :setter: Sets the value for property ``action``. Raises a ValueError or a TypeError.
        """
        return self._action

    @action.setter
    def action(self, action: Union[str, enums.ResourceAction]) -> None:
        """
        All management resources have an action. Actions determine weather most resources should be created or removed,
        and if packages should be installed or uninstalled.

        :param action: The action which should be executed for the management resource. Must be of "create" or
                       "remove". Parameter is case-insensitive.
        :raise ValueError: Raised in case wrong value is provided.
        :raise TypeError: Raised in case ``action`` is no ``enums.ResourceAction``.
        """
        self._action = enums.ResourceAction.to_enum(action)

    @LazyProperty
    def group(self) -> str:
        """
        Group property.

        :getter: Return the value for ``group``.
        :setter: Sets the value for property ``group``.
        """
        return self._group

    @group.setter
    def group(self, group: str) -> None:
        """
        Unix group ownership of a file or directory.

        :param group: The group which the resource will belong to.
        :raise TypeError: Raised in case ``group`` is no string. Raises a TypeError.
        """
        if not isinstance(group, str):  # type: ignore
            raise TypeError("Field group of object resource needs to be of type str!")
        self._group = group

    @LazyProperty
    def mode(self) -> str:
        """
        Mode property.

        :getter: Return the value for ``mode``.
        :setter: Sets the value for property ``mode``. Raises a TypeError.
        """
        return self._mode

    @mode.setter
    def mode(self, mode: str) -> None:
        """
        Unix file permission mode ie: '0644' assigned to file and directory resources.

        :param mode: The mode which the resource will have.
        :raise TypeError: Raised in case ``mode`` is no string.
        """
        if not isinstance(mode, str):  # type: ignore
            raise TypeError("Field mode in object resource needs to be of type str!")
        self._mode = mode

    @LazyProperty
    def owner(self) -> str:
        """
        Owner property.

        :getter: Return the value for ``owner``.
        :setter: Sets the value for property ``owner``. Raises a TypeError.
        """
        return self._owner

    @owner.setter
    def owner(self, owner: str) -> None:
        """
        Unix owner of a file or directory.

        :param owner: The owner whom the resource will belong to.
        :raise TypeError: Raised in case ``owner`` is no string.
        """
        if not isinstance(owner, str):  # type: ignore
            raise TypeError("Field owner in object resource needs to be of type str!")
        self._owner = owner

    @LazyProperty
    def path(self) -> str:
        """
        Path property.

        :getter: Return the value for ``path``.
        :setter: Sets the value for property ``path``. Raises a TypeError.
        """
        return self._path

    @path.setter
    def path(self, path: str) -> None:
        """
        File path used by file and directory resources.

        :param path: Normally an absolute path of the file or directory to create or manage.
        :raise TypeError: Raised in case ``path`` is no string.
        """
        if not isinstance(path, str):  # type: ignore
            raise TypeError("Field path in object resource needs to be of type str!")
        self._path = path

    @LazyProperty
    def template(self) -> str:
        """
        Template property.

        :getter: Return the value for ``template``.
        :setter: Sets the value for property ``template``. Raises a TypeError.
        """
        return self._template

    @template.setter
    def template(self, template: str) -> None:
        """
        Path to cheetah template on Cobbler's local file system. Used to generate file data shipped to koan via json.
        All templates have access to flatten autoinstall_meta data.

        :param template: The template to use for the resource.
        :raise TypeError: Raised in case ``template`` is no string.
        """
        if not isinstance(template, str):  # type: ignore
            raise TypeError(
                "Field template in object resource needs to be of type str!"
            )
        self._template = template
