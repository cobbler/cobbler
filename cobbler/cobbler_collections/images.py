"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

from cobbler.cobbler_collections import collection
from cobbler.items import image as image
from cobbler import utils
from cobbler.cexceptions import CX


class Images(collection.Collection):
    """
    A image instance represents a ISO or virt image we want to track
    and repeatedly install.  It differs from a answer-file based installation.
    """

    @staticmethod
    def collection_type() -> str:
        return "image"

    @staticmethod
    def collection_types() -> str:
        return "images"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_image = image.Image(api, **item_dict)
        new_image.from_dict(item_dict)
        return new_image

    def remove(self, name, with_delete: bool = True, with_sync: bool = True, with_triggers: bool = True,
               recursive: bool = True):
        """
        Remove element named 'name' from the collection

        :raises CX: In case object does not exist or it would orhan a system.
        """
        # NOTE: with_delete isn't currently meaningful for repos but is left in for consistency in the API. Unused.
        name = name.lower()
        obj = self.find(name=name)
        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        # first see if any Groups use this distro
        if not recursive:
            for v in self.api.systems():
                if v.image is not None and v.image.lower() == name:
                    raise CX("removal would orphan system: %s" % v.name)

        if recursive:
            kids = obj.get_children()
            for k in kids:
                self.api.remove_system(k, recursive=True)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/image/pre/*", [])
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_image(name)

        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/image/post/*", [])
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/change/*", [])
