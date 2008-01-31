#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.6.5"
SHORT_DESC = "Network provisioning tool for use with Cobbler"
LONG_DESC = """
koan stands for "kickstart-over-a-network" and allows for both
network provisioning of new virtualized guests and destructive provisioning of
any existing system.  For use with a boot-server configured with
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
