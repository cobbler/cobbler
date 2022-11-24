"""
Test module to verify the functionality of the Agama autoinstall generator.
"""

import json
from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.agama import AgamaGenerator
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_agama_generate_autoinstall(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the built-in template renderes with the Agama generator.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(test_system, target_template)

    # Assert
    assert json.loads(result)


def test_agama_generate_autoinstall_metatdata(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the generator can successfully generate the metadata for Agama.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    test_generator.generate_autoinstall_metadata(test_system, "")

    # Assert - no exception is good enough for now
    assert True
