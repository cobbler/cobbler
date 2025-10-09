"""
Test module for verifying built-in generic (aka shell script) snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_autoinstall_done(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in autoinstall_done snippet.
    """
    # Arrange
    expected_result: List[str] = [
        'curl "http://example.org/cblr/svc/op/autoinstall/profile/testprofile" -o /root/cobbler.xml',
        'curl "http://example.org/cblr/svc/op/trig/mode/post/profile/testprofile" -o /dev/null',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinstall_done"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "profile_name": "testprofile",
        "autoinstall": {},
        "breed": "suse",
        "run_install_triggers": True,
        "http_server": "example.org",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_autoinstall_start(cobbler_api: CobblerAPI):
    """
    Test to verfy the functionality of the built-in autoinstall_start snippet.
    """
    # Arrange
    expected_result: List[str] = [
        'wget "http:///cblr/svc/op/trig/mode/pre/profile/testprofile" -O /dev/null'
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinstall_start"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"profile_name": "testprofile", "run_install_triggers": True}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_cobbler_register(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in cobbler_register snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Begin cobbler registration",
        "# cobbler registration is disabled in /etc/cobbler/settings.yaml",
        "# End cobbler registration",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cobbler_register"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_koan_environment(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in koan_environment snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start koan environment setup",
        'echo "export COBBLER_SERVER=$server" > /etc/profile.d/cobbler.sh',
        'echo "setenv COBBLER_SERVER $server" > /etc/profile.d/cobbler.csh',
        "# End koan environment setup",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-koan_environment"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_restore_boot_device(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in restore_boot_device snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Some Linux distributions, such as Fedora 17+, SLES 11+ and RHEL 7+, set the disk",
        "# as first boot device in Power machines. Therefore, restore the original boot",
        "# order.",
        "# we have already chrooted, former /root is available now at /root/inst-sys",
        'boot_order_orig="$(cat /root/inst-sys/boot-device.bak)"',
        'boot_order_cur="$(nvram --print-config=boot-device)"',
        'if [[ ( -n "$boot_order_orig" ) &&  ( "$boot_order_orig" != "$boot_order_cur" ) ]]',
        "then",
        '    nvram --update-config boot-device="$boot_order_orig"',
        "fi",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-restore_boot_device"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"arch": "ppc64le", "breed": "suse"}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_save_boot_device(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in save_boot_device snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Some Linux distributions, such as Fedora 17+, SLES 11+ and RHEL 7+, set the disk",
        "# as first boot device in Power machines. Therefore, save the original boot",
        "# order, so it can be restored after installation is completed.",
        "nvram --print-config=boot-device > /root/boot-device.bak",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-save_boot_device"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"arch": "ppc64le", "breed": "suse"}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
