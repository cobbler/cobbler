"""
Test module to assert the performance of deserializing the object tree.
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
def test_deserialize(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that benchmarks the file based deserialization process of Cobbler.
    """

    def deserialize():
        # pylint: disable=protected-access
        CobblerAPI.__shared_state = {}  # pyright: ignore [reportPrivateUsage]
        CobblerAPI.__has_loaded = False  # pyright: ignore [reportPrivateUsage]
        api = CobblerAPI()
        api.deserialize()

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(
        cobbler_api, create_distro, save=True, with_triggers=False, with_sync=False
    )

    # Act
    result = benchmark.pedantic(deserialize, rounds=CobblerTree.test_rounds)  # type: ignore

    # Assert
