"""
TODO
"""

from typing import TYPE_CHECKING, Any, Dict, List

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
        return "template"

    @staticmethod
    def collection_types() -> str:
        return "templates"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> template.Template:
        """
        Return a Template forged from seed_data

        :param api: parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object
        """
        return template.Template(self.api, **seed_data)

    def refresh_content(self) -> None:
        """
        Refresh the content of all templates in the collection. If the refresh of a template failed a warning is logged.
        """
        failed_refreshes: List[str] = []
        for obj in self:
            refresh_success = obj.refresh_content()
            if not refresh_success:
                failed_refreshes.append(obj.uid)
        if len(failed_refreshes) > 0:
            self.logger.warning(
                "Refreshing the content of following templates failed: %s",
                ", ".join(failed_refreshes),
            )
