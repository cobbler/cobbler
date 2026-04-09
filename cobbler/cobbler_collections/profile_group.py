"""
ProfileGroupCollection
"""

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cobbler_collections.collection import Collection
from cobbler.items import profile_group

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class ProfileGroups(Collection[profile_group.ProfileGroup]):
    """
    The collection for profile groups.
    """

    @staticmethod
    def collection_type() -> str:
        return "profile_group"

    @staticmethod
    def collection_types() -> str:
        return "profile_groups"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> profile_group.ProfileGroup:
        """
        Return a Profile Group forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: The data the object is initialized with.
        :returns: The created ProfileGroup.
        """
        return profile_group.ProfileGroup(api, **seed_data)
