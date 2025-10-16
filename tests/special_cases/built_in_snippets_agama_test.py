"""
Test module to verify the built-in snippets for Agama.
"""

from typing import Any, Dict

import pytest

from cobbler.api import CobblerAPI


def test_built_in_agama_bootloader(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-bootloader"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""
