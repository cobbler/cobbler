"""
Test module to assert the performance of adding different kinds of items.
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
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_packages_create(
    benchmark: BenchmarkFixture, cobbler_api: CobblerAPI, cache_enabled: bool
):
    """
    Test that asserts if creating a package is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (cobbler_api,), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_packages, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_files_create(
    benchmark: BenchmarkFixture, cobbler_api: CobblerAPI, cache_enabled: bool
):
    """
    Test that asserts if creating a package is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (cobbler_api,), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_files, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_mgmtclasses_create(
    benchmark: BenchmarkFixture, cobbler_api: CobblerAPI, cache_enabled: bool
):
    """
    Test that asserts if creating a package is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (cobbler_api,), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_mgmtclasses, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_repos_create(
    benchmark: BenchmarkFixture, cobbler_api: CobblerAPI, cache_enabled: bool
):
    """
    Test that asserts if creating a repository is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (cobbler_api,), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_repos, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_distros_create(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    cache_enabled: bool,
):
    """
    Test that asserts if creating a distro is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_packages(cobbler_api)
        CobblerTree.create_files(cobbler_api)
        CobblerTree.create_mgmtclasses(cobbler_api)
        CobblerTree.create_repos(cobbler_api)
        return (cobbler_api, create_distro), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_distros, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_menus_create(
    benchmark: BenchmarkFixture, cobbler_api: CobblerAPI, cache_enabled: bool
):
    """
    Test that asserts if creating a menu is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (cobbler_api,), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_menus, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


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
def test_profiles_create(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if creating a profile is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_packages(cobbler_api)
        CobblerTree.create_files(cobbler_api)
        CobblerTree.create_mgmtclasses(cobbler_api)
        CobblerTree.create_repos(cobbler_api)
        CobblerTree.create_distros(cobbler_api, create_distro)
        CobblerTree.create_menus(cobbler_api)
        return (cobbler_api, create_profile), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_profiles, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


@pytest.mark.parametrize(
    "cache_enabled",
    [
        (False,),
        (True,),
    ],
)
def test_images_create(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], Image],
    cache_enabled: bool,
):
    """
    Test that asserts if creating an image is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_menus(cobbler_api)
        return (cobbler_api, create_image), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_images, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


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
def test_systems_create(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    create_image: Callable[[str], Image],
    create_system: Callable[[str, str, str], System],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if creating a system is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        CobblerTree.create_packages(cobbler_api)
        CobblerTree.create_files(cobbler_api)
        CobblerTree.create_mgmtclasses(cobbler_api)
        CobblerTree.create_repos(cobbler_api)
        CobblerTree.create_distros(cobbler_api, create_distro)
        CobblerTree.create_menus(cobbler_api)
        CobblerTree.create_images(cobbler_api, create_image)
        CobblerTree.create_profiles(cobbler_api, create_profile)
        return (cobbler_api, create_system), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_systems, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert


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
def test_all_items_create(
    benchmark: BenchmarkFixture,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    create_image: Callable[[str], Image],
    create_system: Callable[[str, str, str], System],
    cache_enabled: bool,
    enable_menu: bool,
):
    """
    Test that asserts if creating all items at once is running without a performance decrease.
    """

    def setup_func() -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        CobblerTree.remove_all_objs(cobbler_api)
        return (
            cobbler_api,
            create_distro,
            create_profile,
            create_image,
            create_system,
        ), {}

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    cobbler_api.settings().enable_menu = enable_menu

    # Act
    result = benchmark.pedantic(
        CobblerTree.create_all_objs, setup=setup_func, rounds=CobblerTree.test_rounds
    )

    # Cleanup
    CobblerTree.remove_all_objs(cobbler_api)

    # Assert
