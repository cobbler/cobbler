"""
Shared fixture module for buildiso tests.
"""

import pytest

from cobbler.actions import mkloaders
from cobbler.api import CobblerAPI


@pytest.fixture(scope="function", autouse=True)
def create_loaders(cobbler_api: CobblerAPI):
    """
    Fixture to create bootloaders on disk for buildiso tests.
    """
    loaders = mkloaders.MkLoaders(cobbler_api)
    loaders.run()
