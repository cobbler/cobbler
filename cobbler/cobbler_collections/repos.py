"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import os.path

from cobbler.cobbler_collections import collection
from cobbler.items import repo
from cobbler import utils
from cobbler.cexceptions import CX


class Repos(collection.Collection):
    """
    Repositories in Cobbler are way to create a local mirror of a yum repository.
    When used in conjunction with a mirrored distro tree (see "cobbler import"),
    outside bandwidth needs can be reduced and/or eliminated.
    """

    @staticmethod
    def collection_type() -> str:
        return "repo"

    @staticmethod
    def collection_types() -> str:
        return "repos"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_repo = repo.Repo(api)
        new_repo.from_dict(item_dict)
        return new_repo

    def remove(self, name, with_delete: bool = True, with_sync: bool = True, with_triggers: bool = True,
               recursive: bool = False):
        """
        Remove element named 'name' from the collection

        :raises CX: In case the object does not exist.
        """
        # NOTE: with_delete isn't currently meaningful for repos
        # but is left in for consistancy in the API.  Unused.
        name = name.lower()
        obj = self.find(name=name)
        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/repo/pre/*", [])

        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/repo/post/*", [])
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/change/*", [])

            path = os.path.join(self.api.settings().webdir, "repo_mirror", obj.name)
            if os.path.exists(path):
                utils.rmtree(path)
