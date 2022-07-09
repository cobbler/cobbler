"""
Cobbler module that at runtime holds all systems in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from cobbler.cobbler_collections import collection
from cobbler.items import system as system
from cobbler import utils
from cobbler.cexceptions import CX


class Systems(collection.Collection):
    """
    Systems are hostnames/MACs/IP names and the associated profile
    they belong to.
    """

    @staticmethod
    def collection_type() -> str:
        return "system"

    @staticmethod
    def collection_types() -> str:
        return "systems"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict

        :param api: TODO
        :param item_dict: TODO
        :returns: TODO
        """
        new_system = system.System(api)
        new_system.is_deserialize = True
        new_system.from_dict(item_dict)
        new_system.is_deserialize = False
        return new_system

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

        :raises CX: In case the name of the object was not given.
        """
        name = name.lower()
        obj = self.find(name=name)

        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/system/pre/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_system(name)

        if obj.parent is not None and obj.name in obj.parent.children:
            obj.parent.children.remove(obj.name)
            # ToDo: Only serialize parent object, use:
            #       Use self.collection_mgr.serialize_one_item(obj.parent)
            self.api.serialize()

        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()
        self.collection_mgr.serialize_delete(self, obj)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/system/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
