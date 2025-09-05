"""
Cobbler module that at runtime holds all distros in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import os.path
from typing import TYPE_CHECKING, Any, Dict

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
        ref: distro.Distro,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Remove the given element from the collection

        :param ref: The object to delete
        :param with_delete: In case the deletion triggers are executed for this distro.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this distro references.
        :param rebuild_menu: unused
        :raises CX: In case any subitem (profiles or systems) would be orphaned. If the option ``recursive`` is set then
                    the orphaned items would be removed automatically.
        """
        super().remove(
            ref,
            with_delete=with_delete,
            with_sync=with_sync,
            with_triggers=with_triggers,
            recursive=recursive,
            rebuild_menu=rebuild_menu,
        )

        # look through all mirrored directories and find if any directory is holding this particular distribution's
        # kernel and initrd
        settings = self.api.settings()
        possible_storage = glob.glob(settings.webdir + "/distro_mirror/*")
        path = None
        kernel = ref.kernel
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

    def remove_quick_pxe_sync(
        self, ref: distro.Distro, rebuild_menu: bool = True
    ) -> None:
        self.api.get_sync().remove_single_distro(ref)
