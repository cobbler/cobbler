"""
A distro represents a network bootable matched set of kernels
and initrd files

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import utils
import collection
import item_distro as distro
import cexceptions

class Distros(collection.Collection):

    def collection_type(self):
        return "distribution"

    def factory_produce(self,config,seed_data):
        """
        Return a Distro forged from seed_data
        """
        return distro.Distro(config).from_datastruct(seed_data)

    def filename(self):
        """
        Config file for distro serialization
        """
        return "/var/lib/cobbler/distros"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        # first see if any Groups use this distro
        for v in self.config.profiles():
            if v.distro == name:
               raise cexceptions.CobblerException("orphan_profile",v.name)
        if self.find(name):
            del self.listing[name]
            return True
        raise cexceptions.CobblerException("delete_nothing")

