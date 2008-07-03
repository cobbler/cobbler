"""
Repositories in cobbler are way to create a local mirror of a yum repository.
When used in conjunction with a mirrored kickstart tree (see "cobbler import")
outside bandwidth needs can be reduced and/or eliminated.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import item_repo as repo
import utils
import collection
from cexceptions import *
from utils import _


TESTMODE = False

#--------------------------------------------

class Repos(collection.Collection):

    def collection_type(self):
        return "repo"

    def factory_produce(self,config,seed_data):
        """
        Return a system forged from seed_data
        """
        return repo.Repo(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=False):
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
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/repo/pre/*")

            del self.listing[name]
            self.config.serialize_delete(self, obj)

            if with_delete:
                self.log_func("deleted repo %s" % name)
                if with_triggers: 
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/repo/post/*")
            return True
        raise CX(_("cannot delete an object that does not exist: %s") % name)

