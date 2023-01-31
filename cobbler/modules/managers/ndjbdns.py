# coding=utf-8
"""
This is some of the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2014, Mittwald CM Service GmbH & Co. KG
# SPDX-FileCopyrightText: Martin Helmich <m.helmich@mittwald.de>
# SPDX-FileCopyrightText: Daniel Krämer <d.kraemer@mittwald.de>

import os
import subprocess

from cobbler.manager import ManagerModule

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _NDjbDnsManager(ManagerModule):
    """
    Support for Dr. D J Bernstein DNS server.

    This DNS server has a lot of forks with IPv6 support. However, the original has no support for IPv6 and thus we
    can't add support for it at the moment.
    """

    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "ndjbdns".
        """
        return "ndjbdns"

    def __init__(self, api):
        super().__init__(api)

    def write_configs(self):
        """
        This writes the new dns configuration file to the disc.
        """
        template_file = "/etc/cobbler/ndjbdns.template"
        data_file = "/etc/ndjbdns/data"
        data_dir = os.path.dirname(data_file)

        a_records = {}

        with open(template_file, "r", encoding="UTF-8") as template_fd:
            template_content = template_fd.read()

        for system in self.systems:
            for (_, interface) in list(system.interfaces.items()):
                host = interface.dns_name
                ip_address = interface.ip_address

                if host:
                    if host in a_records:
                        raise Exception(f"Duplicate DNS name: {host}")
                    a_records[host] = ip_address

        template_vars = {"forward": []}
        for host, ip_address in list(a_records.items()):
            template_vars["forward"].append((host, ip_address))

        self.api.templar.render(template_content, template_vars, data_file)

        with subprocess.Popen(
            ["/usr/bin/tinydns-data"], cwd=data_dir
        ) as subprocess_popen_obj:
            subprocess_popen_obj.communicate()

            if subprocess_popen_obj.returncode != 0:
                raise Exception("Could not regenerate tinydns data file.")


def get_manager(api):
    """
    Creates a manager object to manage an isc dhcp server.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _NDjbDnsManager(api)
    return MANAGER
