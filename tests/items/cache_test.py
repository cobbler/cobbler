"""
TODO
"""

from typing import Any, Callable, Dict, List, Union

import pytest
from _pytest.python_api import RaisesContext

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System
from cobbler.settings import Settings

from tests.conftest import does_not_raise


def test_collection_types(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    mgr = cobbler_api._collection_mgr

    # Act
    result = mgr.__dict__.items()

    # Assert
    print(result)
    assert len(result) == 8


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
    expected_exception: RaisesContext[Any],
    expected_output: bool,
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_repo"
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
    create_distro,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
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
    create_image,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
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
    cobbler_api: CobblerAPI, input_value, expected_exception, expected_output
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_menu = Menu(cobbler_api)
    test_menu.name = "test_menu"
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
    create_distro,
    create_profile,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = {"my_value": 5}

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
    create_distro,
    create_profile,
    create_system,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = {"my_value": 5}
    test_system = create_system(profile_name=test_profile.name)

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
    cobbler_api: CobblerAPI, input_value, expected_exception, expected_output
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_repo"
    cobbler_api.add_repo(test_repo)
    test_repo.to_dict(resolved=True)
    test_repo.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_repo.cache.set_dict_cache(test_cache1, True)
        test_repo.cache.set_dict_cache(test_cache2, False)
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
    create_distro,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
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
        test_distro.cache.set_dict_cache(test_cache1, True)
        test_distro.cache.set_dict_cache(test_cache2, False)
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
    create_image,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
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
        test_image.cache.set_dict_cache(test_cache1, True)
        test_image.cache.set_dict_cache(test_cache2, False)
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
    cobbler_api: CobblerAPI, input_value, expected_exception, expected_output
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_menu = Menu(cobbler_api)
    test_menu.name = "test_menu"
    cobbler_api.add_menu(test_menu)
    test_menu.to_dict(resolved=True)
    test_menu.to_dict(resolved=False)
    test_cache1 = "test1"
    test_cache2 = "test2"

    # Act
    with expected_exception:
        test_menu.cache.set_dict_cache(test_cache1, True)
        test_menu.cache.set_dict_cache(test_cache2, False)
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
    create_distro,
    create_profile,
    input_value,
    expected_exception,
    expected_output,
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = {"my_value": 5}
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
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_value: bool,
    expected_exception: RaisesContext[Any],
    expected_output: bool,
):
    """
    TODO
    """
    # Arrange
    cobbler_api.settings().cache_enabled = input_value
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = {"my_value": 5}
    test_system = create_system(profile_name=test_profile.name)
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
def test_dict_cache_invalidate(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_image: Callable[[], Image],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    cache_enabled: bool,
    expected_exception: RaisesContext[CX],
    expected_output: bool,
):
    """
    TODO
    """

    def validate_caches(
        test_api: CobblerAPI,
        objs: List[BaseItem],
        obj_test: Union[BaseItem, Settings, Dict[str, Any]],
        dep: List[BaseItem],
    ):
        """
        TODO
        """
        for obj in objs:
            obj.to_dict(resolved=False)
            obj.to_dict(resolved=True)
        remain_objs = set(objs) - set(dep)
        if isinstance(obj_test, BaseItem):
            remain_objs.remove(obj_test)
            obj_test.owners = "test"
            if (
                obj_test.cache.get_dict_cache(True) is not None
                or obj_test.cache.get_dict_cache(False) is not None
            ):
                return False
        elif obj_test == test_api.settings():
            test_api.clean_items_cache(obj_test)
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
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_repo"
    cobbler_api.add_repo(test_repo)
    objs.append(test_repo)
    test_menu1 = Menu(cobbler_api)
    test_menu1.name = "test_menu1"
    cobbler_api.add_menu(test_menu1)
    objs.append(test_menu1)
    test_menu2 = Menu(cobbler_api)
    test_menu2.name = "test_menu2"
    test_menu2.parent = test_menu1.name
    cobbler_api.add_menu(test_menu2)
    objs.append(test_menu2)
    test_distro = create_distro()
    test_distro.source_repos = [test_repo.name]
    objs.append(test_distro)
    test_profile1 = create_profile(distro_name=test_distro.name, name="test_profile1")
    test_profile1.enable_menu = False
    objs.append(test_profile1)
    test_profile2 = create_profile(
        profile_name=test_profile1.name, name="test_profile2"
    )
    test_profile2.enable_menu = False
    test_profile2.menu = test_menu2.name
    objs.append(test_profile2)
    test_profile3 = create_profile(
        profile_name=test_profile1.name, name="test_profile3"
    )
    test_profile3.enable_menu = False
    test_profile3.repos = [test_repo.name]
    objs.append(test_profile3)
    test_image = create_image()
    test_image.menu = test_menu1.name
    objs.append(test_image)
    test_system1 = create_system(profile_name=test_profile1.name, name="test_system1")
    objs.append(test_system1)
    test_system2 = create_system(image_name=test_image.name, name="test_system2")
    objs.append(test_system2)

    # Act
    repo_dep = test_repo.descendants
    menu1_dep = test_menu1.descendants
    menu2_dep = test_menu2.descendants
    distro_dep = test_distro.descendants
    profile1_dep = test_profile1.descendants
    profile2_dep = test_profile2.descendants
    profile3_dep = test_profile3.descendants
    image_dep = test_image.descendants
    system1_dep = test_system1.descendants
    system2_dep = test_system2.descendants

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
    assert validate_caches(cobbler_api, objs, test_repo, repo_dep) == expected_output
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
        validate_caches(cobbler_api, objs, cobbler_api.settings(), settings_dep)
        == expected_output
    )
    assert (
        validate_caches(cobbler_api, objs, cobbler_api.get_signatures(), signatures_dep)
        == expected_output
    )
    with expected_exception:
        cobbler_api.clean_items_cache(True)
