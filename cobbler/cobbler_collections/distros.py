"""
Cobbler module that at runtime holds all distros in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import os.path
from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import distro
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Distros(collection.Collection[distro.Distro]):
    """
    A distro represents a network bootable matched set of kernels and initrd files.
    """

    @staticmethod
    def collection_type() -> str:
        return "distro"

    @staticmethod
    def collection_types() -> str:
        return "distros"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> "distro.Distro":
        """
        Return a Distro forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return distro.Distro(self.api, **seed_data)

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ) -> None:
        """
        Remove element named 'name' from the collection

        :raises CX: In case any subitem (profiles or systems) would be orphaned. If the option ``recursive`` is set then
                    the orphaned items would be removed automatically.
        """
        obj = self.listing.get(name, None)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        # first see if any Groups use this distro
        if not recursive:
            for profile in self.api.profiles():
                if profile.distro and profile.distro.name == name:  # type: ignore
                    raise CX(f"removal would orphan profile: {profile.name}")

        if recursive:
            kids = self.api.find_profile(return_list=True, **{"distro": obj.name})
            if kids is None:
                kids = []
            if not isinstance(kids, list):
                raise ValueError("find_items is expected to return a list or None!")
            for k in kids:
                self.api.remove_profile(
                    k,
                    recursive=recursive,
                    delete=with_delete,
                    with_triggers=with_triggers,
                )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/distro/pre/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_distro(obj)
        with self.lock:
            del self.listing[name]

        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/distro/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )

        # look through all mirrored directories and find if any directory is holding this particular distribution's
        # kernel and initrd
        settings = self.api.settings()
        possible_storage = glob.glob(settings.webdir + "/distro_mirror/*")
        path = None
        kernel = obj.kernel
        for storage in possible_storage:
            if os.path.dirname(kernel).find(storage) != -1:
                path = storage
                continue

        # if we found a mirrored path above, we can delete the mirrored storage /if/ no other object is using the
        # same mirrored storage.
        if (
            with_delete
            and path is not None
            and os.path.exists(path)
            and kernel.find(settings.webdir) != -1
        ):
            # this distro was originally imported so we know we can clean up the associated storage as long as
            # nothing else is also using this storage.
            found = False
            distros = self.api.distros()
            for dist in distros:
                if dist.kernel.find(path) != -1:
                    found = True
            if not found:
                filesystem_helpers.rmtree(path)
