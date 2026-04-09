"""
DistroGroupCollection
"""

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cobbler_collections.collection import Collection
from cobbler.items import distro_group

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class DistroGroups(Collection[distro_group.DistroGroup]):
    """
    The collection for distro groups.
    """

    @staticmethod
    def collection_type() -> str:
        return "distro_group"

    @staticmethod
    def collection_types() -> str:
        return "distro_groups"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> distro_group.DistroGroup:
        """
        Return a Distro Group forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: The data the object is initialized with.
        :returns: The created DistroGroup.
        """
        return distro_group.DistroGroup(api, **seed_data)
