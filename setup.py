#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "1.5.0"
SHORT_DESC = "Network install tool for use with Cobbler"
LONG_DESC = """
Koan stands for kickstart-over-a-network and allows for both
network installation of new virtualized guests and reinstallation              
of an existing system.  For use with a boot-server configured with Cobbler
"""

if __name__ == "__main__":
        docspath="share/doc/koan-%s/" % VERSION
        manpath="share/man/man1/"
        logpath="/var/log/koan"
	setup(
                name="koan",
                version = VERSION,
                author = "Michael DeHaan",
                author_email = "mdehaan@redhat.com",
                url = "http://cobbler.et.redhat.com/",
                license = "GPL",
                packages = ["koan"],
                scripts = ["koan/koan"],
                data_files = [
				("/var/spool/koan", []),
				(manpath, ['koan.1.gz']),
                                (logpath, [])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )
