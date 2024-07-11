"""
Fixtures that are common for testing the cobbler collections.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager


@pytest.fixture()
def collection_mgr(cobbler_api: CobblerAPI) -> CollectionManager:
    """
    Fixture that provides access to the collection manager instance for testing.
    """
    # pylint: disable=protected-access
    return cobbler_api._collection_mgr  # pyright: ignore [reportPrivateUsage]
