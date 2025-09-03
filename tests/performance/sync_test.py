"""
Test module to assert the performance of "cobbler sync".
"""

from typing import Callable

import pytest
from pytest_benchmark.fixture import (  # type: ignore[reportMissingTypeStubs,import-untyped]
    BenchmarkFixture,
)

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.modules.managers import in_tftpd

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
def test_sync(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str, bool], Distro],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if "cobbler sync" without arguments is running without a performance decrease.
    """

    def sync():
        cobbler_api.sync()

    # Arrange
    # Reset the tftp singleton to prevent accessing stale manager collections
    in_tftpd.MANAGER = None
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(cobbler_api, create_distro, False, False, False)

    # Act
    result = benchmark.pedantic(sync, rounds=CobblerTree.test_rounds)  # type: ignore

    # Assert
