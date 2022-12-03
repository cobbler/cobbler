"""
Tests that validate the functionality of the module that is responsible for caching the results of the to_dict method.
"""

import logging
from typing import Any, Callable, Iterable, List, Set

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.bootable_item import BootableItem
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System

from tests.conftest import does_not_raise

logger = logging.getLogger()


def test_collection_types(cobbler_api: CobblerAPI):
    """
    Test to verify that all collection types are listed inside and freshly initialized collection manager.
    """
    # pylint: disable=protected-access
    # Arrange
    mgr = cobbler_api._collection_mgr  # type: ignore[reportPrivateUsage]

    # Act
    result = mgr.__dict__.items()

    # Assert
    assert len(result) == 10


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_repo_dict_cache_load(
    cobbler_api: CobblerAPI,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of repositories are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_repo = cobbler_api.new_repo(name="test_repo")
    cobbler_api.add_repo(test_repo)

    # Act
    with expected_exception:
        result1 = test_repo.to_dict(resolved=True)
        result2 = test_repo.to_dict(resolved=False)
        cached_result1 = test_repo.cache.get_dict_cache(True)
        cached_result2 = test_repo.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_distro_dict_cache_load(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    input_value: bool,
    expected_exception: Any,
    expected_output: str,
):
    """
    Test to verify that the dict cache of distros are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()

    # Act
    with expected_exception:
        result1 = test_distro.to_dict(resolved=True)
        result2 = test_distro.to_dict(resolved=False)
        cached_result1 = test_distro.cache.get_dict_cache(True)
        cached_result2 = test_distro.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_image_dict_cache_load(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], Image],
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of images are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_image = create_image()

    # Act
    with expected_exception:
        result1 = test_image.to_dict(resolved=True)
        result2 = test_image.to_dict(resolved=False)
        cached_result1 = test_image.cache.get_dict_cache(True)
        cached_result2 = test_image.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_menu_dict_cache_load(
    cobbler_api: CobblerAPI,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of menus are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_menu = cobbler_api.new_menu(name="test_menu")
    cobbler_api.add_menu(test_menu)

    # Act
    with expected_exception:
        result1 = test_menu.to_dict(resolved=True)
        result2 = test_menu.to_dict(resolved=False)
        cached_result1 = test_menu.cache.get_dict_cache(True)
        cached_result2 = test_menu.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_profile_dict_cache_load(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of profiles are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}  # type: ignore[method-assign]
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = {"my_value": 5}  # type: ignore[method-assign]

    # Act
    with expected_exception:
        result1 = test_profile.to_dict(resolved=True)
        result2 = test_profile.to_dict(resolved=False)
        cached_result1 = test_profile.cache.get_dict_cache(True)
        cached_result2 = test_profile.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_system_dict_cache_load(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of systems are loaded when cache is enabled and not loaded when cache is disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}  # type: ignore[method-assign]
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = {"my_value": 5}  # type: ignore[method-assign]
    test_system: System = create_system(profile_uid=test_profile.uid)

    # Act
    with expected_exception:
        result1 = test_system.to_dict(resolved=True)
        result2 = test_system.to_dict(resolved=False)
        cached_result1 = test_system.cache.get_dict_cache(True)
        cached_result2 = test_system.cache.get_dict_cache(False)

    # Assert
    assert (cached_result1 == result1) == expected_output
    assert (cached_result2 == result2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_repo_dict_cache_use(
    cobbler_api: CobblerAPI,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache for repositories is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_repo = cobbler_api.new_repo(name="test_repo")
    cobbler_api.add_repo(test_repo)
    test_repo.to_dict(resolved=True)
    test_repo.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_repo.cache.set_dict_cache(test_cache1, True)  # type: ignore
        test_repo.cache.set_dict_cache(test_cache2, False)  # type: ignore
        result1 = test_repo.cache.get_dict_cache(True)
        result2 = test_repo.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_distro_dict_cache_use(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of distros is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.to_dict(resolved=True)
    test_distro.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_distro.cache.set_dict_cache(test_cache1, True)  # type: ignore
        test_distro.cache.set_dict_cache(test_cache2, False)  # type: ignore
        result1 = test_distro.cache.get_dict_cache(True)
        result2 = test_distro.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_image_dict_cache_use(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], Image],
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of images is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_image = create_image()
    test_image.to_dict(resolved=True)
    test_image.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_image.cache.set_dict_cache(test_cache1, True)  # type: ignore
        test_image.cache.set_dict_cache(test_cache2, False)  # type: ignore
        result1 = test_image.cache.get_dict_cache(True)
        result2 = test_image.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_menu_dict_cache_use(
    cobbler_api: CobblerAPI,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache for menus is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_menu = Menu(cobbler_api)
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.add_menu(test_menu)
    test_menu.to_dict(resolved=True)
    test_menu.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_menu.cache.set_dict_cache(test_cache1, True)  # type: ignore
        test_menu.cache.set_dict_cache(test_cache2, False)  # type: ignore
        result1 = test_menu.cache.get_dict_cache(True)
        result2 = test_menu.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_profile_dict_cache_use(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of profiles is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}  # type: ignore[method-assign]
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = {"my_value": 5}  # type: ignore[method-assign]
    test_profile.to_dict(resolved=True)
    test_profile.to_dict(resolved=False)
    test_cache1 = {"test": True}
    test_cache2 = {"test": False}

    # Act
    with expected_exception:
        test_profile.cache.set_dict_cache(test_cache1, True)
        test_profile.cache.set_dict_cache(test_cache2, False)
        result1 = test_profile.cache.get_dict_cache(True)
        result2 = test_profile.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        (True, does_not_raise(), True),
        (False, does_not_raise(), False),
    ],
)
def test_system_dict_cache_use(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Any,
    create_system: Any,
    input_value: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verify that the dict cache of systems is utilized when cache is enabled and not utilized when cache is
    disabled.
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}  # type: ignore[method-assign]
    test_profile: Profile = create_profile(test_distro.uid)
    test_profile.kernel_options = {"my_value": 5}  # type: ignore[method-assign]
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.to_dict(resolved=True)
    test_system.to_dict(resolved=False)
    test_cache1 = {"test": True}
    test_cache2 = {"test": False}

    # Act
    with expected_exception:
        test_system.cache.set_dict_cache(test_cache1, True)
        test_system.cache.set_dict_cache(test_cache2, False)
        result1 = test_system.cache.get_dict_cache(True)
        result2 = test_system.cache.get_dict_cache(False)

    # Assert
    assert (result1 == test_cache1) == expected_output
    assert (result2 == test_cache2) == expected_output


@pytest.mark.parametrize(
    "cache_enabled,expected_exception,expected_output",
    [
        (True, pytest.raises(CX), True),
        (False, pytest.raises(CX), False),
    ],
)
def test_dict_cache_edit_invalidate(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_image: Callable[[], Image],
    create_profile: Any,
    create_system: Any,
    cache_enabled: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verfiy that the dict cache is invalidated for all dependent objects when an object is edited.
    """

    def validate_caches(
        test_api: CobblerAPI,
        objs: List[BaseItem],
        obj_test: BaseItem,
        dep: Iterable[BaseItem],
    ):
        for obj in objs:
            obj.to_dict(resolved=False)
            obj.to_dict(resolved=True)
        remain_objs = set(objs) - set(dep)
        if isinstance(obj_test, BootableItem):
            remain_objs.remove(obj_test)
            obj_test.owners = "test"  # type: ignore[method-assign]
            if (
                obj_test.cache.get_dict_cache(True) is not None
                or obj_test.cache.get_dict_cache(False) is not None
            ):
                return False
        elif obj_test == test_api.settings():
            test_api.clean_items_cache(obj_test)  # type: ignore
        elif obj_test == test_api.get_signatures():
            test_api.signature_update()
        for obj in dep:
            if obj.cache.get_dict_cache(True) is not None:
                return False
            if obj.cache.get_dict_cache(False) is None:
                return False
        for obj in remain_objs:
            if obj.cache.get_dict_cache(True) is None:
                return False
            if obj.cache.get_dict_cache(False) is None:
                return False
        return True

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    objs: List[BaseItem] = []
    test_repo1 = Repo(cobbler_api)
    test_repo1.name = "test_repo1"  # type: ignore[method-assign]
    cobbler_api.add_repo(test_repo1)
    objs.append(test_repo1)
    test_repo2 = Repo(cobbler_api)
    test_repo2.name = "test_repo2"  # type: ignore[method-assign]
    cobbler_api.add_repo(test_repo2)
    objs.append(test_repo2)
    test_menu1 = Menu(cobbler_api)
    test_menu1.name = "test_menu1"  # type: ignore[method-assign]
    cobbler_api.add_menu(test_menu1)
    objs.append(test_menu1)
    test_menu2 = Menu(cobbler_api)
    test_menu2.name = "test_menu2"  # type: ignore[method-assign]
    test_menu2.parent = test_menu1.uid  # type: ignore[method-assign]
    cobbler_api.add_menu(test_menu2)
    objs.append(test_menu2)
    test_distro = create_distro()
    test_distro.source_repos = [test_repo1.uid]  # type: ignore[method-assign]
    objs.append(test_distro)
    test_profile1: Profile = create_profile(
        distro_uid=test_distro.uid, name="test_profile1"
    )
    test_profile1.enable_menu = False  # type: ignore[method-assign]
    objs.append(test_profile1)
    test_profile2: Profile = create_profile(
        profile_uid=test_profile1.uid, name="test_profile2"
    )
    test_profile2.enable_menu = False  # type: ignore[method-assign]
    test_profile2.menu = test_menu2.uid  # type: ignore[method-assign]
    objs.append(test_profile2)
    test_profile3: Profile = create_profile(
        profile_uid=test_profile1.uid, name="test_profile3"
    )
    test_profile3.enable_menu = False  # type: ignore[method-assign]
    test_profile3.repos = [test_repo1.uid, test_repo2.uid]  # type: ignore[method-assign]
    objs.append(test_profile3)
    test_image = create_image()
    test_image.menu = test_menu1.uid  # type: ignore[method-assign]
    objs.append(test_image)
    test_system1 = create_system(profile_uid=test_profile1.uid, name="test_system1")
    objs.append(test_system1)
    test_system2 = create_system(image_uid=test_image.uid, name="test_system2")
    objs.append(test_system2)

    # Act
    repo1_dep = test_repo1.tree_walk("_owners")
    repo2_dep = test_repo2.tree_walk("_owners")
    menu1_dep = test_menu1.tree_walk("_owners")
    menu2_dep = test_menu2.tree_walk("_owners")
    distro_dep = test_distro.tree_walk("_owners")
    profile1_dep = test_profile1.tree_walk("_owners")
    profile2_dep = test_profile2.tree_walk("_owners")
    profile3_dep = test_profile3.tree_walk("_owners")
    image_dep = test_image.tree_walk("_owners")
    system1_dep = test_system1.tree_walk("_owners")
    system2_dep = test_system2.tree_walk("_owners")

    settings_dep = objs
    signatures_dep = [
        test_distro,
        test_profile1,
        test_profile2,
        test_profile3,
        test_image,
        test_system1,
        test_system2,
    ]

    # Assert
    assert validate_caches(cobbler_api, objs, test_repo1, repo1_dep) == expected_output
    assert validate_caches(cobbler_api, objs, test_repo2, repo2_dep) == expected_output
    assert validate_caches(cobbler_api, objs, test_menu1, menu1_dep) == expected_output
    assert validate_caches(cobbler_api, objs, test_menu2, menu2_dep) == expected_output
    assert (
        validate_caches(cobbler_api, objs, test_distro, distro_dep) == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, test_profile1, profile1_dep)
        == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, test_profile2, profile2_dep)
        == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, test_profile3, profile3_dep)
        == expected_output
    )
    assert validate_caches(cobbler_api, objs, test_image, image_dep) == expected_output
    assert (
        validate_caches(cobbler_api, objs, test_system1, system1_dep) == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, test_system2, system2_dep) == expected_output
    )

    assert (
        validate_caches(cobbler_api, objs, cobbler_api.settings(), settings_dep)  # type: ignore
        == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, cobbler_api.get_signatures(), signatures_dep)  # type: ignore
        == expected_output
    )
    with expected_exception:
        cobbler_api.clean_items_cache(True)  # type: ignore


