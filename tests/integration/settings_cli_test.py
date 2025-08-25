"""
This test package is responsible for ensuring that the Cobbler CLI "cobbler-settings" is able to manipulate the config
file in the desired ways.
"""

import pathlib
import shutil
from configparser import ConfigParser
from typing import Any, Callable, Dict

import pytest

from cobbler.remote import CobblerXMLRPCInterface
from cobbler.settings import cli as cobbler_settings


@pytest.mark.integration
def test_settings_cli_automigrate_disable(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can disable the auto-migration of the YAML
    """
    # Arrange
    test_config_path = tmp_path / "settings.yaml"
    test_config = "auto_migrate_settings: true\n"
    test_config_path.write_text(test_config)
    expected_result = pathlib.Path(
        "/code/tests/integration/data/test_settings_cli_automigrate_disable/expected_result.yaml"
    ).read_text(encoding="UTF-8")

    # Act
    cobbler_settings.main(["-c", str(test_config_path), "automigrate", "--disable"])

    # Assert
    result = test_config_path.read_text(encoding="UTF-8")
    assert result == expected_result


@pytest.mark.integration
def test_settings_cli_automigrate_enable(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can enable the auto-migration of the YAML
    """
    # Arrange
    test_config_path = tmp_path / "settings.yaml"
    test_config = "auto_migrate_settings: false\n"
    test_config_path.write_text(test_config)
    expected_result = pathlib.Path(
        "/code/tests/integration/data/test_settings_cli_automigrate_enable/expected_result.yaml"
    ).read_text(encoding="UTF-8")

    # Act
    cobbler_settings.main(["-c", str(test_config_path), "automigrate", "--enable"])

    # Assert
    result = test_config_path.read_text(encoding="UTF-8")
    assert result == expected_result


@pytest.mark.integration
def test_settings_cli_migrate():
    """
    Check that cobbler-settings can migrate the YAML file from one version to the next one
    """
    # Arrange
    old_config = (
        "tests/integration/data/test_settings_cli_migrate/settings-expected.yaml"
    )
    new_config = "tests/integration/data/test_settings_cli_migrate/settings-new.yaml"
    expected_config = (
        "tests/integration/data/test_settings_cli_migrate/settings-expected.yaml"
    )
    new_version = "3.4.0"

    # Act
    # Test migration from 3.3.2 to 3.4.0
    cobbler_settings.main(
        ["-c", str(old_config), "migrate", "-t", str(new_config), "--new", new_version]
    )

    # Assert
    assert pathlib.Path(expected_config).read_text(encoding="UTF-8") == pathlib.Path(
        new_config
    ).read_text(encoding="UTF-8")


@pytest.mark.integration
def test_settings_cli_migrate_from_2_8_5(
    create_distro: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
    restart_cobbler: Callable[[], None],
):
    """
    Check that cobbler-settings can migrate the YAML file from one version to the next one
    """
    # Arrange
    old_config = (
        "tests/integration/data/test_settings_cli_migrate_from_2_8_5/settings-old.yaml"
    )
    new_config = (
        "tests/integration/data/test_settings_cli_migrate_from_2_8_5/settings-new.yaml"
    )
    new_version = "3.3.0"

    # Create new distro
    create_distro(
        {
            "name": "fake",
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
            "boot_loaders": "<<inherit>>",
        }
    )

    # Move collections to old "config" place to be processed during migration
    shutil.rmtree("/var/lib/cobbler/config/", ignore_errors=True)
    shutil.copytree("/var/lib/cobbler/collections/", "/var/lib/cobbler/config/")
    shutil.move("/var/lib/cobbler/config/distros", "/var/lib/cobbler/config/distros.d")

    # Fake the current installed version
    shutil.copy2("/etc/cobbler/version", "/etc/cobbler/version.bak")
    version_file = "/etc/cobbler/version"
    config = ConfigParser()
    config.read(version_file)
    config["cobbler"]["version"] = "3.3.0"
    with open(version_file, "w", encoding="UTF-8") as version_file_fh:
        config.write(version_file_fh)
    # sed -i s'/version = .*/version = 3.3.0/g'
    pathlib.Path("/etc/cobbler/modules.conf").touch()

    # Act
    # Test migration from old 2.8.5 to 3.3.0
    # Perform the migration of collections
    cobbler_settings.main(
        ["-c", str(old_config), "migrate", "-t", str(new_config), "--new", new_version]
    )

    # Cleanup
    # Remove faked Cobbler version
    shutil.copy2("/etc/cobbler/version.bak", "/etc/cobbler/version")

    # Restart cobblerd after migration to reload migrated collections
    restart_cobbler()

    # Assert - Boot loaders should be preserved after migration.
    assert (
        remote.get_distro("fake", False, False, token).get("boot_loaders") == "<<inherit>>"  # type: ignore
    )

    # Cleanup
    shutil.rmtree("/var/lib/cobbler/config/", ignore_errors=True)


@pytest.mark.integration
def test_settings_cli_modify_bool(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """
    # Arrange
    test_config = tmp_path / "settings-bool.yaml"
    test_config_content = "auto_migrate_settings: false\n"
    test_config.write_text(test_config_content)
    test_key = "enable_ipxe"
    test_value = "true"

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert f"{test_key}: {test_value}" in test_config.read_text(encoding="UTF-8")


@pytest.mark.integration
def test_settings_cli_modify_dict(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """
    # Arrange
    test_config = tmp_path / "settings-dict.yaml"
    test_config_content = "kernel_options:\n  from_cobbler: true"
    test_config.write_text(test_config_content)
    test_key = "kernel_options"
    test_value = ""
    expected_config = pathlib.Path(
        "/code/tests/integration/data/test_settings_cli_modify_dict/expected_config.yaml"
    )

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert expected_config.read_text(encoding="UTF-8") == test_config.read_text(
        encoding="UTF-8"
    )


@pytest.mark.integration
def test_settings_cli_modify_float(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """
    # Arrange
    test_config = tmp_path / "settings-int.yaml"
    test_config_content = "default_virt_file_size: 5.0\n"
    test_config.write_text(test_config_content)
    test_key = "default_virt_file_size"
    test_value = "10.0"

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert f"{test_key}: {test_value}" in test_config.read_text(encoding="UTF-8")


@pytest.mark.integration
def test_settings_cli_modify_int(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """
    # Arrange
    test_config = tmp_path / "settings-int.yaml"
    test_config_content = "default_virt_ram: 512\n"
    test_config.write_text(test_config_content)
    test_key = "default_virt_ram"
    test_value = "1024"

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert f"{test_key}: {test_value}" in test_config.read_text(encoding="UTF-8")


@pytest.mark.integration
def test_settings_cli_modify_list(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """
    # Arrange
    test_folder = pathlib.Path(
        "/code/tests/integration/data/test_settings_cli_modify_list/"
    )
    original_config = test_folder / "original_config.yaml"
    test_config = tmp_path / "settings-list.yaml"
    shutil.copy(str(original_config), str(test_config))
    test_key = "build_reporting_email"
    test_value = ""
    expected_config = test_folder / "expected_config.yaml"

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert expected_config.read_text(encoding="UTF-8") == test_config.read_text(
        encoding="UTF-8"
    )


@pytest.mark.integration
def test_settings_cli_modify_str(tmp_path: pathlib.Path):
    """
    Check that cobbler-settings can modify value from the YAML
    """

    # Arrange
    test_config = tmp_path / "settings-str.yaml"
    test_config_content = 'buildisodir: "/var/cache/cobbler/buildiso"\n'
    test_config.write_text(test_config_content)
    test_key = "buildisodir"
    test_value = "/my/custom/directory"

    # Act
    cobbler_settings.main(
        ["-c", str(test_config), "modify", "-k", test_key, "-v", test_value]
    )

    # Assert
    assert f"{test_key}: {test_value}" in test_config.read_text(encoding="UTF-8")


@pytest.mark.integration
def test_settings_cli_verify():
    """
    Check that cobbler-settings can verify the YAML configuration
    """
    # Arrange
    test_config = pathlib.Path("/code/tests/test_data/V3_0_0/settings.yaml")
    config_version = "3.0.0"

    # Act & Assert
    cobbler_settings.main(["-c", str(test_config), "validate", "-v", config_version])
