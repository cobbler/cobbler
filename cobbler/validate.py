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
import shlex
import os.path

import netaddr

from cobbler.cexceptions import CX


KICKSTART_TEMPLATE_BASE_DIR = "/var/lib/cobbler/kickstarts/"
SNIPPET_TEMPLATE_BASE_DIR = "/var/lib/cobbler/snippets/"

RE_OBJECT_NAME = re.compile(r'[a-zA-Z0-9_\-.:]*$')
RE_HOSTNAME = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$')

VALID_REPO_BREEDS = [
    "rsync", "rhn", "yum", "apt", "wget"
]


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


def snippet_file_path(snippet):
    """
    Validate the snippet file path.

    @param: str snippet (absolute path to a local snippet file)
    @returns: str snippet or CX
    """
    if not isinstance(snippet, basestring):
        raise CX("Invalid input, snippet must be a string")
    else:
        snippet = snippet.strip()

    if snippet.find("..") != -1:
        raise CX("Invalid snippet template file location %s, must be absolute path" % snippet)

    if not snippet.startswith(SNIPPET_TEMPLATE_BASE_DIR):
        raise CX("Invalid snippet template file location %s, it is not inside %s" % (snippet, SNIPPET_TEMPLATE_BASE_DIR))

    if not os.path.isfile(snippet):
        raise CX("Invalid snippet template file location %s, file not found" % snippet)

    return snippet


def kickstart_file_path(kickstart, for_item=True, new_kickstart=False):
    """
    Validate the kickstart file path.

    @param: str kickstart (absolute path to a local kickstart file)
    @param: bool for_item (enable/disable special handling for Item objects)
    @param: bool new_kickstart (when set to true new filenames are allowed)
    @returns: str kickstart or CX
    """
    if not isinstance(kickstart, basestring):
        raise CX("Invalid input, kickstart must be a string")
    else:
        kickstart = kickstart.strip()

    if kickstart == "":
        # empty kickstart is allowed (interactive installations)
        return kickstart

    if for_item is True:
        # this kickstart value has special meaning for Items
        # other callers of this function have no use for this
        if kickstart == "<<inherit>>":
            return kickstart

    if kickstart.find("..") != -1:
        raise CX("Invalid kickstart template file location %s, must be absolute path" % kickstart)

    if not kickstart.startswith(KICKSTART_TEMPLATE_BASE_DIR):
        raise CX("Invalid kickstart template file location %s, it is not inside %s" % (kickstart, KICKSTART_TEMPLATE_BASE_DIR))

    if not os.path.isfile(kickstart) and not new_kickstart:
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
        # hostname is not required
        return dnsname

    if not RE_HOSTNAME.match(dnsname):
        raise CX("Invalid hostname format (%s)" % dnsname)

    return dnsname


def mac_address(mac, for_item=True):
    """
    Validate as an Eternet mac address.

    @param: str mac (mac address)
    @returns: str mac or CX
    """
    if not isinstance(mac, basestring):
        raise CX("Invalid input, mac must be a string")
    else:
        mac = mac.lower().strip()

    if for_item is True:
        # this value has special meaning for items
        if mac == "random":
            return mac

    if not netaddr.valid_mac(mac):
        raise CX("Invalid mac address format (%s)" % mac)

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

    if not netaddr.valid_ipv4(addr):
        raise CX("Invalid IPv4 address format (%s)" % addr)

    if netaddr.IPAddress(addr).is_netmask():
        raise CX("Invalid IPv4 host address (%s)" % addr)

    return addr


def ipv4_netmask(addr):
    """
    Validate an IPv4 netmask.

    @param: str addr (ipv4 netmask)
    @returns: str addr or CX
    """
    if not isinstance(addr, basestring):
        raise CX("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv4(addr):
        raise CX("Invalid IPv4 address format (%s)" % addr)

    if not netaddr.IPAddress(addr).is_netmask():
        raise CX("Invalid IPv4 netmask (%s)" % addr)

    return addr


def ipv6_address(addr):
    """
    Validate an IPv6 address.

    @param: str addr (ipv6 address)
    @returns: str addr or CX
    """
    if not isinstance(addr, basestring):
        raise CX("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv6(addr):
        raise CX("Invalid IPv6 address format (%s)" % addr)

    return addr


def name_servers(nameservers, for_item=True):
    """
    Validate nameservers IP addresses, works for IPv4 and IPv6

    @param: str/list nameservers (string or list of nameserver addresses)
    @param: bool for_item (enable/disable special handling for Item objects)
    """
    if isinstance(nameservers, basestring):
        nameservers = nameservers.strip()
        if for_item is True:
            # special handling for Items
            if nameservers in ["<<inherit>>", ""]:
                nameservers = "<<inherit>>"
                return nameservers

        # convert string to a list; do the real validation
        # in the isinstance(list) code block below
        nameservers = shlex.split(nameservers)

    if isinstance(nameservers, list):
        for ns in nameservers:
            ip_version = netaddr.IPAddress(ns).version
            if ip_version == 4:
                ipv4_address(ns)
            elif ip_version == 6:
                ipv6_address(ns)
            else:
                raise CX("Invalid IP address format")
    else:
        raise CX("Invalid input type %s, expected str or list" % type(nameservers))

    return nameservers


def name_servers_search(search, for_item=True):
    """
    Validate nameservers search domains.

    @param: str/list search (string or list of search domains)
    @param: bool for_item (enable/disable special handling for Item objects)
    """
    if isinstance(search, basestring):
        search = search.strip()
        if for_item is True:
            # special handling for Items
            if search in ["<<inherit>>", ""]:
                search = "<<inherit>>"
                return search

        # convert string to a list; do the real validation
        # in the isinstance(list) code block below
        search = shlex.split(search)

    if isinstance(search, list):
        for sl in search:
            hostname(sl)
    else:
        raise CX("Invalid input type %s, expected str or list" % type(search))

    return search

# EOF
