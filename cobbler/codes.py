"""
various codes and constants used by Cobbler

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import re

KICKSTART_TEMPLATE_BASE_DIR = "/var/lib/cobbler/kickstarts/"
SNIPPET_TEMPLATE_BASE_DIR = "/var/lib/cobbler/snippets/"

RE_OBJECT_NAME = re.compile(r'[a-zA-Z0-9_\-.:]*$')
RE_MAC_ADDRESS = re.compile(r'^([0-9a-f]{2}[-:]){5}[0-9a-f]{2}$')
RE_INFINIBAND_MAC_ADDRESS = re.compile(':'.join(('[0-9A-Fa-f][0-9A-Fa-f]',) * 20) + '$')
RE_IPV4_ADDRESS = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
RE_HOSTNAME = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$')


VALID_REPO_BREEDS = [
    "rsync", "rhn", "yum", "apt", "wget"
]


# EOF
