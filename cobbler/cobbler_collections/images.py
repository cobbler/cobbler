"""
Cobbler module that at runtime holds all images in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cobbler_collections import collection
from cobbler.items import image

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Images(collection.Collection[image.Image]):
    """
    A image instance represents a ISO or virt image we want to track
    and repeatedly install.  It differs from a answer-file based installation.
    """

    @staticmethod
    def collection_type() -> str:
        return "image"

    @staticmethod
    def collection_types() -> str:
        return "images"

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[str, Any]):
        """
        Return a Distro forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return image.Image(self.api, **seed_data)

    def remove_quick_pxe_sync(
        self, ref: image.Image, rebuild_menu: bool = True
    ) -> None:
        self.api.get_sync().remove_single_image(ref)
