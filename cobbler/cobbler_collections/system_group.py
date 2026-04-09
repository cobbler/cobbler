"""
SystemGroupCollection
"""

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cobbler_collections.collection import Collection
from cobbler.items import system_group

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class SystemGroups(Collection[system_group.SystemGroup]):
    """
    The collection for system groups.
    """

    @staticmethod
    def collection_type() -> str:
        return "system_group"

    @staticmethod
    def collection_types() -> str:
        return "system_groups"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> system_group.SystemGroup:
        """
        Return a System Group forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: The data the object is initialized with.
        :returns: The created SystemGroup.
        """
        return system_group.SystemGroup(api, **seed_data)
