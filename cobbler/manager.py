"""
Base class for modules.managers.* classes
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 SUSE LLC
# SPDX-FileCopyrightText: Thomas Renninger <trenn@suse.de>

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class ManagerModule:
    """
    Base class for Manager modules located in ``modules/manager/*.py``

    These are typically but not necessarily used to manage systemd services.
    Enabling can be done via settings ``manage_*`` (e.g. ``manage_dhcp``) and ``restart_*`` (e.g. ``restart_dhcp``).
    Different modules could manage the same functionality as dhcp can be managed via isc.py or dnsmasq.py
    (compare with ``/etc/cobbler/modules.py``).
    """

    @staticmethod
    def what():
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

    def write_configs(self):
        """
        Write module specific config files.
        E.g. dhcp manager would write ``/etc/dhcpd.conf`` here
        """

    def restart_service(self) -> int:
        """
        Write module specific config files.
        E.g. dhcp manager would write ``/etc/dhcpd.conf`` here
        """

    def regen_ethers(self):
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
