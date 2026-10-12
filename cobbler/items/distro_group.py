"""
DistroGroup class for grouping distros.

Changelog:

V4.0.0 (unreleased):
    * Initial creation of the class as a concrete ``ItemGroup`` subclass for grouping distros. Full CRUD support
      added to ``cobbler.api``/``cobbler.remote``.
"""

import copy
from typing import TYPE_CHECKING, Any

from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.item_group import ItemGroup

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class DistroGroup(ItemGroup):
    """
    DistroGroup class
    """

    TYPE_NAME = "distro_group"
    COLLECTION_TYPE = "distro_group"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        super().__init__(api, *args, **kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self) -> "BaseItem":
        """
        Clone this distro group
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return DistroGroup(self.api, **_dict)
