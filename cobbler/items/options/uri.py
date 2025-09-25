"""
TODO
"""

import types
from typing import TYPE_CHECKING, Any, Callable, Optional

from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.template import Template

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


CustomPathValidatorType = Optional[Callable[["CobblerAPI", str], bool]]


class URIOption(ItemOption["Template"]):
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI", item: Any, **kwargs: Any) -> None:
        super().__init__(api, item, **kwargs)
        self._schema = ""
        self._authority = ""
        self._path = ""
        self._query = ""
        self._fragment = ""
        path_validator = kwargs.get("path_validator")
        if not callable(path_validator):
            # Set the argument to None if the argument is not a callable
            path_validator = None
        self.__path_validator: CustomPathValidatorType = types.MethodType(
            path_validator, self  # type: ignore
        )

    @property
    def parent_name(self) -> str:
        """
        TODO
        """
        return "uri"

    @property
    def full_uri(self) -> str:
        """
        TODO
        """
        # FIXME: This is implementation is too crude atm.
        return f"{self._schema}://{self._authority}{self._path}?{self._query}#{self._fragment}"

    @LazyProperty
    def schema(self) -> str:
        """
        TODO
        """
        return self._schema

    @schema.setter
    def schema(self, val: str) -> None:
        """
        TODO
        """
        self._schema = val

    @LazyProperty
    def authority(self) -> str:
        """
        TODO
        """
        return self._authority

    @authority.setter
    def authority(self, val: str) -> None:
        """
        TODO
        """
        self._authority = val

    @LazyProperty
    def path(self) -> str:
        """
        TODO
        """
        return self._path

    @path.setter
    def path(self, val: str) -> None:
        """
        TODO
        """
        # pylint: disable-next=not-callable
        if self.__path_validator is not None and not self.__path_validator(
            self._api, val
        ):
            raise ValueError("Additional path validation failed!")
        self._path = val

    @LazyProperty
    def query(self) -> str:
        """
        TODO
        """
        return self._query

    @query.setter
    def query(self, val: str) -> None:
        """
        TODO
        """
        self._query = val

    @LazyProperty
    def fragment(self) -> str:
        """
        TODO
        """
        return self._fragment

    @fragment.setter
    def fragment(self, val: str) -> None:
        """
        TODO
        """
        self._fragment = val
