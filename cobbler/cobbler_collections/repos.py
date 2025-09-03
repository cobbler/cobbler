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
        ref: repo.Repo,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ):
        """
        Remove the given element from the collection

        :param ref: The object to delete
        :param with_delete: In case the deletion triggers are executed for this repository.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this repository references.
        :param rebuild_menu: unused
        :raises CX: Raised in case you want to delete a none existing repository.
        """
        # rebuild_menu is not used
        _ = rebuild_menu

        if ref is None:  # type: ignore
            raise CX("cannot delete an object that does not exist")

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/repo/pre/*", []
                )

        with self.lock:
            self.remove_from_indexes(ref)
            del self.listing[ref.uid]
        self.collection_mgr.serialize_delete(self, ref)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/repo/post/*", []
                )
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )

            path = os.path.join(self.api.settings().webdir, "repo_mirror", ref.name)
            if os.path.exists(path):
                filesystem_helpers.rmtree(path)

    def remove_quick_pxe_sync(self, ref: repo.Repo, rebuild_menu: bool = True) -> None:
        # Nothing to do for repos
        pass
