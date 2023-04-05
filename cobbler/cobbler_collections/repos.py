"""
Cobbler module that at runtime holds all repos in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os.path
from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import repo
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Repos(collection.Collection[repo.Repo]):
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

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[str, Any]):
        """
        Return a Distro forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: The data the object is initalized with.
        :returns: The created repository.
        """
        return repo.Repo(self.api, **seed_data)

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ):
        """
        Remove element named 'name' from the collection

        :raises CX: In case the object does not exist.
        """
        # NOTE: with_delete isn't currently meaningful for repos
        # but is left in for consistancy in the API.  Unused.
        obj = self.find(name=name)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        if isinstance(obj, list):
            # Will never happen, but we want to make mypy happy.
            raise CX("Ambiguous match detected!")

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/repo/pre/*", []
                )

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/repo/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )

            path = os.path.join(self.api.settings().webdir, "repo_mirror", obj.name)
            if os.path.exists(path):
                filesystem_helpers.rmtree(path)
