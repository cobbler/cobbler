"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Xen, there are many
additional options, with client-side defaults (not kept here).

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import item_profile as profile
import utils
import collection
import cexceptions

TESTMODE = False

#--------------------------------------------

class Profiles(collection.Collection):

    def collection_type(self):
        return "profile"

    def factory_produce(self,config,seed_data):
        return profile.Profile(config).from_datastruct(seed_data)

    def filename(self):
        if TESTMODE:
            return "/var/lib/cobbler/test/profiles"
        else:
            return "/var/lib/cobbler/profiles"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        for v in self.config.systems():
           if v.profile == name:
               raise cexceptions.CobblerException("orphan_system",v.name)
        if self.find(name):
            del self.listing[name]
            return True
        raise cexceptions.CobblerException("delete_nothing")