@pytest.mark.parametrize(
    "cache_enabled,expected_exception,expected_output",
    [
        (True, pytest.raises(CX), True),
        (False, pytest.raises(CX), False),
    ],
)
def test_dict_cache_rename_invalidate(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_image: Callable[[], Image],
    create_profile: Any,
    create_system: Any,
    cache_enabled: bool,
    expected_exception: Any,
    expected_output: bool,
):
    """
    Test to verfiy that the dict cache is invalidated for all dependent objects when an object is renamed.
    """

    def validate_caches(
        objs: List[BaseItem],
        obj_test: BaseItem,
    ):
        for obj in objs:
            obj.to_dict(resolved=False)
            obj.to_dict(resolved=True)
        logger.info("Generated dict cache for all %s object(s)", len(objs))
        remain_objs = set(objs)
        deps: Set[BaseItem] = set()
        if isinstance(obj_test, BootableItem):
            deps = set(obj_test.tree_walk())
            remain_objs = remain_objs - deps
            remain_objs.remove(obj_test)
            logger.info("Pre Rename")
            cobbler_api.get_items(obj_test.COLLECTION_TYPE).rename(
                obj_test, f"{obj_test.name}_newname"
            )
            logger.info("Post Rename/Pre owners")
            obj_test.owners = "test"  # type: ignore[method-assign]
            logger.info("Post Owners")
            if (
                obj_test.cache.get_dict_cache(True) is not None
                or obj_test.cache.get_dict_cache(False) is not None
            ):
                logger.info("get_dict_cache was None")
                return False
        logger.info([x.uid for x in deps])
        for obj in deps:
            # Dependant resolved object caches are invalidated to ensure resolved cache consistency
            if obj.cache.get_dict_cache(True) is not None:
                logger.info(
                    "get_dict_cache(resolved=True) was not None %s (%s)",
                    obj.uid,
                    obj.name,
                )
                return False
            if obj.cache.get_dict_cache(False) is None:
                logger.info(
                    "get_dict_cache(resolved=False) was None %s (%s)", obj.uid, obj.name
                )
                return False
        logger.info([x.uid for x in remain_objs])
        for obj in remain_objs:
            if obj.cache.get_dict_cache(True) is None:
                logger.info(
                    "get_dict_cache(resolved=True) was None %s (%s)", obj.uid, obj.name
                )
                return False
            if obj.cache.get_dict_cache(False) is None:
                logger.info(
                    "get_dict_cache(resolved=False) was None %s (%s)", obj.uid, obj.name
                )
                return False
        return True

    # Arrange
    cobbler_api.settings().cache_enabled = cache_enabled
    objs: List[BaseItem] = []
    test_repo1 = Repo(cobbler_api)
    test_repo1.name = "test_repo1"  # type: ignore[method-assign]
    cobbler_api.add_repo(test_repo1)
    objs.append(test_repo1)
    test_repo2 = Repo(cobbler_api)
    test_repo2.name = "test_repo2"  # type: ignore[method-assign]
    cobbler_api.add_repo(test_repo2)
    objs.append(test_repo2)
    test_menu1 = Menu(cobbler_api)
    test_menu1.name = "test_menu1"  # type: ignore[method-assign]
    cobbler_api.add_menu(test_menu1)
    objs.append(test_menu1)
    test_menu2 = Menu(cobbler_api)
    test_menu2.name = "test_menu2"  # type: ignore[method-assign]
    test_menu2.parent = test_menu1.uid  # type: ignore[method-assign]
    cobbler_api.add_menu(test_menu2)
    objs.append(test_menu2)
    test_distro = create_distro()
    test_distro.source_repos = [test_repo1.uid]  # type: ignore[method-assign]
    objs.append(test_distro)
    test_profile1 = create_profile(distro_uid=test_distro.uid, name="test_profile1")
    test_profile1.enable_menu = False
    objs.append(test_profile1)
    test_profile2 = create_profile(profile_uid=test_profile1.uid, name="test_profile2")
    test_profile2.enable_menu = False
    test_profile2.menu = test_menu2.uid
    objs.append(test_profile2)
    test_profile3 = create_profile(profile_uid=test_profile1.uid, name="test_profile3")
    test_profile3.enable_menu = False
    test_profile3.repos = [test_repo1.uid, test_repo2.uid]
    objs.append(test_profile3)
    test_image = create_image()
    test_image.menu = test_menu1.uid  # type: ignore[method-assign]
    objs.append(test_image)
    test_system1 = create_system(profile_uid=test_profile1.uid, name="test_system1")
    objs.append(test_system1)
    test_system2 = create_system(image_uid=test_image.uid, name="test_system2")
    objs.append(test_system2)

    # Act & Assert
    assert validate_caches(objs, test_repo1) == expected_output
    assert validate_caches(objs, test_repo2) == expected_output
    assert validate_caches(objs, test_menu1) == expected_output
    assert validate_caches(objs, test_menu2) == expected_output
    assert validate_caches(objs, test_distro) == expected_output
    assert validate_caches(objs, test_profile1) == expected_output
    assert validate_caches(objs, test_profile2) == expected_output
    assert validate_caches(objs, test_profile3) == expected_output
    assert validate_caches(objs, test_image) == expected_output
    assert validate_caches(objs, test_system1) == expected_output
    assert validate_caches(objs, test_system2) == expected_output
    with expected_exception:
        cobbler_api.clean_items_cache(True)  # type: ignore[reportArgumentType,arg-type]
