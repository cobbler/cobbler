"""
Module that holds all abstract methods and classes that are acting as interfaces for the rest of the auto-installation
module.
"""

import logging
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.item import Item


class AutoinstallBaseGenerator:
    """
    Abstract base class to define the interface that is available to auto-installation generators.
    """

    def __init__(self, api: "CobblerAPI"):
        """
        The constructor that initializes the generator.

        :param api: The API to resolve information with.
        """
        self.logger = logging.getLogger()
        self.api = api

    def generate_autoinstall(
        self, obj: "Item", template: str, requested_file: str
    ) -> str:
        """
        Generates an auto-installation file.

        :param obj: The object to generate the file for.
        :param template: The template that should be used for rendering the requested file.
        :param requested_file: The name of the requested file.
        :return: The generated AutoYaST XML file.
        """
        raise NotImplementedError()

    def generate_autoinstall_metadata(self, obj, key: str) -> Optional[Any]:
        """
        This method generates special metadata that might be requested individually.

        :param obj: The item that is in the context of the metadata that is requested.
        :param key: The name of the metadata key that should be generated.
        :return: Returns None in case the key is not known.
        """
        return None
