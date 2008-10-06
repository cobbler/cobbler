"""
Repositories in cobbler are way to create a local mirror of a yum repository.
When used in conjunction with a mirrored kickstart tree (see "cobbler import")
outside bandwidth needs can be reduced and/or eliminated.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
        if seed_data.has_key('breed'):
            if seed_data['breed'] == "rsync":
                return repo.RsyncRepo(config).from_datastruct(seed_data)
            elif seed_data['breed'] == "rhn":
                return repo.RhnRepo(config).from_datastruct(seed_data)
            elif seed_data['breed'] == "yum":
                return repo.YumRepo(config).from_datastruct(seed_data)
            elif seed_data['breed'] == "apt":
                return repo.AptRepo(config).from_datastruct(seed_data)
            else:
                raise CX(_("Uknown repository breed %s")%seed_data['breed'])
        # Required until rsync breed is properly set on every required case
        # Block, taken from is_rsync_mirror
        lower = seed_data.get("mirror")
        print "hola tu",lower
        if not ( lower.startswith("http://") or lower.startswith("ftp://") or lower.startswith("rhn://") ):
            seed_data['breed'] = "rsync"
            print "adios tu",seed_data['breed']
            return repo.RsyncRepo(config).from_datastruct(seed_data)
        # 
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

