"""
Test module for verifying built-in preseed snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_download_config_files_deb(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in download_config_files_deb snippet.
    """
    # Arrange
    expected_result: List[str] = ["\\"]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-download_config_files_deb"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"template_files": {}}
    cobbler_api.settings().cheetah_import_whitelist.append("os")
    cobbler_api.settings().cheetah_import_whitelist.append("stat")

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_late_apt_repo_config(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in late_apt_repo_config snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# start late_apt_repo_config",
        "cat<<EOF>/etc/apt/sources.list",
        "EOF",
        "# end late_apt_repo_config",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-late_apt_repo_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_install_network_config_deb(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_install_network_config_deb snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_install_network_config_deb"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_run_deb(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_run_deb snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# A general purpose snippet to add late-command actions for preseeds",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_run_deb"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_preseed_apt_repo_config(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in preseed_apt_repo_config snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Additional repositories, local[0-9] available",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-preseed_apt_repo_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
