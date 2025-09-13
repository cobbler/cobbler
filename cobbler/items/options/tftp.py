"""
TFTP option management for Cobbler Profile and System items.
"""

from typing import TYPE_CHECKING, Any, Union

from cobbler import enums, validate
from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.profile import Profile
    from cobbler.items.system import System

    InheritableProperty = property
else:
    from cobbler.decorator import InheritableProperty


class TFTPOption(ItemOption[Union["Profile", "System"]]):
    """
    Option class for managing TFTP server settings for Cobbler Profile and System items.

    Handles configuration of next server addresses and related TFTP options.
    """

    def __init__(
        self, api: "CobblerAPI", item: Union["Profile", "System"], **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item, **kwargs)
        self._next_server_v4 = enums.VALUE_INHERITED
        self._next_server_v6 = enums.VALUE_INHERITED
        # TODO: filename property

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "tftp"

    @InheritableProperty
    def next_server_v4(self) -> str:
        """
        next_server_v4 property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``next_server_v4``.
        :setter: Sets the value for the property ``next_server_v4``.
        """
        return self._resolve([self.parent_name, "next_server_v4"])

    @next_server_v4.setter
    def next_server_v4(self, server: str = ""):
        """
        Setter for the IPv4 next server. See profile.py for more details.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
            raise TypeError("next_server_v4 must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v4 = enums.VALUE_INHERITED
        else:
            self._next_server_v4 = validate.ipv4_address(server)

    @InheritableProperty
    def next_server_v6(self) -> str:
        """
        next_server_v6 property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``next_server_v6``.
        :setter: Sets the value for the property ``next_server_v6``.
        """
        return self._resolve([self.parent_name, "next_server_v6"])

    @next_server_v6.setter
    def next_server_v6(self, server: str = ""):
        """
        Setter for the IPv6 next server. See profile.py for more details.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
            raise TypeError("next_server_v6 must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v6 = enums.VALUE_INHERITED
        else:
            self._next_server_v6 = validate.ipv6_address(server)
