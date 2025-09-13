"""
DNS Option Management for Cobbler Items

This module provides classes to manage DNS-related options for Cobbler items, including Profiles, Systems, and Network
Interfaces. It defines option classes for setting and validating DNS servers, search domains, DNS names, and common
names (CNAMEs). The module ensures proper validation and uniqueness of DNS names within Cobbler, and supports
inheritance and lazy property evaluation.
"""

from typing import TYPE_CHECKING, Any, List, Union

from cobbler import validate
from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.network_interface import NetworkInterface
    from cobbler.items.profile import Profile
    from cobbler.items.system import System

    InheritableProperty = property
    LazyProperty = property
else:
    from cobbler.decorator import InheritableProperty, LazyProperty


class DNSOption(ItemOption[Union["Profile", "System"]]):
    """
    Option class for managing DNS settings for Cobbler Profile and System items.

    Provides properties and methods to set and validate DNS servers and search domains.
    """

    def __init__(
        self, api: "CobblerAPI", item: Union["Profile", "System"], **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item)
        self._name_servers: Union[str, List[str]] = []
        self._name_servers_search: Union[str, List[str]] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "dns"

    @InheritableProperty
    def name_servers(self) -> List[str]:
        """
        name_servers property.
        FIXME: Differentiate between IPv4/6

        :getter: Returns the value for ``name_servers``.
        :setter: Sets the value for the property ``name_servers``.
        """
        return self._resolve_list([self.parent_name, "name_servers"])

    @name_servers.setter
    def name_servers(self, data: Union[str, List[str]]):
        """
        Set the DNS servers.
        FIXME: Differentiate between IPv4/6

        :param data: string or list of nameservers
        :returns: True or CX
        """
        self._name_servers = validate.name_servers(data)

    @LazyProperty
    def name_servers_search(self) -> List[str]:
        """
        name_servers_search property.

        :getter: Returns the value for ``name_servers_search``.
        :setter: Sets the value for the property ``name_servers_search``.
        """
        return self._resolve_list([self.parent_name, "name_servers_search"])

    @name_servers_search.setter
    def name_servers_search(self, data: Union[str, List[Any]]):
        """
        Set the DNS search paths.

        :param data: string or list of search domains
        :returns: True or CX
        """
        self._name_servers_search = validate.name_servers_search(data)


class DNSInterfaceOption(ItemOption["NetworkInterface"]):
    """
    Option class for managing DNS settings specific to a NetworkInterface.

    Handles DNS name assignment and validation, as well as management of common names (CNAMEs).
    """

    def __init__(
        self, api: "CobblerAPI", item: "NetworkInterface", **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item)
        self._name = ""
        self._common_names: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "dns"

    @property
    def name(self) -> str:
        """
        name property.

        :getter: Returns the value for ``dns_name`.
        :setter: Sets the value for the property ``dns_name``.
        """
        return self._name

    @name.setter
    def name(self, dns_name: str):
        """
        Set DNS name for interface.

        :param dns_name: DNS Name of the system
        :raises ValueError: In case the DNS name is already existing inside Cobbler
        """
        if self._name == dns_name:
            return
        dns_name = validate.hostname(dns_name)
        if dns_name != "" and not self._api.settings().allow_duplicate_hostnames:
            # FIXME: Better querying for ItemOption structs
            matched = self._api.find_network_interface(
                return_list=True, dns=f"name={dns_name}"
            )
            if matched is None:
                matched = []
            if not isinstance(matched, list):  # type: ignore
                raise ValueError("Incompatible return type detected!")
            for match in matched:
                raise ValueError(
                    f'DNS name duplicate found "{dns_name}". Object with the conflict has the name "{match.uid}"'
                )
        old_dns_name = self._name
        self._name = dns_name
        self._api.network_interfaces().update_index_value(
            self._item, "dns.name", old_dns_name, dns_name
        )

    @property
    def common_names(self) -> List[str]:
        """
        cnames property.

        :getter: Returns the value for ``cnames``.
        :setter: Sets the value for the property ``cnames``.
        """
        return self._common_names

    @common_names.setter
    def common_names(self, cnames: List[str]):
        """
        Setter for the cnames of the NetworkInterface class.

        :param cnames: The new cnames.
        """
        self._common_names = self._api.input_string_or_list_no_inherit(cnames)
