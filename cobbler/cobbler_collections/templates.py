"""
TODO
"""

from typing import TYPE_CHECKING, Any, Dict
from cobbler.cobbler_collections.collection import Collection
from cobbler.items import template

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Templates(Collection[template.Template]):
    """
    TODO
    """

    @staticmethod
    def collection_type() -> str:
        return "distro"

    @staticmethod
    def collection_types() -> str:
        return "distros"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> template.Template:
        return None  # type: ignore

    def remove(
        self,
        ref: template.Template,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ):
        pass
