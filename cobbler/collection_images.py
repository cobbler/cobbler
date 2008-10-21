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

    def factory_produce(self,config,seed_data):
        return image.Image(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=True):
        """
        Remove element named 'name' from the collection
        """

        # NOTE: with_delete isn't currently meaningful for repos
        # but is left in for consistancy in the API.  Unused.

        name = name.lower()
        obj = self.find(name=name)
        if obj is not None:
            if with_delete:
                if with_triggers:
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/image/pre/*")
                if with_sync:
                    lite_sync = action_litesync.BootLiteSync(self.config)
                    lite_sync.remove_single_image(name)

            del self.listing[name]
            self.config.serialize_delete(self, obj)

            if with_delete:
                self.log_func("deleted repo %s" % name)
                if with_triggers:
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/image/post/*")
            return True
        raise CX(_("cannot delete an object that does not exist: %s") % name)

