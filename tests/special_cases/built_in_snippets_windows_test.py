"""
Test module for verifying built-in Windows snippets in Cobbler.
"""

from typing import Any, Dict

import pytest

from cobbler.api import CobblerAPI


def test_built_in_windows_wait_network_online(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Windows snippet "built-in-wait_network_online".
    """
    # Arrange
    expected_result = [
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
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-wait_network_online"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
