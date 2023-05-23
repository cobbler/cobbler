"""
This module contains extensions for services Cobbler is managing. The services are restarted via the ``service`` command
or alternatively through the server executables directly. Cobbler does not announce the restarts but is expecting to be
allowed to do this on its own at any given time. Thus all services managed by Cobbler should not be touched by any
other tool or administrator.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 SUSE LLC
# SPDX-FileCopyrightText: Thomas Renninger <trenn@suse.de>

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from cobbler import templar

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.system import System


class ManagerModule:
    """
    Base class for Manager modules located in ``modules/manager/*.py``

    These are typically but not necessarily used to manage systemd services.
    Enabling can be done via settings ``manage_*`` (e.g. ``manage_dhcp``) and ``restart_*`` (e.g. ``restart_dhcp``).
    Different modules could manage the same functionality as dhcp can be managed via isc.py or dnsmasq.py
    (compare with ``/etc/cobbler/modules.py``).
    """

    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager module.
        Must be overwritten by the inheriting class
        """
        return "undefined"

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor

        :param api: The API instance to resolve all information with.
        """
        self.logger = logging.getLogger()
        self.api = api
        self.distros = self.api.distros()
        self.profiles = self.api.profiles()
        self.systems = self.api.systems()
        self.settings = self.api.settings()
        self.repos = self.api.repos()
        self.templar = templar.Templar(self.api)

    def write_configs(self) -> None:
        """
        Write module specific config files.
        E.g. dhcp manager would write ``/etc/dhcpd.conf`` here
        """

    def restart_service(self) -> int:
        """
        Write module specific config files.
        E.g. dhcp manager would write ``/etc/dhcpd.conf`` here
        """
        return 0

    def regen_ethers(self) -> None:
        """
        ISC/BIND doesn't use this. It is there for compatibility reasons with other managers.
        """

    def sync(self) -> int:
        """
        This syncs the manager's server (systemd service) with it's new config files.
        Basically this restarts the service to apply the changes.

        :return: Integer return value of restart_service - 0 on success
        """
        self.write_configs()
        return self.restart_service()


class DhcpManagerModule(ManagerModule):
    """
    TODO
    """

    @abstractmethod
    def sync_dhcp(self) -> None:
        """
        TODO
        """


class DnsManagerModule(ManagerModule):
    """
    TODO
    """

    @abstractmethod
    def regen_hosts(self) -> None:
        """
        TODO
        """


class TftpManagerModule(ManagerModule):
    """
    TODO
    """

    @abstractmethod
    def sync_systems(self, systems: List[str], verbose: bool = True) -> None:
        """
        TODO

        :param systems: TODO
        :param verbose: TODO
        """

    @abstractmethod
    def write_boot_files(self) -> int:
        """
        TODO
        """
        return 1

    @abstractmethod
    def add_single_distro(self, distro: "Distro") -> None:
        """
        TODO

        :param distro: TODO
        """

    @abstractmethod
    def sync_single_system(
        self,
        system: "System",
        menu_items: Optional[Dict[str, Union[str, Dict[str, str]]]] = None,
    ) -> None:
        """
        TODO

        :param system: TODO
        :param menu_items: TODO
        """
