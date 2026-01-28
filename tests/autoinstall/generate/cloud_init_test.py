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
