"""
Test module to assert the performance of deserializing the object tree.
"""

import os
from typing import Callable

import pytest
from pytest_benchmark.fixture import (  # type: ignore[reportMissingTypeStubs,import-untyped]
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
    create_distro: Callable[[str, bool], Distro],
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
    iterations = 1
    if CobblerTree.test_iterations > -1:
        iterations = CobblerTree.test_iterations
    iterations_per_test = int(
        os.getenv("COBBLER_PERFORMANCE_TEST_DESERIALIZE_ITERATIONS", -1)
    )
    if iterations_per_test > -1:
        iterations = iterations_per_test
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(
        cobbler_api, create_distro, save=True, with_triggers=False, with_sync=False
    )

    # Act
    result = benchmark.pedantic(deserialize, rounds=CobblerTree.test_rounds, iterations=iterations)  # type: ignore

    # Assert
