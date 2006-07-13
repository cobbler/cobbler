#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.1.1"
SHORT_DESC = "Boot server configurator"
LONG_DESC = """
Cobbler is a command line tool for simplified configuration of boot/provisioning servers.  It is also accessible as a Python library.  Cobbler supports PXE, Xen, and re-provisioning an existing Linux system via auto-kickstart.  The last two modes require 'koan' to be run on the remote system.

"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath="share/man/man1/"
        setup(
                name="cobbler",
                version = VERSION,
                author = "Michael DeHaan",
                author_email = "mdehaan@redhat.com",
                # FIXME: lame, this should point to a real cobbler webpage
                url = "http://bugzilla.redhat.com",
                license = "GPL",
                packages = ["cobbler","cobbler/yaml"],
                scripts = ["cobbler/cobbler"],
                data_files = [
                                # (docspath, ['README']),
                                (manpath, ['cobbler.1.gz'])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

