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
from typing import TYPE_CHECKING, List

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

    def sync_single_system(self, system: "System") -> int:
        """
        This synchronizes data for a single system. The default implementation is
        to trigger full synchronization. Manager modules can overwrite this method
        to improve performance.

        :param system: A system to be added.
        """
        del system  # unused var
        self.regen_ethers()
        return self.sync()

    def remove_single_system(self, system_obj: "System") -> None:
        """
        This method removes a single system.
        """
        del system_obj  # unused var
        self.regen_ethers()
        self.sync()


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

    def add_single_hosts_entry(self, system: "System") -> None:
        """
        This method adds a single system to the host file.
        DNS manager modules can implement this method to improve performance.
        Otherwise, this method defaults to a full host regeneration.

        :param system: A system to be added.
        """
        del system  # unused var
        self.regen_hosts()

    def remove_single_hosts_entry(self, system: "System") -> None:
        """
        This method removes a single system from the host file.
        DNS manager modules can implement this method to improve performance.
        Otherwise, this method defaults to a full host regeneration.

        :param system: A system to be removed.
        """
        del system  # unused var
        self.regen_hosts()


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
