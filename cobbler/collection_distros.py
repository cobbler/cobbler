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
from cexceptions import *
import action_litesync
from rhpl.translate import _, N_, textdomain, utf8

class Distros(collection.Collection):

    def collection_type(self):
        return "distro"

    def factory_produce(self,config,seed_data):
        """
        Return a Distro forged from seed_data
        """
        return distro.Distro(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=False):
        """
        Remove element named 'name' from the collection
        """
        name = name.lower()

        # first see if any Groups use this distro
        if not recursive:
            for v in self.config.profiles():
                if v.distro.lower() == name:
                    raise CX(_("removal would orphan profile: %s") % v.name)

        obj = self.find(name=name)
        if obj is not None:
            if recursive:
                kids = obj.get_children()
                for k in kids:
                    self.config.api.remove_profile(k, recursive=True)

            if with_delete:
                if with_triggers: 
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/distro/pre/*")
                if with_sync:
                    lite_sync = action_litesync.BootLiteSync(self.config)
                    lite_sync.remove_single_profile(name)
            del self.listing[name]
            self.config.serialize_delete(self, obj)
            if with_delete:
                self.log_func("deleted distro %s" % name)
                if with_triggers: 
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/distro/post/*")
            return True
        raise CX(_("cannot delete object that does not exist: %s") % name)

