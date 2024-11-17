"""
Tests that validate the functionality of the module that is responsible for providing basic item functionality.
"""

import copy
from typing import Any, List, Optional

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.abstract.base_item import BaseItem

from tests.conftest import does_not_raise


class MockItem(BaseItem):
    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        super().__init__(api, *args, **kwargs)
        self._inmemory = True

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self) -> BaseItem:
        _dict = copy.deepcopy(self.to_dict())
        # Drop attributes which are computed from other attributes
        computed_properties = ["uid"]
        for property_name in computed_properties:
            _dict.pop(property_name, None)
        return MockItem(self.api, **_dict)

    def _resolve(self, property_name: str) -> Any:
        settings_name = property_name
        if property_name == "owners":
            settings_name = "default_ownership"
        attribute = "_" + property_name
        attribute_value = getattr(self, attribute)

        if attribute_value == enums.VALUE_INHERITED:
            settings = self.api.settings()
            possible_return = None
            if hasattr(settings, settings_name):
                possible_return = getattr(settings, settings_name)
            elif hasattr(settings, f"default_{settings_name}"):
                possible_return = getattr(settings, f"default_{settings_name}")

            if possible_return is not None:
                return possible_return

        return attribute_value

    @property
    def uid(self) -> str:
        """
        The uid is the internal unique representation of a Cobbler object. It should never be used twice, even after an
        object was deleted.

        :getter: The uid for the item. Should be unique across a running Cobbler instance.
        :setter: The new uid for the object. Should only be used by the Cobbler Item Factory.
        """
        return self._uid

    @uid.setter
    def uid(self, uid: str) -> None:
        """
        Setter for the uid of the item.

        :param uid: The new uid.
        """
        self._uid = uid


def test_uid(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the uid property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    titem.uid = "uid"

    # Assert
    assert titem.uid == "uid"


@pytest.mark.parametrize(
    "input_ctime,expected_exception,expected_result",
    [("", pytest.raises(TypeError), None), (0.0, does_not_raise(), 0.0)],
)
def test_ctime(
    cobbler_api: CobblerAPI,
    input_ctime: Any,
    expected_exception: Any,
    expected_result: float,
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the ctime property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    with expected_exception:
        titem.ctime = input_ctime

        # Assert
        assert titem.ctime == expected_result


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (0.0, does_not_raise()),
        (0, pytest.raises(TypeError)),
        ("", pytest.raises(TypeError)),
    ],
)
def test_mtime(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the mtime property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    with expected_exception:
        titem.mtime = value

        # Assert
        assert titem.mtime == value


def test_name(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the name property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    titem.name = "testname"

    # Assert
    assert titem.name == "testname"


def test_comment(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the comment property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    titem.comment = "my comment"

    # Assert
    assert titem.comment == "my comment"


@pytest.mark.parametrize(
    "input_owners,expected_exception,expected_result",
    [
        ("", does_not_raise(), []),
        (enums.VALUE_INHERITED, does_not_raise(), ["admin"]),
        ("Test1 Test2", does_not_raise(), ["Test1", "Test2"]),
        (["Test1", "Test2"], does_not_raise(), ["Test1", "Test2"]),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_owners(
    cobbler_api: CobblerAPI,
    input_owners: Any,
    expected_exception: Any,
    expected_result: Optional[List[str]],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the owners property correctly.
    """
    # Arrange
    titem = MockItem(cobbler_api)

    # Act
    with expected_exception:
        titem.owners = input_owners

        # Assert
        assert titem.owners == expected_result


def test_check_if_valid(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Asserts that the check for a valid item is performed successfuly.
    """
    # Arrange
    titem = MockItem(cobbler_api)
    titem.name = (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )

    # Act
    titem.check_if_valid()

    # Assert
    assert True  # This test passes if there is no exception raised
