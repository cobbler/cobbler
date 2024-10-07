"""
Test module to assert the performance of the startup of the daemon.
"""

from typing import Callable, Dict, Tuple

import pytest
from pytest_benchmark.fixture import (  # type: ignore[reportMissingTypeStubs]
    BenchmarkFixture,
)

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro

from tests.performance import CobblerTree


@pytest.mark.parametrize(
    "cache_enabled,enable_menu",
    [
        (
            False,
            False,
        ),
        (
            True,
            False,
        ),
        (
            False,
            True,
        ),
        (
            True,
            True,
        ),
    ],
)
def test_start(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if the startup of Cobbler is running without a performance decrease.
    """

    def start_cobbler():
        # pylint: disable=protected-access,unused-variable
        CobblerAPI.__shared_state = {}  # type: ignore[reportPrivateUsage]
        CobblerAPI.__has_loaded = False  # type: ignore[reportPrivateUsage]
        api = CobblerAPI()  # type: ignore[reportUnusedVariable]

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(
        cobbler_api, create_distro, save=True, with_triggers=False, with_sync=False
    )

    # Act
    result = benchmark.pedantic(start_cobbler, rounds=CobblerTree.test_rounds)  # type: ignore

    # Assert
