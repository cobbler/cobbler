#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "1.3.1"
SHORT_DESC = "Network install tool for use with Cobbler"
LONG_DESC = """
koan stands for "kickstart-over-a-network" and allows for both
network installation of new virtualized guests and reinstallation of
existing systems.  For use with a boot-server configured with
'cobbler'.
"""

if __name__ == "__main__":
        docspath="share/doc/koan-%s/" % VERSION
        manpath="share/man/man1/"
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
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )
