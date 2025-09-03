"""
Cobbler module that at runtime holds all profiles in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import profile

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Profiles(collection.Collection[profile.Profile]):
    """
    A profile represents a distro paired with an automatic OS installation template file.
    """

    @staticmethod
    def collection_type() -> str:
        return "profile"

    @staticmethod
    def collection_types() -> str:
        return "profiles"

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[Any, Any]):
        """
        Return a Distro forged from seed_data
        """
        return profile.Profile(self.api, **seed_data)

    def remove(
        self,
        ref: profile.Profile,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ):
        """
        Remove the given element from the collection

        :param ref: The object to delete
        :param with_delete: In case the deletion triggers are executed for this profile.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this profile references.
        :param rebuild_menu: unused
        :raises CX: In case the reference to the object was not given.
        """
        if ref is None:  # type: ignore
            raise CX("cannot delete an object that does not exist")

        if not recursive:
            search_result = self.api.find_system(True, profile=ref.uid)
            if isinstance(search_result, list) and len(search_result) > 0:
                raise CX(
                    f"removal would orphan the following system(s): {', '.join([ref.uid for ref in search_result])}"
                )

        if recursive:
            kids = ref.descendants
            kids.sort(key=lambda x: -x.depth)
            for k in kids:
                self.api.remove_item(
                    k.COLLECTION_TYPE,
                    k,
                    recursive=False,
                    delete=with_delete,
                    with_triggers=with_triggers,
                    with_sync=with_sync,
                )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/profile/pre/*", []
                )

        with self.lock:
            self.remove_from_indexes(ref)
            del self.listing[ref.uid]
        self.collection_mgr.serialize_delete(self, ref)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/profile/post/*", []
                )
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )
            if with_sync:
                self.remove_quick_pxe_sync(ref)

    def remove_quick_pxe_sync(
        self, ref: profile.Profile, rebuild_menu: bool = True
    ) -> None:
        self.api.get_sync().remove_single_profile(ref, rebuild_menu=rebuild_menu)
