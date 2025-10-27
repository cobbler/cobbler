"""
Test module to assert the performance of editing items.
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
    "inherit_property",
    [
        False,
        True,
    ],
)
@pytest.mark.parametrize(
    "what",
    [
        "repo",
        "distro",
        "menu",
        "profile",
        "image",
        "system",
    ],
)
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
def test_item_edit(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str, bool], Distro],
    cache_enabled: bool,
    enable_menu: bool,
    inherit_property: bool,
    what: str,
):
    """
    Test that asserts if editing items is running without a performance decrease.
    """

    def item_edit(api: CobblerAPI, what: str):
        for test_item in api.get_items(what):
            if inherit_property:
                old_owners = test_item.owners
                test_item.owners = "test owners"  # type: ignore[method-assign]
                test_item.owners = old_owners
            else:
                old_comment = test_item.comment
                test_item.comment = "test comment"  # type: ignore[method-assign]
                test_item.comment = old_comment

    # Arrange
    iterations = 1
    if CobblerTree.test_iterations > -1:
        iterations = CobblerTree.test_iterations
    iterations_per_test = int(
        os.getenv("COBBLER_PERFORMANCE_TEST_ITEM_EDIT_ITERATIONS", -1)
    )
    if iterations_per_test > -1:
        iterations = iterations_per_test
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(cobbler_api, create_distro, False, False, False)

    # Act
    result = benchmark.pedantic(  # type: ignore
        item_edit,
        rounds=CobblerTree.test_rounds,
        iterations=iterations,
        args=(cobbler_api, what),
    )

    # Assert
