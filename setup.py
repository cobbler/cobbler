#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.3.5"
SHORT_DESC = "Boot server configurator"
LONG_DESC = """
Cobbler is a command line tool for configuration of boot/provisioning servers.  It is also accessible as a Python library.  Cobbler supports PXE, provisioning virtualized ("virt") images, and reinstalling machines that are already up and running (over SSH).  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from rsync mirrors, kickstart templating, and managing dhcpd.conf.
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
                url = "http://cobbler.et.redhat.com/",
                license = "GPL",
                packages = ["cobbler","cobbler/yaml"],
                scripts = ["cobbler/cobbler"],
                data_files = [
                                # (docspath, ['README']),
                                (wwwpath, []),
                                (cobpath, ['elilo-3.6-ia64.efi']),
                                (etcpath, ['kickstart_fc5.ks']),
                                (etcpath, ['default.ks']),
				(etcpath, ['dhcp.template']),
				(etcpath, ['default.pxe']),
                                (manpath, ['cobbler.1.gz']),
                                (etcpath, ['rsync.exclude'])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

