"""
TODO
"""

from cobbler.cobbler_collections.collection import Collection


class Templates(Collection):
    """
    TODO
    """

    @staticmethod
    def collection_type() -> str:
        return "distro"

    @staticmethod
    def collection_types() -> str:
        return "distros"

    def factory_produce(self, api, seed_data):
        pass

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ):
        pass
