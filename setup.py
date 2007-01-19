#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.3.7"
SHORT_DESC = "Boot and update server configurator"
LONG_DESC = """
Cobbler is a command line tool for configuration of boot/provisioning, and update servers which is also accessible as a Python library.  Cobbler supports PXE, provisioning virtualized images, and reinstalling machines that are already up and running (over SSH).  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from rsync mirrors, kickstart templating, integrated yum mirroring (and linking repository setup with kickstarts), plus managing dhcpd.conf.
"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath  = "share/man/man1/"
        cobpath  = "/var/lib/cobbler/"
        etcpath  = "/etc/cobbler/"
        wwwpath  = "/var/www/cobbler/"
        logpath  = "/var/log/cobbler/"
        logpath2 = "/var/log/cobbler/kicklog"
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
                                (wwwpath,  ['watcher.py']),
                                (cobpath,  ['elilo-3.6-ia64.efi']),
                                (etcpath,  ['kickstart_fc5.ks']),
                                (etcpath,  ['default.ks']),
				(etcpath,  ['dhcp.template']),
				(etcpath,  ['default.pxe']),
                                (manpath,  ['cobbler.1.gz']),
                                (etcpath,  ['rsync.exclude']),
                                (logpath,  []),
                                (logpath2, [])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

