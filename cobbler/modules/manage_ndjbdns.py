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

import clogger
import templar
import os
import subprocess


def register():
    return "manage"


def get_manager(config, logger):
    return NDjbDnsManager(config, logger)


class NDjbDnsManager:

    def __init__(self, config, logger):
        self.logger = logger
        if self.logger is None:
            self.logger = clogger.Logger()

        self.config = config
        self.systems = config.systems()
        self.templar = templar.Templar(config)

    def what(self):
        return "ndjbdns"

    def regen_hosts(self):
        pass

    def write_dns_files(self):
        template_file = '/etc/cobbler/ndjbdns.template'
        data_file = '/etc/ndjbdns/data'
        data_dir = os.path.dirname(data_file)

        a_records = {}

        with open(template_file, 'r') as f:
            template_content = f.read()

        for system in self.systems:
            for (name, interface) in system.interfaces.iteritems():
                host = interface['dns_name']
                ip = interface['ip_address']

                if host:
                    if host in a_records:
                        raise Exception('Duplicate DNS name: %s' % host)
                    a_records[host] = ip

        template_vars = {'forward': []}
        for host, ip in a_records.items():
            template_vars['forward'].append((host, ip))

        self.templar.render(template_content, template_vars, data_file)

        p = subprocess.Popen(['/usr/bin/tinydns-data'], cwd=data_dir)
        p.communicate()

        if p.returncode is not 0:
            raise Exception('Could not regenerate tinydns data file.')
