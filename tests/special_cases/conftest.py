"""
Module to contain all fixtures that are shared by the special test-cases that we execute.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.manager import AutoInstallationManager


@pytest.fixture(name="autoinstall_manager")
def fixture_autoinstall_manager(cobbler_api: CobblerAPI):
    """
    Fixture to provide an instance of AutoInstallationManager for testing built-in templates.
    """
    return AutoInstallationManager(cobbler_api)
