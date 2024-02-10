"""
Test module to assert that the functionality of inheritable items is given. This is ensured with the concrete item type
"Distro".
"""

from typing import Any, Callable, Optional

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System

from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "input_depth,expected_exception,expected_result",
    [
        ("", pytest.raises(TypeError), None),
        (5, does_not_raise(), 5),
    ],
)
def test_depth(
    cobbler_api: CobblerAPI,
    input_depth: Any,
    expected_exception: Any,
    expected_result: Optional[int],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the depth property correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    with expected_exception:
        titem.depth = input_depth

        # Assert
        assert titem.depth == expected_result


def test_parent(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the parent property correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    titem.parent = ""

    # Assert
    assert titem.parent is None


def test_children(cobbler_api: CobblerAPI):
    """
    Assert that a given Cobbler Item successfully returns the list of child objects.
    """
    # pylint: disable=use-implicit-booleaness-not-comparison
    # Arrange
    titem = Distro(cobbler_api)

    # Act

    # Assert
    assert titem.children == []


def test_tree_walk(cobbler_api: CobblerAPI):
    """
    Assert that all decendants of a Cobbler Item are correctly captured by called the method.
    """
    # pylint: disable=use-implicit-booleaness-not-comparison
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.tree_walk()

    # Assert
    assert result == []


def test_item_descendants(cobbler_api: CobblerAPI):
    """
    Assert that all decendants of a Cobbler Item are correctly captured by called the property.
    """
    # pylint: disable=use-implicit-booleaness-not-comparison
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.descendants

    # Assert
    assert result == []


def test_descendants(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_image: Callable[[], Image],
    create_profile: Callable[[str, str], Profile],
    create_system: Callable[[str, str], System],
):
    """
    Assert that the decendants property is also working with an enabled Cache.
    """
    # Arrange
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_repo"
    cobbler_api.add_repo(test_repo)
    test_menu1 = Menu(cobbler_api)
    test_menu1.name = "test_menu1"
    cobbler_api.add_menu(test_menu1)
    test_menu2 = Menu(cobbler_api)
    test_menu2.name = "test_menu2"
    test_menu2.parent = test_menu1.name
    cobbler_api.add_menu(test_menu2)
    test_distro = create_distro()
    test_profile1: Profile = create_profile(distro_name=test_distro.name, name="test_profile1")  # type: ignore
    test_profile1.enable_menu = False
    test_profile1.repos = [test_repo.name]
    test_profile2: Profile = create_profile(
        profile_name=test_profile1.name, name="test_profile2"  # type: ignore
    )
    test_profile2.enable_menu = False
    test_profile2.menu = test_menu2.name
    test_profile3: Profile = create_profile(
        profile_name=test_profile1.name, name="test_profile3"  # type: ignore
    )
    test_profile3.enable_menu = False
    test_profile3.repos = [test_repo.name]
    test_image = create_image()
    test_image.menu = test_menu1.name
    test_system1: System = create_system(profile_name=test_profile1.name, name="test_system1")  # type: ignore
    test_system2: System = create_system(image_name=test_image.name, name="test_system2")  # type: ignore

    # Act
    cache_tests = [
        test_repo.descendants,
        test_distro.descendants,
        test_image.descendants,
        test_profile1.descendants,
        test_profile2.descendants,
        test_profile3.descendants,
        test_menu1.descendants,
        test_menu2.descendants,
        test_system1.descendants,
        test_system2.descendants,
    ]
    results = [
        [test_profile1, test_profile2, test_profile3, test_system1],
        [test_profile1, test_profile2, test_profile3, test_system1],
        [test_system2],
        [test_profile2, test_profile3, test_system1],
        [],
        [],
        [test_image, test_menu2, test_profile2, test_system2],
        [test_profile2],
        [],
        [],
    ]

    # Assert
    for index, x in enumerate(cache_tests):
        assert set(x) == set(results[index])


def test_get_conceptual_parent(
    request: "pytest.FixtureRequest",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Assert that retrieving the conceptual parent is working as expected.
    """
    # Arrange
    tmp_distro = create_distro()
    tmp_profile = create_profile(tmp_distro.name)
    titem = Profile(cobbler_api)
    titem.name = "subprofile_%s" % (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    titem.parent = tmp_profile.name

    # Act
    result = titem.get_conceptual_parent()

    # Assert
    assert result is not None
    assert result.name == tmp_distro.name
