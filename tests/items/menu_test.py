"""
Tests that validate the functionality of the module that is responsible for providing menu related functionality.
"""

from typing import TYPE_CHECKING

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.menu import Menu
from cobbler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    settings = mocker.MagicMock(name="menu_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    distro = Menu(cobbler_api)

    # Arrange
    assert isinstance(distro, Menu)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    menu = Menu(cobbler_api)

    # Act
    result = menu.make_clone()

    # Assert
    assert menu != result


def test_display_name(cobbler_api: CobblerAPI):
    # Arrange
    menu = Menu(cobbler_api)

    # Act
    menu.display_name = ""

    # Assert
    assert menu.display_name == ""


def test_to_dict(cobbler_api: CobblerAPI):
    # Arrange
    titem = Menu(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    # Arrange
    titem = Menu(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert enums.VALUE_INHERITED not in str(result)


def test_inheritance(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings: Settings
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    menu = Menu(cobbler_api)

    # Act
    for key, key_value in menu.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(menu, new_key)
            settings_name = new_key
            if new_key == "owners":
                settings_name = "default_ownership"
            if hasattr(test_settings, f"default_{settings_name}"):
                settings_name = f"default_{settings_name}"
            if hasattr(test_settings, settings_name):
                setting = getattr(test_settings, settings_name)
                if isinstance(setting, str):
                    new_value = "test_inheritance"
                elif isinstance(setting, bool):
                    new_value = True
                elif isinstance(setting, int):
                    new_value = 1
                elif isinstance(setting, float):
                    new_value = 1.0
                elif isinstance(setting, dict):
                    new_value = {"test_inheritance": "test_inheritance"}
                elif isinstance(setting, list):
                    new_value = ["test_inheritance"]
                setattr(test_settings, settings_name, new_value)

            prev_value = getattr(menu, new_key)
            setattr(menu, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(menu, new_key)
