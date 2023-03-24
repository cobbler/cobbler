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
    "parameter,expected_exception,expected_result,ignore_keys",
    [
        ({"include": "bla"}, pytest.raises(SchemaError), False, []),
        ({}, does_not_raise(), {}, []),
        ({"server": "192.168.0.1"}, does_not_raise(), {"server": "192.168.0.1"}, []),
        (
            {"server": "192.168.0.1", "foobar": 1234},
            pytest.raises(SchemaError),
            False,
            [],
        ),
        (
            {"server": "192.168.0.1", "foobar": 1234},
            does_not_raise(),
            {"server": "192.168.0.1", "foobar": 1234},
            ["foobar"],
        ),
        (
            {
                "server": "192.168.0.1",
                "foobar2": 1234,
                "extra_settings_list": ["foobar2"],
            },
            does_not_raise(),
            {
                "server": "192.168.0.1",
                "foobar2": 1234,
                "extra_settings_list": ["foobar2"],
            },
            [],
        ),
        (
            {"server": "192.168.0.1", "foobar2": 1234},
            pytest.raises(SchemaError),
            False,
            ["foobar"],
        ),
        (
            {
                "server": "192.168.0.1",
                "foobar": 1234,
                "foobar2": 1234,
                "extra_settings_list": ["foobar2"],
            },
            pytest.raises(SchemaError),
            False,
            [],
        ),
        (
            {"server": "192.168.0.1", "foobar": 1234, "foobar2": 1234},
            pytest.raises(SchemaError),
            False,
            ["foobar"],
        ),
        (
            {
                "server": "192.168.0.1",
                "foobar": 1234,
                "foobar2": 1234,
                "extra_settings_list": ["foobar2"],
            },
            does_not_raise(),
            {
                "server": "192.168.0.1",
                "extra_settings_list": ["foobar2"],
                "foobar": 1234,
                "foobar2": 1234,
            },
            ["foobar"],
        ),
    ],
)
def test_validate_settings(parameter, expected_exception, expected_result, ignore_keys):
    # Arrange

    # Act
    with expected_exception:
        result = settings.validate_settings(parameter, ignore_keys)

        # Assert
        assert result == expected_result


def test_read_settings_file_with_ignore_keys(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        new_settings = yaml.safe_load(settings_file)
        new_settings.update({"foobar": 1234})
    with open(settings_path, "w") as new_settings_file:
        new_settings_file.write(yaml.dump(new_settings))

    # Act
    result = settings.read_settings_file(settings_path, ignore_keys=["foobar"])

    with open(settings_path, "w") as new_settings_file:
        new_settings.pop("foobar")
        new_settings_file.write(yaml.dump(new_settings))

    # Assert
    assert isinstance(result, dict)
    assert result.get("server")
    assert result.get("foobar")


def test_read_settings_file_with_ignore_keys_failing(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        new_settings = yaml.safe_load(settings_file)
        new_settings.update({"foobar": 1234})
    with open(settings_path, "w") as new_settings_file:
        new_settings_file.write(yaml.dump(new_settings))

    # Act
    result = settings.read_settings_file(settings_path)

    with open(settings_path, "w") as new_settings_file:
        new_settings.pop("foobar")
        new_settings_file.write(yaml.dump(new_settings))

    # Assert
    assert not result


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


def test_update_settings_file_ignore_keys_failing(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        settings_read_pre = yaml.safe_load(settings_file)
        settings_read_pre.update({"grub2_mod_dir": "/usr/share/grub2"})
        settings_read_pre["foobar"] = 1234

    # Act
    result = settings.update_settings_file(settings_read_pre, filepath=settings_path)

    # Assert
    assert not result


def test_update_settings_file_ignore_keys_success(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        settings_read_pre = yaml.safe_load(settings_file)
        settings_read_pre.update({"grub2_mod_dir": "/usr/share/grub2"})
        settings_read_pre["foobar"] = 1234

    # Act
    result = settings.update_settings_file(
        settings_read_pre, filepath=settings_path, ignore_keys=["foobar"]
    )

    # Assert
    assert result
    with open(settings_path) as settings_file:
        settings_read_post = yaml.safe_load(settings_file)
        assert "grub2_mod_dir" in settings_read_post
        assert settings_read_post["grub2_mod_dir"] == "/usr/share/grub2"
        assert "foobar" in settings_read_post
        assert settings_read_post["foobar"] == 1234


def test_update_settings_file_extra_settings_list(tmpdir: pathlib.Path):
    # Arrange
    src = "/etc/cobbler/settings.yaml"
    settings_path = os.path.join(tmpdir, "settings.yaml")
    shutil.copyfile(src, settings_path)
    with open(settings_path) as settings_file:
        settings_read_pre = yaml.safe_load(settings_file)
        settings_read_pre.update({"grub2_mod_dir": "/usr/share/grub2"})
        settings_read_pre["extra_settings_list"] = ["foobar"]
        settings_read_pre["foobar"] = 1234

    # Act
    result = settings.update_settings_file(settings_read_pre, filepath=settings_path)

    # Assert
    assert result
    with open(settings_path) as settings_file:
        settings_read_post = yaml.safe_load(settings_file)
        assert "grub2_mod_dir" in settings_read_post
        assert settings_read_post["grub2_mod_dir"] == "/usr/share/grub2"
        assert "foobar" in settings_read_post
        assert settings_read_post["foobar"] == 1234


def test_update_settings_file_emtpy_dict(tmpdir: pathlib.Path):
    # Arrange
    settings_data = {}
    settings_path = os.path.join(tmpdir, "settings.yaml")

    # Act
    result = settings.update_settings_file(settings_data, filepath=settings_path)

    # Assert
    assert result
