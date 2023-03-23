"""
Cobbler module that contains the code for a Cobbler file object.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Kelsey Hightower <kelsey.hightower@gmail.com>

import copy
from typing import TYPE_CHECKING, Any

from cobbler.utils import input_converters
from cobbler.items import resource
from cobbler.decorator import LazyProperty
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class File(resource.Resource):
    """
    A Cobbler file object.
    """

    TYPE_NAME = "file"
    COLLECTION_TYPE = "file"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._is_dir = False

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all values yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return File(self.api, **_dict)

    def check_if_valid(self):
        """
        Checks if the object is valid. This is the case if name, path, owner, group, and mode are set.
        Templates are only required for files if ``is_dir`` is true then template is not required.

        :raises CX: Raised in case a required argument is missing
        """
        super().check_if_valid()
        if not self.inmemory:
            return
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

    @LazyProperty
    def is_dir(self):
        r"""
        Is this a directory or not.

        :getter: Returns the value of ``is_dir``
        :setter: Sets the value of ``is_dir``. Raises a TypeError in case value is not a boolean.
        """
        return self._is_dir

    @is_dir.setter
    def is_dir(self, is_dir: bool):
        r"""
        If true, treat file resource as a directory. Templates are ignored.

        :param is_dir: This is the path to check if it is a directory.
        :raises TypeError: Raised in case ``is_dir`` is not a boolean.
        """
        is_dir = input_converters.input_boolean(is_dir)
        if not isinstance(is_dir, bool):
            raise TypeError("Field is_dir in object file needs to be of type bool!")
        self._is_dir = is_dir
