#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "1.6.4"
SHORT_DESC = "Network install tool for use with Cobbler"
LONG_DESC = """
Koan is a helper tool for use with 'cobbler'.  It allows for
network installation of new virtualized guests, updating files, 
and reinstallation of an existing system.
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
                scripts = ["koan/koan", "koan/cobbler-register"],
                data_files = [
				("/var/spool/koan", []),
				(manpath, ['koan.1.gz']),
				(manpath, ['cobbler-register.1.gz']),
                                (logpath, [])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )
