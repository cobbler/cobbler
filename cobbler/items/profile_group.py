"""
ProfileGroup class for grouping profiles.
"""

import copy
from typing import TYPE_CHECKING, Any

from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.item_group import ItemGroup

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class ProfileGroup(ItemGroup):
    """
    ProfileGroup class
    """

    TYPE_NAME = "profile_group"
    COLLECTION_TYPE = "profile_group"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        super().__init__(api, *args, **kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self) -> "BaseItem":
        """
        Clone this profile group
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return ProfileGroup(self.api, **_dict)
