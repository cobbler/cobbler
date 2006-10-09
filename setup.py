#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.2.3"
SHORT_DESC = "Boot server configurator"
LONG_DESC = """
Cobbler is a command line tool for simplified configuration of boot/provisioning servers.  It is also accessible as a Python library.  Cobbler supports PXE, Xen, and re-provisioning an existing Linux system via auto-kickstart.  The last two modes require 'koan' to be run on the remote system.

"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath="share/man/man1/"
        cobpath="/var/lib/cobbler/"
        etcpath="/etc/cobbler/"
        wwwpath="/var/www/cobbler/"
        setup(
                name="cobbler",
                version = VERSION,
                author = "Michael DeHaan",
                author_email = "mdehaan@redhat.com",
                url = "http://et.redhat.com/",
                license = "GPL",
                packages = ["cobbler","cobbler/yaml"],
                scripts = ["cobbler/cobbler"],
                data_files = [
                                # (docspath, ['README']),
                                (wwwpath, []),
                                (cobpath, ['elilo-3.6-ia64.efi']),
				(etcpath, ['dhcp.template']),
                                (manpath, ['cobbler.1.gz'])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

