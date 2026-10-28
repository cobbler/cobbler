"""
Test module to verify the functionality of the Cloud-Init autoinstall generator.
"""

from typing import Any, Callable

import pytest
import yaml

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.cloud_init import CloudInitGenerator
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_cloud_init_generate_autoinstall(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the built-in template renderes with the Cloud-Init generator.
    """
    # Arrange
    expected_result = "instance-id: example-id"
    target_template = cobbler_api.find_template(False, False, name="built-in-meta-data")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_system.autoinstall_meta = {"cloud_init_instance_id": "example-id"}
    test_generator = CloudInitGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(
        test_system, target_template, "meta-data"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == expected_result


def test_cloud_init_generate_autoinstall_user_data_injects_nopxe_late_command(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test that a system-targeted Subiquity ``autoinstall`` mapping automatically gets a ``late-commands`` entry
    disabling PXE/network boot for that system, mirroring the Preseed/AutoYaST ``autoinstall_done`` built-in.
    """
    # Arrange
    target_template = cobbler_api.find_template(False, False, name="built-in-user-data")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_system.autoinstall_meta = {
        "cloud_init_user_data_modules": ["ubuntu-autoinstall"],
        "cloud_init_ubuntu_autoinstall": {"version": 1},
    }
    test_generator = CloudInitGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(
        test_system, target_template, "user-data"
    )

    # Assert
    parsed = yaml.safe_load(result)
    late_commands = parsed["autoinstall"]["late-commands"]
    expected_url = (
        f"http://{cobbler_api.settings().server}"
        f"/cblr/svc/op/nopxe/system/{test_system.name}"
    )
    assert any(expected_url in command for command in late_commands)


def test_cloud_init_generate_autoinstall_nopxe_does_not_leak_across_systems(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test that injecting the ``nopxe`` late-command does not mutate the shared Profile's own persisted
    ``autoinstall_meta``, and that two Systems inheriting the same Profile each get their own correctly-targeted
    ``nopxe`` URL rather than leaking one System's URL into the other's rendered ``user-data``.
    """
    # Arrange
    target_template = cobbler_api.find_template(False, False, name="built-in-user-data")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall_meta = {
        "cloud_init_user_data_modules": ["ubuntu-autoinstall"],
        "cloud_init_ubuntu_autoinstall": {
            "version": 1,
            "late-commands": ["echo my-custom-command"],
        },
    }
    system_a: System = create_system(
        profile_uid=test_profile.uid, name="cloud-init-system-a"
    )
    system_b: System = create_system(
        profile_uid=test_profile.uid, name="cloud-init-system-b"
    )
    system_a.autoinstall = target_template
    system_b.autoinstall = target_template
    test_generator = CloudInitGenerator(cobbler_api)

    # Act
    result_a = test_generator.generate_autoinstall(
        system_a, target_template, "user-data"
    )
    result_b = test_generator.generate_autoinstall(
        system_b, target_template, "user-data"
    )

    # Assert - each system's rendered user-data points nopxe at itself, not the other system
    for system, result in ((system_a, result_a), (system_b, result_b)):
        expected_url = (
            f"http://{cobbler_api.settings().server}"
            f"/cblr/svc/op/nopxe/system/{system.name}"
        )
        late_commands = yaml.safe_load(result)["autoinstall"]["late-commands"]
        nopxe_commands = [c for c in late_commands if "/cblr/svc/op/nopxe/" in c]
        assert len(nopxe_commands) == 1
        assert expected_url in nopxe_commands[0]
        assert "echo my-custom-command" in late_commands

    # Assert - the shared Profile's own persisted autoinstall_meta was never mutated
    assert test_profile.autoinstall_meta["cloud_init_ubuntu_autoinstall"][
        "late-commands"
    ] == ["echo my-custom-command"]


def test_cloud_init_generate_autoinstall_metadata(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the generator can successfully generate the metadata for Cloud-Init.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = CloudInitGenerator(cobbler_api)

    # Act
    test_generator.generate_autoinstall_metadata(test_system, "")

    # Assert - no exception is good enough for now
    assert True
