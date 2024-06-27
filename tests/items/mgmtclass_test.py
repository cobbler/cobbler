import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.mgmtclass import Mgmtclass


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(
        name="mgmtclass_setting_mock", spec=cobbler_api.settings()
    )
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    mgmtclass = Mgmtclass(cobbler_api)

    # Arrange
    assert isinstance(mgmtclass, Mgmtclass)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    result = mgmtclass.make_clone()

    # Arrange
    assert result != mgmtclass


def test_check_if_valid(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)
    mgmtclass.name = "unittest_mgmtclass"

    # Act
    mgmtclass.check_if_valid()

    # Assert
    assert True


def test_packages(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.packages = ""

    # Assert
    assert mgmtclass.packages == []


def test_files(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.files = ""

    # Assert
    assert mgmtclass.files == []


def test_params(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.params = ""

    # Assert
    assert mgmtclass.params == {}


def test_is_definition(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.is_definition = False

    # Assert
    assert not mgmtclass.is_definition


def test_class_name(cobbler_api: CobblerAPI):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.class_name = ""

    # Assert
    assert mgmtclass.class_name == ""


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    titem = Mgmtclass(cobbler_api)

    # Act
    for key, key_value in titem.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(titem, new_key)
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

            prev_value = getattr(titem, new_key)
            setattr(titem, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(titem, new_key)
