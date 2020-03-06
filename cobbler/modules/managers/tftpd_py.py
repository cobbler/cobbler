"""
This is some of the code behind 'cobbler sync'.

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
import cobbler.clogger as clogger
import cobbler.tftpgen as tftpgen
import cobbler.templar as templar


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "manage"


class TftpdPyManager(object):

    def what(self):
        return "tftpd"

    def __init__(self, collection_mgr, logger):
        """
        Constructor
        """
        self.logger = logger
        if self.logger is None:
            self.logger = clogger.Logger()

        self.collection_mgr = collection_mgr
        self.bootloc = collection_mgr.settings().tftpboot_location
        self.templar = templar.Templar(collection_mgr)

    def regen_hosts(self):
        pass        # not used

    def write_dns_files(self):
        pass        # not used

    def write_boot_files_distro(self, distro):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        pass        # not used.  Handed by tftp.py

    def write_boot_files(self):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        pass        # not used.  Handed by tftp.py

    def add_single_distro(self, distro):
        pass        # not used

    def sync(self, verbose=True):
        """
        Write out files to /tftpdboot.  Mostly unused for the python server
        """
        self.logger.info("copying bootloaders")
        tftpgen.TFTPGen(self.collection_mgr, self.logger).copy_bootloaders(self.bootloc)

    def update_netboot(self, name):
        """
        Write out files to /tftpdboot.  Unused for the python server
        """
        pass

    def add_single_system(self, name):
        """
        Write out files to /tftpdboot.  Unused for the python server
        """
        pass


def get_manager(collection_mgr, logger):
    return TftpdPyManager(collection_mgr, logger)
