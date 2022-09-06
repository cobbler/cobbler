"""
Cobbler module that at runtime holds all distros in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os.path
import glob

from cobbler.cobbler_collections import collection
from cobbler.items import distro
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.utils import filesystem_helpers


class Distros(collection.Collection):
    """
    A distro represents a network bootable matched set of kernels and initrd files.
    """

    @staticmethod
    def collection_type() -> str:
        return "distro"

    @staticmethod
    def collection_types() -> str:
        return "distros"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_distro = distro.Distro(api)
        new_distro.from_dict(item_dict)
        return new_distro

    def remove(
        self,
        name,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ):
        """
        Remove element named 'name' from the collection

        :raises CX: In case any subitem (profiles or systems) would be orphaned. If the option ``recursive`` is set then
                    the orphaned items would be removed automatically.
        """
        name = name.lower()

        obj = self.find(name=name)

        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        # first see if any Groups use this distro
        if not recursive:
            for profile in self.api.profiles():
                if profile.distro and profile.distro.name.lower() == name:
                    raise CX("removal would orphan profile: %s" % profile.name)

        kernel = obj.kernel
        if recursive:
            kids = obj.get_children()
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
                lite_sync.remove_single_distro(name)
        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()

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
        for storage in possible_storage:
            if os.path.dirname(obj.kernel).find(storage) != -1:
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
            for d in distros:
                if d.kernel.find(path) != -1:
                    found = True
            if not found:
                filesystem_helpers.rmtree(path)
