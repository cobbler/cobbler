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
        self.datadir = '/etc/ndjbdns'

    def what(self):
        return "ndjbdns"

    def regen_hosts(self):
        pass

    def write_dns_files(self):
        a_records = {}
        for system in self.systems:
            for (name, interface) in system.interfaces.iteritems():
                host = interface['dns_name']
                ip = interface['ip_address']

                if host:
                    if host in a_records:
                        raise Exception('Duplicate DNS name: %s' % host)
                    a_records[host] = ip

        self.logger.info('Writing data file.')
        with open('%s/data.new' % self.datadir, 'w') as datafile:
            with open('%s/data.static' % self.datadir, 'r') as staticfile:
                datafile.write(staticfile.read())
            datafile.write("\n")

            for host, ip in a_records.items():
                datafile.write("=%s:%s\n" % (host, ip))

        os.rename('%s/data.new' % self.datadir, '%s/data' % self.datadir)
        self.logger.info('Wrote data file.')

        p = subprocess.Popen(['/usr/bin/tinydns-data'], cwd=self.datadir)
        p.communicate()

        if p.returncode is not 0:
            raise Exception('tinydns-data is broken!')
