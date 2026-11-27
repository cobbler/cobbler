"""
SystemGroup class for grouping systems.

Changelog:

V4.0.0:
    * Initial creation of the class as a concrete ``ItemGroup`` subclass for grouping systems. Full CRUD support
      added to ``cobbler.api``/``cobbler.remote``.
"""

import copy
from typing import TYPE_CHECKING, Any

from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.item_group import ItemGroup

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class SystemGroup(ItemGroup):
    """
    SystemGroup class
    """

    TYPE_NAME = "system_group"
    COLLECTION_TYPE = "system_group"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        super().__init__(api, *args, **kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self, keep_uid: bool = False) -> "BaseItem":
        """
        Clone this system group

        :param keep_uid: See :meth:`~cobbler.items.abstract.base_item.BaseItem.make_clone`.
        """
        _dict = copy.deepcopy(self.to_dict())
        if not keep_uid:
            _dict.pop("uid", None)
        return SystemGroup(self.api, **_dict)
