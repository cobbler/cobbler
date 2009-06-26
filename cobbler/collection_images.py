"""
A image instance represents a ISO or virt image we want to track
and repeatedly install.  It differs from a answer-file based installation.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import item_image as image
import utils
import collection
from cexceptions import *
from utils import _
import action_litesync

#--------------------------------------------

class Images(collection.Collection):

    def collection_type(self):
        return "image"

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=True, logger=logger):
        """
        Remove element named 'name' from the collection
        """

        # NOTE: with_delete isn't currently meaningful for repos
        # but is left in for consistancy in the API.  Unused.

        name = name.lower()

        # first see if any Groups use this distro
        if not recursive:
            for v in self.config.systems():
                if v.image is not None and v.image.lower() == name:
                    raise CX(_("removal would orphan system: %s") % v.name)

        obj = self.find(name=name)

        if obj is not None:

            if recursive:
                kids = obj.get_children()
                for k in kids:
                    self.config.api.remove_system(k, recursive=True, logger=logger)

            if with_delete:
                if with_triggers:
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/image/pre/*")
                if with_sync:
                    lite_sync = action_litesync.BootLiteSync(self.config, logger=logger)
                    lite_sync.remove_single_image(name)

            del self.listing[name]
            self.config.serialize_delete(self, obj)

            if with_delete:
                self.log_func("deleted repo %s" % name)
                if with_triggers:
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/image/post/*")
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/change/*")

            return True

        raise CX(_("cannot delete an object that does not exist: %s") % name)
