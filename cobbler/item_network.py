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
from cexceptions import *
from utils import _, _IP, _CIDR

class Network(item.Item):

    TYPE_NAME = _("network")
    COLLECTION_TYPE = "network"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Network(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        self.name             = None
        self.cidr             = None
        self.address          = None
        self.gateway          = None
        self.broadcast        = None
        self.nameservers      = []
        self.reserved         = []
        self.used_addresses   = []
        self.free_addresses   = []
        self.comment          = ""

    def from_datastruct(self,seed_data):
        self.name             = self.load_item(seed_data, 'name')
        self.cidr             = _CIDR(self.load_item(seed_data, 'cidr'))
        self.address          = _IP(self.load_item(seed_data, 'address', self.cidr[0]))
        self.gateway          = _IP(self.load_item(seed_data, 'gateway', self.cidr[-2]))
        self.broadcast        = _IP(self.load_item(seed_data, 'broadcast', self.cidr[-1]))
        self.nameservers      = [_IP(i) for i in self.load_item(seed_data, 'nameservers', [])]
        self.reserved         = [_CIDR(c) for c in self.load_item(seed_data, 'reserved', [])]
        self.used_addresses   = [_IP(i) for i in self.load_item(seed_data, 'used_addresses', [])]
        self.free_addresses   = [_CIDR(c) for c in self.load_item(seed_data, 'free_addresses', [])]
        self.comment          = self.load_item(seed_data, 'comment', '')

        return self

    def set_cidr(self, cidr):
        self.cidr = _CIDR(cidr)

    def set_address(self, address):
        self.address = _IP(address)

    def set_gateway(self, gateway):
        self.gateway = _IP(gateway)

    def set_broadcast(self, broadcast):
        self.broadcast = _IP(broadcast)

    def set_nameservers(self, nameservers):
        nameservers = [s.strip() for s in nameservers.split(',')]
        self.nameservers = [_IP(i) for i in nameservers]

    def set_reserved(self, reserved):
        reserved = [s.strip() for s in reserved.split(',')]
        self.reserved = [_CIDR(c) for c in reserved]

#    def set_used_addresses(self, used_addresses):
#        pass

#    def set_free_addresses(self, free_addresses):
#        pass

    def subtract_and_flatten(self, cidr_list, remove_list):
        for item in remove_list:
            for i in range(len(cidr_list)):
                if item in cidr_list[i]:
                    cidr_list += cidr_list[i] - item
                    del(cidr_list[i])
                    break
        return cidr_list

    def add_existing_interfaces(self):
        for s in self.config.systems():
            for i in s.interfaces:
                pass

    def remove_existing_interfaces(self):
        for s in self.config.systems():
            for i in s.interfaces:
                pass

    def add_interface(self, system, interface):
        ip = interface['ip_address']
        if ip == 'auto' or ip == '' or ip == None:
            return self.add_auto_interface(system, interface)

        ip = _IP(ip)
        if ip not in self.cidr:
            raise CX(_("Address (%s) not in %s (%s)" % (ip,
                                                        self.name,
                                                        self.cidr)))
        available = False
        for block in self.free_addresses:
            if ip in block:
                available = True
                break
        if not available:
            raise CX(_("Address %s is not free in network %s" % (ip, self.name)))

        self.used_addresses.append(ip)
        print self.used_addresses
        self.update_free()
        print self.used_addresses

    def sync(self, action):
        if action == 'add':
            self.add_existing_interfaces()
        elif action == 'edit':
            # horribly inefficient
            self.remove_existing_interfaces()
            self.add_existing_interfaces()
        elif action == 'remove':
            self.remove_existing_interfaces()

        self.update_free()

    def update_free(self):
        free = [self.cidr]

        #remove all the taken addresses
        self.free_addresses = self.subtract_and_flatten(free,
                                   self.reserved +
                                   self.used_addresses +
                                   [self.address] +
                                   [self.gateway] +
                                   [self.broadcast])

    def used_address_count(self):
        return len(self.used_addresses)

    def free_address_count(self):
        total = 0
        for item in self.free_addresses:
            total += len(item)
        return total

    def is_valid(self):
        """
	A network is valid if:
          * it has a name and a CIDR
          * it does not overlap another network
	"""
        if self.name is None:
            raise CX(_("name is required"))
        if self.cidr is None:
            raise CX(_("cidr is required"))
        for other in self.config.networks():
            if other.name == self.name:
                continue
            if self.cidr in other.cidr or other.cidr in self.cidr:
                raise CX(_("cidr %s overlaps with network %s (%s)" % (self.cidr, other.name, other.cidr)))
        return True

    def to_datastruct(self):
        return {
            'name'           : self.name,
            'cidr'           : self.cidr,
            'address'        : self.address,
            'gateway'        : self.gateway,
            'broadcast'      : self.broadcast,
            'nameservers'    : self.nameservers,
            'reserved'       : self.reserved,
            'used_addresses' : self.used_addresses,
            'free_addresses' : self.free_addresses,
            'comment'        : self.comment
        }

    def printable(self):
        buf =       _("network          : %s\n") % self.name
        buf = buf + _("CIDR             : %s\n") % self.cidr
        buf = buf + _("gateway          : %s\n") % self.gateway
        buf = buf + _("network address  : %s\n") % self.address
        buf = buf + _("broadcast        : %s\n") % self.broadcast
        buf = buf + _("nameservers      : %s\n") % [str(i) for i in self.nameservers]
        buf = buf + _("reserved         : %s\n") % [str(i) for i in self.reserved]
        buf = buf + _("free addresses   : %s\n") % self.free_address_count()
        buf = buf + _("used addresses   : %s\n") % self.used_address_count()
        buf = buf + _("comment          : %s\n") % self.comment
        return buf

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.
        """
        return None

    def remote_methods(self):
        return {
            'name'           : self.set_name,
            'cidr'           : self.set_cidr,
            'address'        : self.set_address,
            'gateway'        : self.set_gateway,
            'broadcast'      : self.set_broadcast,
            'nameservers'    : self.set_nameservers,
            'reserved'       : self.set_reserved,
            'used_addresses' : self.set_used_addresses,
            'free_addresses' : self.set_free_addresses,
            'comment'        : self.set_comment
        }
