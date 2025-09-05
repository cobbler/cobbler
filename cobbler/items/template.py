"""
TODO
"""

from typing import TYPE_CHECKING, Any

from cobbler.decorator import LazyProperty
from cobbler.items.abstract.base_item import BaseItem

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Template(BaseItem):
    """
    TODO
    """

    TYPE_NAME = "template"
    COLLECTION_TYPE = "template"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._template_type = ""
        self._template_uri = ""
        self._built_in = False

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self) -> "Template":
        return None  # type: ignore

    def _resolve(self, property_name: str) -> Any:
        pass

    @LazyProperty
    def template_type(self) -> str:
        """
        TODO
        """
        return self._template_type

    @LazyProperty
    def template_uri(self) -> str:
        """
        TODO
        """
        return self._template_uri

    @LazyProperty
    def built_in(self) -> bool:
        """
        TODO
        """
        return self._built_in
