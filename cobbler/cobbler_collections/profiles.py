"""
Cobbler module that at runtime holds all profiles in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict

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
        Return a Profile forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return profile.Profile(self.api, **seed_data)

    def remove_quick_pxe_sync(
        self, ref: profile.Profile, rebuild_menu: bool = True
    ) -> None:
        """
        Delete the profile's webdir file and its autoinstall-template directory, optionally rebuilding the PXE
        boot menu afterwards.

        :param ref: The profile that was removed.
        :param rebuild_menu: If ``True``, rebuild the PXE boot menu after removing the profile.
        """
        self.api.get_sync().remove_single_profile(ref, rebuild_menu=rebuild_menu)
