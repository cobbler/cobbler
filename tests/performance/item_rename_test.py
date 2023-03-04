"""
Test module to assert the performance of renaming items.
"""

from typing import Any, Callable, Dict, Tuple

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System

from tests.performance import CobblerTree


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
def test_item_rename(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    create_image: Callable[[str], Image],
    create_system: Callable[[str, str, str], System],
    cache_enabled: bool,
    enable_menu: bool,
    what: str,
):
    """
    Test that asserts if renaming an item is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_all_objs(
            cobbler_api, create_distro, create_profile, create_image, create_system
        )
        return (cobbler_api, what), {}

    def item_rename(api: CobblerAPI, what: str):
        for test_item in api.get_items(what):
            api.rename_item(what, test_item, test_item.name + "_renamed")

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu

    # Act
    result = benchmark.pedantic(
        item_rename, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert
