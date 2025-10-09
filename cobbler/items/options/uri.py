"""
URI option management for Cobbler items.
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
    Option class for managing an URI for Cobbler items.
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
        return "uri"

    @property
    def full_uri(self) -> str:
        """
        Property to represent the full URI that is curently stored.
        """
        # FIXME: This is implementation is too crude atm.
        return f"{self._schema}://{self._authority}{self._path}?{self._query}#{self._fragment}"

    @LazyProperty
    def schema(self) -> str:
        """
        Property that represents the schema. A schema is something like "http", "ftp" or anything else that makes sense
        in the context of the usage of the URIOption.

        :getter: Returns the current schema.
        :setter: Sets the new value for schema.
        """
        return self._schema

    @schema.setter
    def schema(self, val: str) -> None:
        """
        Sets the new value for the schema.

        :param val: The string with the new value.
        """
        self._schema = val

    @LazyProperty
    def authority(self) -> str:
        """
        Property that represents the authority. An authority is a hostname, an IP address or empty.

        :getter: Returns the current authority.
        :setter: Sets the new value for the authority.
        """
        return self._authority

    @authority.setter
    def authority(self, val: str) -> None:
        """
        Sets the new value for the authority.

        :param val: The string with the new value.
        """
        self._authority = val

    @LazyProperty
    def path(self) -> str:
        """
        Property that represents the path. A path is the location where the target resource can be found if requested
        from the optional authority. In case a path validator is present, it is executed.

        :getter: Returns the current path.
        :setter: Sets the new value for the path in case the optional path validation succeeds.
        """
        return self._path

    @path.setter
    def path(self, val: str) -> None:
        """
        Sets the new value for the path.

        :param val: The string with the new value.
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
        Property that represents the query. The query does not need to be prefixed with a questionmark and only a single
        query parameter is supported at the moment.

        :getter: Returns the current query.
        :setter: Sets the new value for the query.
        """
        return self._query

    @query.setter
    def query(self, val: str) -> None:
        """
        Sets the new value for the query.

        :param val: The string with the new value.
        """
        self._query = val

    @LazyProperty
    def fragment(self) -> str:
        """
        Property that represents the fragment. The framgent does not need to be prefixed with a questionsmark and only a
        single fragment parameter is supported at the moment.

        :getter: Returns the current fragement.
        :setter: Sets the new value for the fragment.
        """
        return self._fragment

    @fragment.setter
    def fragment(self, val: str) -> None:
        """
        Sets the new value for the fragment.

        :param val: The string with the new value.
        """
        self._fragment = val
