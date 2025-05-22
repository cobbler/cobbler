"""
Test module to assert the performance of creating the PXE menu.
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
def test_make_pxe_menu(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str, bool], Distro],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if creating the PXE menu is running wihtout a performance decrease.
    """

    def make_pxe_menu():
        cobbler_api.tftpgen.make_pxe_menu()

    # Arrange
    iterations = 1
    if CobblerTree.test_iterations > -1:
        iterations = CobblerTree.test_iterations
    iterations_per_test = int(
        os.getenv("COBBLER_PERFORMANCE_TEST_MAKE_PXE_MENU_ITERATIONS", -1)
    )
    if iterations_per_test > -1:
        iterations = iterations_per_test
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(cobbler_api, create_distro, False, False, False)

    # Act
    result = benchmark.pedantic(make_pxe_menu, rounds=CobblerTree.test_rounds, iterations=iterations)  # type: ignore

    # Assert
