#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.2.1"
SHORT_DESC = "Network provisioning tool for Xen and Existing Non-Bare Metal"
LONG_DESC = """
koan standards for "kickstart-over-a-network" and allows for both
network provisioning of new Xen guests and destructive provisioning of
any existing system.  For use with a boot-server configured with
'cobbler'
"""

if __name__ == "__main__":
        docspath="share/doc/koan-%s/" % VERSION
        manpath="share/man/man1/"
	setup(
                name="koan",
                version = VERSION,
                author = "Michael DeHaan",
                author_email = "mdehaan@redhat.com",
                # FIXME: lame, this should point to a real prm webpage
                url = "http://bugzilla.redhat.com",
                license = "GPL",
                packages = ["koan","koan/yaml"],
                scripts = ["koan/koan"],
                data_files = [
				(manpath, ['koan.1.gz']),
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )
