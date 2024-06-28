import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.file import File
from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(name="file_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    distro = File(cobbler_api)

    # Arrange
    assert isinstance(distro, File)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    file = File(cobbler_api)

    # Act
    clone = file.make_clone()

    # Assert
    assert clone != file


# Properties Tests


@pytest.mark.parametrize("value,expected_exception", [
    (False, does_not_raise())
])
def test_is_dir(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    file = File(cobbler_api)

    # Act
    with expected_exception:
        file.is_dir = value

        # Assert
        assert file.is_dir is value


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    file = File(cobbler_api)

    # Act
    for key, key_value in file.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(file, new_key)
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

            prev_value = getattr(file, new_key)
            setattr(file, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(file, new_key)
