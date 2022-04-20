import os
import pathlib
import shutil

import pytest
import yaml
from schema import SchemaError

from cobbler import settings
from cobbler.settings import Settings
from tests.conftest import does_not_raise


def test_to_string():
    # Arrange
    test_settings = Settings()

    # Act
    result = test_settings.to_string()

    # Assert
    result_list = result.split("\n")
    assert len(result_list) == 3
    assert result_list[1] == "kernel options  : {}"


def test_to_dict():
    # Arrange
    test_settings = Settings()

    # Act
    result = test_settings.to_dict()

    # Assert
    assert result == test_settings.__dict__


def test_is_valid():
    # Arrange
    test_settings = settings.Settings()

    # Act
    result = test_settings.is_valid()

    # Arrange
    assert result is True


@pytest.mark.parametrize(
    "parameter,expected_exception,expected_result",
    [
        ({}, does_not_raise(), "127.0.0.1"),
        (None, does_not_raise(), "127.0.0.1"),
        ({"invalid": True}, pytest.raises(ValueError), "127.0.0.1"),
    ],
)
def test_from_dict(parameter, expected_exception, expected_result):
    # Arrange
    test_settings = Settings()

    # Act
    with expected_exception:
        test_settings.from_dict(parameter)

    # Assert
    assert test_settings.server == expected_result


@pytest.mark.parametrize(
    "parameter,expected_exception,expected_result",
    [
        ({"include": "bla"}, pytest.raises(SchemaError), False),
        # ({}, pytest.raises(SchemaError), {}), # Does not work because I don't want to hand in 150 dict keys.
    ],
)
def test_validate_settings(parameter, expected_exception, expected_result):
    # Arrange

    # Act
    with expected_exception:
        result = settings.validate_settings(parameter)

        # Assert
        assert result == expected_result


def test_read_settings_file():
    # Arrange
    # Default path should be fine for the tests.

    # Act
    result = settings.read_settings_file()

    # Assert
    assert isinstance(result, dict)
    assert result.get("server")


def test_update_settings_file(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        settings_read_pre = yaml.safe_load(settings_file)
        settings_read_pre.update({"grub2_mod_dir": "/usr/share/grub2"})

    # Act
    result = settings.update_settings_file(settings_read_pre, filepath=settings_path)

    # Assert
    assert result
    with open(settings_path) as settings_file:
        settings_read_post = yaml.safe_load(settings_file)
        assert "grub2_mod_dir" in settings_read_post
        assert settings_read_post["grub2_mod_dir"] == "/usr/share/grub2"


def test_update_settings_file_emtpy_dict(tmpdir: pathlib.Path):
    # Arrange
    settings_data = {}
    settings_path = os.path.join(tmpdir, "settings.yaml")

    # Act
    result = settings.update_settings_file(settings_data, filepath=settings_path)

    # Assert
    assert result
