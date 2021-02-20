import os
import pathlib
import shutil
import time

import pytest
import yaml
from schema import SchemaError

from cobbler import settings
from cobbler.settings import Settings
from tests.conftest import does_not_raise


class TestSettings:
    @pytest.mark.parametrize("test_name,test_value,expected_exception,expected_result", [
        ("server", "127.0.0.1", does_not_raise(), "127.0.0.1"),
        ("manage_forward_zones", True, pytest.raises(AttributeError), []),
        ("does_not_exist", None, pytest.raises(KeyError), None)
    ])
    def test_set(self, test_name, test_value, expected_exception, expected_result):
        # Arrange
        test_settings = Settings()

        # Act
        with expected_exception:
            test_settings.set(test_name, test_value)

            # Assert
            assert test_settings.__dict__[test_name] == expected_result

    def test_to_string(self):
        # Arrange
        test_settings = Settings()

        # Act
        result = test_settings.to_string()

        # Assert
        result_list = result.split("\n")
        assert len(result_list) == 3
        assert result_list[1] == "kernel options  : {}"

    def test_to_dict(self):
        # Arrange
        test_settings = Settings()

        # Act
        result = test_settings.to_dict()

        # Assert
        assert result == test_settings.__dict__

    @pytest.mark.parametrize("parameter,expected_exception,expected_result", [
        ({}, does_not_raise(), "127.0.0.1"),
        (None, does_not_raise(), "127.0.0.1")
    ])
    def test_from_dict(self, parameter, expected_exception, expected_result):
        # Arrange
        test_settings = Settings()

        # Act
        with expected_exception:
            test_settings.from_dict(parameter)

        # Assert
        assert test_settings.server == expected_result


@pytest.mark.parametrize("parameter,expected_exception,expected_result", [
    ({}, pytest.raises(SchemaError), None)
])
def test_validate_settings(parameter, expected_exception, expected_result):
    # Arrange

    # Act
    with expected_exception:
        result = settings.validate_settings(parameter)

        # Assert
        assert result == expected_result


def test_parse_bind_config():
    # Arrange

    # Act
    settings.parse_bind_config("/test_dir/tests/test_data/named.conf")

    # Assert
    assert True


def test_autodect_bind_chroot():
    # Arrange

    # Act
    settings.autodetect_bind_chroot()

    # Assert
    assert True


def test_read_settings_file():
    # Arrange
    # Default path should be fine for the tests.

    # Act
    result = settings.read_settings_file()

    # Assert
    assert isinstance(result, dict)
    assert result.get("include")


def test_update_settings_file(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        settings_read_pre = yaml.safe_load(settings_file)
        settings_read_pre.update({"include": ["mystring"]})

    # Act
    result = settings.update_settings_file(settings_read_pre, filepath=settings_path)

    # Assert
    assert result
    with open(settings_path) as settings_file:
        settings_read_post = yaml.safe_load(settings_file)
        assert "include" in settings_read_post
        assert settings_read_post["include"] == ["mystring"]


def test_update_settings_file_emtpy_dict(tmpdir: pathlib.Path):
    # Arrange
    settings_data = {}
    settings_path = os.path.join(tmpdir, "settings.yaml")

    # Act
    result = settings.update_settings_file(settings_data, filepath=settings_path)

    # Assert
    assert not result


def test_settingsfile_migration_extension(tmpdir: pathlib.Path):
    # Arrange
    src = "/test_dir/tests/test_data/settings_old"
    dst = os.path.join(tmpdir, "settings")
    shutil.copyfile(src, dst)
    expected_path = os.path.join(tmpdir, "settings.yaml")

    # Act
    result_settings = settings.read_settings_file(filepath=dst)

    # Assert
    assert os.path.exists(expected_path)
    assert isinstance(result_settings, dict)
    assert "include" in result_settings


def test_settingsfile_migration_content(tmpdir: pathlib.Path):
    # Arrange
    src = "/test_dir/tests/test_data/settings_old"
    dst = os.path.join(tmpdir, "settings")
    shutil.copyfile(src, dst)

    # Act
    result_settings = settings.read_settings_file(filepath=dst)
    settings_obj = Settings().from_dict(result_settings)
    clean_settings = settings.validate_settings(settings_obj.to_dict())

    # Assert
    assert isinstance(clean_settings, dict)
    assert "include" in result_settings
