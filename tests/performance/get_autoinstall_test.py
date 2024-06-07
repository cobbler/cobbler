"""
Test module to assert the performance of retrieving an autoinstallation file.
"""

from typing import Any, Callable, Dict, Tuple
import pytest

from pytest_benchmark.fixture import BenchmarkFixture

from cobbler import autoinstall_manager
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System
from tests.performance import CobblerTree


@pytest.mark.parametrize(
    "what",
    [
        "profile",
        "system",
    ],
)
@pytest.mark.parametrize(
    "cache_enabled",
    [
        False,
        True,
    ],
)
def test_get_autoinstall(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    create_image: Callable[[str], Image],
    create_system: Callable[[str, str, str], System],
    cache_enabled: bool,
    what: str,
):
    """
    Test that asserts if retrieving rendered autoinstallation templates is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_all_objs(
            cobbler_api, create_distro, create_profile, create_image, create_system
        )
        return (cobbler_api, what), {}

    def item_get_autoinstall(api: CobblerAPI, what: str):
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(cobbler_api)
        for test_item in api.get_items(what):
            if what == "profile":
                autoinstall_mgr.generate_autoinstall(profile=test_item.name)
            elif what == "system":
                autoinstall_mgr.generate_autoinstall(system=test_item.name)

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = False

    # Act
    result = benchmark.pedantic(
        item_get_autoinstall, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert
