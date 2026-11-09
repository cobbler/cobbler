"""
Tests that are ensuring the correct functionality of the CobblerAPI in regard to removing items via it.
"""

from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro


def test_remove_item_by_uid(
    cobbler_api: CobblerAPI, create_distro: Callable[..., Distro]
):
    """
    ``remove_item`` (and thus every ``remove_<itemtype>`` method built on top of it) must resolve a
    string ``ref`` as the uid it is documented to be, not silently no-op when given one.
    """
    # Arrange
    test_distro = create_distro()

    # Act
    cobbler_api.remove_distro(test_distro.uid)

    # Assert
    assert cobbler_api.find_distro(name=test_distro.name) is None
