"""
Test module to assert the performance of retrieving an auto-installation file.
"""

from typing import Any, Callable, Dict, Tuple

import pytest
from pytest_benchmark.fixture import (  # type: ignore[reportMissingTypeStubs,import-untyped]
    BenchmarkFixture,
)

from cobbler import autoinstall_manager
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro

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
    create_distro: Callable[[str, bool], Distro],
    cache_enabled: bool,
    what: str,
):
    """
    Test that asserts if retrieving rendered autoinstallation templates is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
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
    CobblerTree.create_all_objs(
        cobbler_api, create_distro, save=False, with_triggers=False, with_sync=False
    )

    # Act
    result = benchmark.pedantic(  # type: ignore
        item_get_autoinstall, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Assert
