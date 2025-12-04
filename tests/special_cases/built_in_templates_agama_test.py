"""
Test module to extensively verify the built-in Agama Template.
"""

# FIXME: Enable exact result checking!

import json
from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.manager import AutoInstallationManager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_autoinst_json_profile_minimal(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in default kickstart template.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert isinstance(result, str)
    assert json.loads(result)


def test_built_in_autoinst_json_system_minimal(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify the built-in default kickstart template.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_system, target_template)

    # Assert
    assert isinstance(result, str)
    assert json.loads(result)


def test_built_in_autoinst_json_system_maximal(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify the built-in default kickstart template.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_system.autoinstall_meta = {
        "agama_product_registration_code": "INTERNAL-USE-ONLY-e32a-f6be",
        "agama_product_id": "SLES",
        "agama_root_password": "$6$IZeqHOaZ$uBmMXlSkpkimLquYAaMntK81ImMGv1ipkk3SWludd84sEzUyWVzr8FpjyveD//zn2Gh0nDRSMDlrP9blqWjI81",
        # TODO: Support merging of lists via inheritance
        "agama_software_patterns": '"base", "cockpit", "kvm_server", "selinux"',
        "agama_software_packages": '"bash", "efibootmgr", "grub2", "grub2-arm64-efi", "openssh", "zypper"',
        "agama_scripts": {"pre": ["test"]},
        "agama_bootloader_stop_on_boot_menu": True,
        "agama_storage_legacy": {"use": "all", "partitions": []},
    }

    # Act
    result = autoinstall_manager.generate_autoinstall(test_system, target_template)

    # Assert
    assert isinstance(result, str)
    assert json.loads(result)
