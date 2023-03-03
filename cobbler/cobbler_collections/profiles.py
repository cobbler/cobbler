"""
Cobbler module that at runtime holds all profiles in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from cobbler.cobbler_collections import collection
from cobbler.items import profile as profile
from cobbler import utils
from cobbler.cexceptions import CX


class Profiles(collection.Collection):
    """
    A profile represents a distro paired with an automatic OS installation template file.
    """

    @staticmethod
    def collection_type() -> str:
        return "profile"

    @staticmethod
    def collection_types() -> str:
        return "profiles"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_profile = profile.Profile(api)
        new_profile.from_dict(item_dict)
        return new_profile

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

        :raises CX: In case the name of the object was not given or any other descendant would be orphaned.
        """
        if not recursive:
            for system in self.api.systems():
                if system.profile is not None and system.profile == name:
                    raise CX(f"removal would orphan system: {system.name}")

        obj = self.find(name=name)
        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        if recursive:
            kids = obj.descendants
            kids.sort(key=lambda x: -x.depth)
            for k in kids:
                self.api.remove_item(
                    k.COLLECTION_TYPE,
                    k,
                    recursive=False,
                    delete=with_delete,
                    with_triggers=with_triggers,
                )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/profile/pre/*", []
                )

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/profile/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_profile(name)
