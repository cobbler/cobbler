#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.2.4"
SHORT_DESC = "Network provisioning tool for Virtualized Images and Existing Non-Bare Metal"
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
                packages = ["koan","koan/yaml"],
                scripts = ["koan/koan"],
                data_files = [
				(manpath, ['koan.1.gz']),
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )
