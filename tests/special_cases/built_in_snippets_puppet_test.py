"""
Test module for verifying built-in puppet snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_puppet_install_if_enabled(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in puppet_install_if_enabled snippet.
    """
    # Arrange
    expected_result: List[str] = ["puppet", ""]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-puppet_install_if_enabled"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"puppet_auto_setup": True}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_puppet_register_if_enabled(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in puppet_register_if_enabled snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# start puppet registration ",
        "# end puppet registration",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-puppet_register_if_enabled"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
