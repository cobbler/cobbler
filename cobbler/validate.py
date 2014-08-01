"""
Copyright 2014. Jorgen Maas <jorgen.maas@gmail.com>

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
import os.path

from cobbler.cexceptions import CX


KICKSTART_TEMPLATE_BASE_DIR = "/var/lib/cobbler/kickstarts/"
KICKSTART_SNIPPET_BASE_DIR = "/var/lib/cobbler/snippets/"

RE_OBJECT_NAME = re.compile(r'[a-zA-Z0-9_\-.:]*$')
RE_MAC_ADDRESS = re.compile(':'.join(('[0-9A-Fa-f][0-9A-Fa-f]',) * 6) + '$')
RE_INFINIBAND_MAC_ADDRESS = re.compile(':'.join(('[0-9A-Fa-f][0-9A-Fa-f]',) * 20) + '$')
RE_IPV4_ADDRESS = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
RE_HOSTNAME = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$')


def object_name(name, parent):
    """
    Validate the object name.

    @param: str name (object name)
    @param: str parent (parent object name)
    @returns: str name or CX
    """
    if not isinstance(name, basestring) or not isinstance(parent, basestring):
        raise CX("Invalid input, name and parent must be strings")
    else:
        name = name.strip()
        parent = parent.strip()

    if name != "" and parent != "" and name == parent:
        raise CX("Self parentage is not allowed")

    if not RE_OBJECT_NAME.match(name):
        raise CX("Invalid characters in name: '%s'" % name)

    return name


def kickstart_file_path(kickstart):
    """
    Validate the kickstart file path.

    @param: str kickstart (absolute path to a local kickstart file)
    @returns: str kickstart or CX
    """
    if not isinstance(kickstart, basestring):
        raise CX("Invalid input, kickstart must be a string")
    else:
        kickstart = kickstart.strip()

    if kickstart == "<<inherit>>" or kickstart == "":
        return kickstart

    if kickstart.find("..") != -1:
        raise CX("Invalid kickstart template file location %s, must be absolute path" % kickstart)

    if not kickstart.startswith(KICKSTART_TEMPLATE_BASE_DIR):
        raise CX("Invalid kickstart template file location %s, it is not inside %s" % (kickstart, KICKSTART_TEMPLATE_BASE_DIR))

    if not os.path.isfile(kickstart):
        raise CX("Invalid kickstart template file location %s, file not found" % kickstart)

    return kickstart


def hostname(dnsname):
    """
    Validate the dns name.

    @param: str dnsname (hostname or fqdn)
    @returns: str dnsname or CX
    """
    if not isinstance(dnsname, basestring):
        raise CX("Invalid input, dnsname must be a string")
    else:
        dnsname = dnsname.strip()

    if dnsname == "":
        return dnsname

    if not RE_HOSTNAME.match(dnsname):
        raise CX("Invalid hostname format")

    return dnsname


def mac_address(mac):
    """
    Validate mac as an Infiniband mac address aswell
    as an Eternet mac address.

    @param: str mac (mac address)
    @returns: str mac or CX
    """
    if not isinstance(mac, basestring):
        raise CX("Invalid input, mac must be a string")
    else:
        mac = mac.strip()

    if mac == "random":
        return mac

    if not RE_MAC_ADDRESS.match(mac) or not RE_INFINIBAND_MAC_ADDRESS.match(mac):
        raise CX("Invalid mac address format")

    return mac


def ipv4_address(addr):
    """
    Validate an IPv4 address.

    @param: str addr (ipv4 address)
    @returns: str addr or CX
    """
    if not isinstance(addr, basestring):
        raise CX("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not RE_IPV4_ADDRESS.match(addr):
        raise CX("Invalid IPv4 address format")

    return addr


# EOF
