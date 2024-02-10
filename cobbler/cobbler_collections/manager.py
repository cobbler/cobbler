"""
Repository of the Cobbler object model
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import weakref
from typing import TYPE_CHECKING, Any, Dict, Union

from cobbler import serializer, validate
from cobbler.cexceptions import CX
from cobbler.cobbler_collections.distros import Distros
from cobbler.cobbler_collections.images import Images
from cobbler.cobbler_collections.menus import Menus
from cobbler.cobbler_collections.profiles import Profiles
from cobbler.cobbler_collections.repos import Repos
from cobbler.cobbler_collections.systems import Systems
from cobbler.settings import Settings

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection
    from cobbler.items.abstract.base_item import BaseItem

    COLLECTION_UNION = Union[Menus, Distros, Repos, Profiles, Images, Systems]


class CollectionManager:
    """
    Manages a definitive copy of all data cobbler_collections with weakrefs pointing back into the class so they can
    understand each other's contents.
    """

    has_loaded = False
    __shared_state: Dict[str, Any] = {}

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor which loads all content if this action was not performed before.
        """
        self.__dict__ = CollectionManager.__shared_state
        if not CollectionManager.has_loaded:
            self.__load(api)

    def __load(self, api: "CobblerAPI") -> None:
        """
        Load all collections from the disk into Cobbler.

        :param api: The api to resolve information with.
        """
        CollectionManager.has_loaded = True

        self.api = api
        self.__serializer = serializer.Serializer(api)
        self._distros = Distros(weakref.proxy(self))
        self._repos = Repos(weakref.proxy(self))
        self._profiles = Profiles(weakref.proxy(self))
        self._systems = Systems(weakref.proxy(self))
        self._images = Images(weakref.proxy(self))
        self._menus = Menus(weakref.proxy(self))

    def distros(self) -> Distros:
        """
        Return the definitive copy of the Distros collection
        """
        return self._distros

    def profiles(self) -> Profiles:
        """
        Return the definitive copy of the Profiles collection
        """
        return self._profiles

    def systems(self) -> Systems:
        """
        Return the definitive copy of the Systems collection
        """
        return self._systems

    def settings(self) -> "Settings":
        """
        Return the definitive copy of the application settings
        """
        return self.api.settings()

    def repos(self) -> Repos:
        """
        Return the definitive copy of the Repos collection
        """
        return self._repos

    def images(self) -> Images:
        """
        Return the definitive copy of the Images collection
        """
        return self._images

    def menus(self) -> Menus:
        """
        Return the definitive copy of the Menus collection
        """
        return self._menus

    def serialize(self) -> None:
        """
        Save all cobbler_collections to disk
        """

        self.__serializer.serialize(self._distros)
        self.__serializer.serialize(self._repos)
        self.__serializer.serialize(self._profiles)
        self.__serializer.serialize(self._images)
        self.__serializer.serialize(self._systems)
        self.__serializer.serialize(self._menus)

    def serialize_one_item(self, item: "ITEM") -> None:  # type: ignore
        """
        Save a collection item to disk

        :param item: collection item
        """
        collection: "Collection[ITEM]" = self.get_items(item.COLLECTION_TYPE)  # type: ignore
        self.__serializer.serialize_item(collection, item)

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Save a collection item to disk

        Deprecated - Use above serialize_one_item function instead
        collection param can be retrieved

        :param collection: Collection
        :param item: collection item
        """
        self.__serializer.serialize_item(collection, item)

    def serialize_delete_one_item(self, item: "ITEM") -> None:  # type: ignore
        """
        Save a collection item to disk

        :param item: collection item
        """
        collection: "COLLECTION_UNION" = self.get_items(item.COLLECTION_TYPE)  # type: ignore
        self.__serializer.serialize_delete(collection, item)  # type: ignore

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Delete a collection item from disk

        :param collection: collection
        :param item: collection item
        """
        self.__serializer.serialize_delete(collection, item)

    def deserialize(self) -> None:
        """
        Load all cobbler_collections from disk

        :raises CX: if there is an error in deserialization
        """
        collection: "COLLECTION_UNION"
        for collection in (
            self._menus,
            self._distros,
            self._repos,
            self._profiles,
            self._images,
            self._systems,
        ):
            try:
                self.__serializer.deserialize(collection)  # type: ignore
            except Exception as error:
                raise CX(
                    f"serializer: error loading collection {collection.collection_type()}: {error}."
                    f"Check your settings!"
                ) from error

    def deserialize_one_item(self, obj: "BaseItem") -> Dict[str, Any]:
        """
        Load a collection item from disk

        :param obj: collection item
        """
        collection_type = self.get_items(obj.COLLECTION_TYPE).collection_types()
        return self.__serializer.deserialize_item(collection_type, obj.name)

    def get_items(
        self, collection_type: str
    ) -> Union[Distros, Profiles, Systems, Repos, Images, Menus, "Settings"]:
        """
        Get a full collection of a single type.

        Valid Values vor ``collection_type`` are: "distro", "profile", "repo", "image", "menu" and "settings".

        :param collection_type: The type of collection to return.
        :return: The collection if ``collection_type`` is valid.
        :raises CX: If the ``collection_type`` is invalid.
        """
        result: Union[
            Distros,
            Profiles,
            Systems,
            Repos,
            Images,
            Menus,
            "Settings",
        ]
        if validate.validate_obj_type(collection_type) and hasattr(
            self, f"_{collection_type}s"
        ):
            result = getattr(self, f"_{collection_type}s")
        else:
            raise CX(
                f'internal error, collection name "{collection_type}" not supported'
            )
        return result
