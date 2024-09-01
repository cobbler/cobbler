"""
Test module to assert the performance of editing items.
"""

from typing import Any, Callable, Dict, Tuple

import pytest
from pytest_benchmark.fixture import (  # type: ignore[reportMissingTypeStubs]
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
        "package",
        "file",
        "mgmtclass",
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
    create_distro: Callable[[str], Distro],
    cache_enabled: bool,
    enable_menu: bool,
    inherit_property: bool,
    what: str,
):
    """
    Test that asserts if editing items is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        return (cobbler_api, what), {}

    def item_edit(api: CobblerAPI, what: str):
        for test_item in api.get_items(what):
            if inherit_property:
                test_item.owners = "test owners"
            else:
                test_item.comment = "test commect"

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu
    CobblerTree.create_all_objs(cobbler_api, create_distro, False, False, False)

    # Act
    result = benchmark.pedantic(  # type: ignore
        item_edit, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Assert
