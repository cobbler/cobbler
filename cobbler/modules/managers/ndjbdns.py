# coding=utf-8
"""
This is some of the code behind 'cobbler sync'.

Copyright 2014, Mittwald CM Service GmbH & Co. KG
Martin Helmich <m.helmich@mittwald.de>
Daniel Krämer <d.kraemer@mittwald.de>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""


from builtins import object
import os
import subprocess

import cobbler.clogger as clogger
import cobbler.templar as templar


def register():
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


def get_manager(config, logger):
    """
    Get the DNS Manger object.

    :param config: Unused parameter.
    :param logger: The logger to audit the actions with.
    :return: The manager object.
    """
    return NDjbDnsManager(config, logger)


class NDjbDnsManager(object):

    def __init__(self, config, logger):
        """
        This class can manage a New-DJBDNS server.

        :param config: Currently an usused parameter.
        :param logger: The logger to audit the actions with.
        """
        self.logger = logger
        if self.logger is None:
            self.logger = clogger.Logger()

        self.config = config
        self.systems = config.systems()
        self.templar = templar.Templar(config)

    def what(self):
        """
        Static method to identify the manager.

        :return: Always "ndjbdns".
        """
        return "ndjbdns"

    def regen_hosts(self):
        """
        Empty stub method to have compability with other dns managers who need this.
        """
        pass

    def write_dns_files(self):
        """
        This writes the new dns configuration file to the disc.
        """
        template_file = '/etc/cobbler/ndjbdns.template'
        data_file = '/etc/ndjbdns/data'
        data_dir = os.path.dirname(data_file)

        a_records = {}

        with open(template_file, 'r') as f:
            template_content = f.read()

        for system in self.systems:
            for (name, interface) in list(system.interfaces.items()):
                host = interface['dns_name']
                ip = interface['ip_address']

                if host:
                    if host in a_records:
                        raise Exception('Duplicate DNS name: %s' % host)
                    a_records[host] = ip

        template_vars = {'forward': []}
        for host, ip in list(a_records.items()):
            template_vars['forward'].append((host, ip))

        self.templar.render(template_content, template_vars, data_file)

        p = subprocess.Popen(['/usr/bin/tinydns-data'], cwd=data_dir)
        p.communicate()

        if p.returncode != 0:
            raise Exception('Could not regenerate tinydns data file.')
