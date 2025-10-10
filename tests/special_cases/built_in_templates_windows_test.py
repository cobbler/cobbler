"""
Test module to extensively verify the built-in Windows Template.
"""

from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.manager import AutoInstallationManager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_windows_xml(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample Windows XML template.
    """
    # Arrange
    expected_result = [
        "REM Sample kickstart file for Windows distributions.",
        "Echo on",
        ":wno10",
        "set n=0",
        "",
        ":wno20",
        "ping 192.168.1.1 -n 3",
        "set exit_code=%ERRORLEVEL%",
        "",
        "IF %exit_code% EQU 0 GOTO wno_exit",
        "set /a n=n+1",
        "IF %n% lss 30 goto wno20",
        "pause",
        "goto wno10",
        "",
        ":wno_exit",
        "",
        "",
        "exit",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-win.xml")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)
