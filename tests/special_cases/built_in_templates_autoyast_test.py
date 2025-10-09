"""
Test module to extensively verify the built-in AutoYaST Template.
"""

from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall_manager import AutoInstallationManager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_sample_autoyast_xml(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample autoyast XML template.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_autoyast.xml"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile.name, None)

    # Assert
    # TODO: Extend assertion
    assert isinstance(result, str)
