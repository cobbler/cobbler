"""
Test module to extensively verify the built-in Cloud-Init Template.
"""

from typing import Callable

import pytest
import yaml

from cobbler.api import CobblerAPI
from cobbler.autoinstall.manager import AutoInstallationManager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_cloud_init_meta_data(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in default Cloud-Init meta-data template.
    """
    # Arrange
    expected_result = [
        "instance-id: example",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-meta-data")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    target_template.tags.add("meta-data")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template
    test_profile.autoinstall_meta = {"cloud_init_instance_id": "example"}

    # Act
    result = autoinstall_manager.generate_autoinstall(
        test_profile, target_template, "meta-data"
    )

    # Assert
    assert isinstance(result, str)
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_user_data(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in default Cloud-Init meta-data template.
    """
    # Arrange
    expected_result = [
        "#cloud-config",
        "",
        "zypper:",
        "  config:",
        "    download.use_deltarpm: true",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-user-data")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    target_template.tags.add("user-data")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template
    test_profile.autoinstall_meta = {
        "cloud_init_user_data_modules": ["zypper-add-repo"],
        "cloud_init_zypper": {"config": {"download.use_deltarpm": True}},
    }

    # Act
    result = autoinstall_manager.generate_autoinstall(
        test_profile, target_template, "user-data"
    )

    # Assert
    assert isinstance(result, str)
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_network_config(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in default Cloud-Init meta-data template.
    """
    # Arrange
    expected_result = [
        "network:",
        "  version: 1",
        "  config:",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-network-config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    target_template.tags.add("meta-data")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template
    test_profile.autoinstall_meta = {"cloud_init_network": {}}

    # Act
    result = autoinstall_manager.generate_autoinstall(
        test_profile, target_template, "meta-data"
    )

    # Assert
    assert isinstance(result, str)
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)
