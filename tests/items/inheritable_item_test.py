from typing import Any, Callable, Optional

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile

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


def test_children(cobbler_api: CobblerAPI):
    """
    Assert that a given Cobbler Item successfully returns the list of child objects.
    """
    # Arrange
    titem = Distro(cobbler_api, name="test_children")

    # Act
    result = titem.children

    # Assert
    assert result == []


def test_tree_walk(cobbler_api: CobblerAPI):
    """
    Assert that all descendants of a Cobbler Item are correctly captured by called the method.
    """
    # Arrange
    titem = Distro(cobbler_api, name="test_tree_walk")

    # Act
    result = titem.tree_walk()

    # Assert
    assert result == []


def test_grab_tree(cobbler_api: CobblerAPI):
    """
    Assert that grabbing the item tree is containing the settings.
    """
    # Arrange
    object_to_check = Distro(cobbler_api)
    # TODO: Create some objects and give them some inheritance.

    # Act
    result = object_to_check.grab_tree()

    # Assert
    assert isinstance(result, list)
    # pylint: disable-next=no-member
    assert result[-1].server == "192.168.1.1"  # type: ignore
