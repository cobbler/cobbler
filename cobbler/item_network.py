"""
A Cobbler repesentation of an IP network.

Copyright 2009, Red Hat, Inc
John Eckersberg <jeckersb@redhat.com>

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

import utils
import item
import time
from cexceptions import *
from utils import _, _IP, _CIDR

FIELDS = [
    [ "name",           None ],
    [ "cidr",           None ],
    [ "address",        None ],
    [ "gateway",        None ],
    [ "broadcast",      None ],
    [ "name_servers",   None ],
    [ "reserved",       None ],
    [ "used_addresses", None ],
    [ "free_addresses", None ],
    [ "comment",        ""   ],
    [ "ctime",          0    ],
    [ "mtime",          0    ],
    [ "owners",         "SETTINGS:default_ownership"],
    [ "uid",            None ],
]

class Network(item.Item):

    TYPE_NAME = _("network")
    COLLECTION_TYPE = "network"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Network(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        utils.clear_from_fields(self,FIELDS)

    def from_datastruct(self,seed_data):
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def set_cidr(self, cidr):
        if self.cidr == None:
            self.free_addresses = [_CIDR(cidr)]
        self.cidr = _CIDR(cidr)
        return True

    def set_address(self, address):
        address = address.strip()
        if address == "":
            self.address = address
        else:
            if self.address != None:
                self._add_to_free(address)
            self.address = _IP(address)
            self._remove_from_free(self.address)
        return True

    def set_gateway(self, gateway):
        gateway = gateway.strip()
        if gateway == "":
            self.gateway = gateway
        else:
            if self.gateway != None:
                self._add_to_free(gateway)
            self.gateway = _IP(gateway)
            self._remove_from_free(self.gateway)
        return True

    def set_broadcast(self, broadcast):
        broadcast = broadcast.strip()
        if broadcast == "":
            self.broadcast = broadcast
        else:
            if self.broadcast != None:
                self._add_to_free(broadcast)
            self.broadcast = _IP(broadcast)
            self._remove_from_free(self.broadcast)
        return True

    def set_name_servers(self, data):
        data = utils.input_string_or_list(data)
        self.name_servers = data
        return True

    def set_reserved(self, reserved):
        return True

    def set_used_addresses(self):
        # FIXME: what should this do?  It was missing before
        return True

    def set_free_addresses(self):
        # FIXME: what should this do?  It was missing before
        return True

    def get_assigned_address(self, system, intf):
        """
        Get the address in the network assigned to an interface of a system.
        """
        try:
            return str(self.used_addresses[(system, intf)])
        except KeyError:
            return None

    def subscribe_system(self, system, intf, ip=None):
        """
        Join a system to the network.  If ip is passed in, try to
        claim that specific address, otherwise just grab the first
        free address.
        """
        if not ip:
            if self.free_address_count() == 0:
                raise CX(_("Network %s has no free addresses" % self.cidr))
            ip = self.free_addresses[0][0]

        self._allocate_address(system, intf, ip)

    def unsubscribe_system(self, system, intf):
        """
        Remove a system from the network.  Allocate it's address back
        into the free pool.
        """
        addr = self.get_assigned_address(system, intf)
        if not addr:
            raise CX(_("Attempting to unsubscribe %s:%s from %s, but not subscribed" % (system, intf, self.name)))

        self._remove_from_used(addr)
        self._add_to_free(addr)

    def _addr_available(self, addr):
        """
        Is addr free in the network?
        """
        for cidr in self.free_addresses:
            if addr in cidr:
                return True
        return False

    def _add_to_free(self, addr, compact=True):
        """
        Add addr to the list of free addresses.  If compact is True,
        then take the list of CIDRs in free_addresses and compact it.
        """
        addr = _IP(addr).cidr()
        self.free_addresses.append(addr)
        if compact:
            self.free_addreses = self._compact(self.free_addresses)

    def _remove_from_free(self, addr):
        """
        Take addr off of the list of free addresses
        """
        self.free_addresses = self._subtract_and_flatten(self.free_addresses, [addr])
        self.free_addresses.sort()

    def _add_to_used(self, system, intf, addr):
        """
        Add system,intf with address to used_addresses.  Make sure no
        entry already exists.
        """
        if (system, intf) in self.used_addresses:
            # should really throw an error if it's already there
            # probably a sign something has gone wrong elsewhere
            raise CX(_("Trying to add %s to used_addresses but is already there!" % i))

        self.used_addresses[(system,intf)] = addr

    def _remove_from_used(self, addr):
        """
        Take addr off of the list of used addresses
        """
        for k,v in self.used_addresses.iteritems():
            if v == addr:
                del(self.used_addresses[k])
                return

    def _allocate_address(self, system, intf, addr):
        """
        Try to allocate addr to system on interface intf.
        """
        if not self._addr_available(addr):
            raise CX(_("Address %s is not available for allocation" % addr))
        self._remove_from_free(addr)
        self._add_to_used(system, intf, addr)

    def _subtract_and_flatten(self, cidr_list, remove_list):
        """
        For each item I in remove_list, find the cidr C in cidr_list
        that contains I.  Perform the subtraction C - I which returns
        a new minimal cidr list not containing I.  Replace C with this
        result, flattened out so we don't get multiple levels of
        lists.
        """
        for item in remove_list:
            for i in range(len(cidr_list)):
                if item in cidr_list[i]:
                    cidr_list += cidr_list[i] - item
                    del(cidr_list[i])
                    break
        return cidr_list

    def _compact(self, cidr_list, sort_first=True):
            """
            Compacts a list of CIDR objects down to a minimal-length list L
            such that the set of IP addresses contained in L is the same as
            the original.

            For example:
            [10.0.0.0/32, 10.0.0.1/32, 10.0.0.2/32, 10.0.0.3/32]
            becomes
            [10.0.0.0/30]
            """
            if len(cidr_list) <= 1:
                return cidr_list

            if sort_first:
                cidr_list.sort()

            did_compact = False
            skip_next = False
            compacted = []
            for i in range(1, len(cidr_list)):
                cur = cidr_list[i]
                prev = cidr_list[i-1]

                if skip_next:
                    skip_next = False
                    continue

                last = prev[-1]
                last += 1
                last = last.cidr()
                if last == cur[0].cidr() and prev.size() == cur.size():
                    compacted.append(CIDR('%s/%d' % (str(prev[0]), prev.prefixlen - 1)))
                    did_compact = True
                    skip_next = True

                if did_compact:
                    return compact(compacted, sort_first=False)
                else:
                    return cidr_list


    def used_address_count(self):
        return len(self.used_addresses)

    def free_address_count(self):
        total = 0
        for item in self.free_addresses:
            total += len(item)
        return total

    def to_datastruct(self):
        # FIXME: can't store things as native python-netaddr objects here
        # and therefore should do that in indiv. set_* functions
        # until then this class really doesn't work.
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.
        """
        return None

    def remote_methods(self):
        return utils.get_remote_methods_from_fields(self,FIELDS)


