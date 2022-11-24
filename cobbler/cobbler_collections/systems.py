"""
Cobbler module that at runtime holds all systems in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cobbler_collections import collection
from cobbler.items import system

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Systems(collection.Collection[system.System]):
    """
    Systems are hostnames/MACs/IP names and the associated profile they belong to.
    """

    @staticmethod
    def collection_type() -> str:
        return "system"

    @staticmethod
    def collection_types() -> str:
        return "systems"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> system.System:
        """
        Return a System forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return system.System(self.api, **seed_data)

    def remove_quick_pxe_sync(
        self, ref: system.System, rebuild_menu: bool = True
    ) -> None:
        self.api.get_sync().remove_single_system(ref)
