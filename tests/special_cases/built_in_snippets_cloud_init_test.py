"""
Test module to verify the built-in snippets for Cloud-Init.
"""

# pylint: disable=too-many-lines

from typing import Any, Dict, List

import pytest
import yaml

from cobbler.api import CobblerAPI


def test_built_in_cloud_init_module_ansible(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ansible"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_apk_repos(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apk-repos"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_apt(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apt"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_apt_pipelining(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apt-pipelining"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_apt_pipelining": True}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "apt_pipelining: True"


def test_built_in_cloud_init_module_bootcmd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "bootcmd:",
        '  - "test1"',
        '  - ["test2", "test3"]',
        '  - "test4"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-bootcmd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_bootcmd": ["test1", ["test2", "test3"], "test4"]
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_byobu_by_default(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-byobu"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_ca_certs": {"remove_defaults": True}},
            ["ca_certs:", "  remove_defaults: true"],
        ),
        (
            {"cloud_init_ca_certs": {"trusted": ["cert1", "cert2"]}},
            ["ca_certs:", "  trusted:", "    - cert1", "    - cert2"],
        ),
        (
            {
                "cloud_init_ca_certs": {
                    "trusted": [
                        "cert1",
                        "-----BEGIN CERTIFICATE-----\nYOUR-ORGS-TRUSTED-CA-CERT-HERE\n-----END CERTIFICATE-----",
                    ]
                }
            },
            [
                "ca_certs:",
                "  trusted:",
                "    - cert1",
                "    - |",
                "      -----BEGIN CERTIFICATE-----",
                "      YOUR-ORGS-TRUSTED-CA-CERT-HERE",
                "      -----END CERTIFICATE-----",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_ca_certs(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ca-certs"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_chef(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-chef"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_disable_ec2_metadata(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-disable-ec2-metadata"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_disable_ec2_metadata": False}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "disable_ec2_metadata: False"


def test_built_in_cloud_init_module_disk_setup(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-disk-setup"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_fan(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "fan:",
        "  config: |",
        "    testline",
        '  config_path: "/etc/network_fan"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-fan"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_fan_config": "testline",
        "cloud_init_fan_config_path": "/etc/network_fan",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_final_message(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "final_message: |",
        "  Testmessage",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-final-message"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_final_message": "Testmessage"}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_growpart(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "growpart:",
        '  mode: "auto"',
        "  devices:",
        '    - "testdevice"',
        "  ignore_growroot_disabled: True",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-growpart"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_growpart_mode": "auto",
        "cloud_init_growpart_devices": ["testdevice"],
        "cloud_init_growpart_ignore_growroot_disabled": True,
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_grub_dpkg(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "grub_dpkg:",
        "  enabled: True",
        '  grub-pc/install_devices: "/dev/sda"',
        "  grub-pc/install_devices_empty: False",
        '  grub-efi/install_devices: "/dev/sda"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-grub-dpkg"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_grub_dpkg_enabled": True,
        "cloud_init_grub_dpkg_bios_device": "/dev/sda",
        "cloud_init_grub_dpkg_devices_bios_empty": False,
        "cloud_init_grub_dpkg_efi_device": "/dev/sda",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_hotplug(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "updates:",
        "  network:",
        "    when:",
        '      - "boot"',
        '      - "hotplug"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-hotplug"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_hotplug_network_when": ["boot", "hotplug"]}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_keyboard(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "keyboard:",
        '  layout: "de"',
        '  model: "pc105"',
        '  variant: "nodeadkeys"',
        '  options: "compose:rwin"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-keyboard"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_keyboard_layout": "de",
        "cloud_init_keyboard_model": "pc105",
        "cloud_init_keyboard_variant": "nodeadkeys",
        "cloud_init_keyboard_options": "compose:rwin",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_keys_to_console(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-keys-to-console"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_landscape(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init landscape snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-landscape"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_locale(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init locale snippet.
    """
    # Arrange
    expected_result = ['locale: "test1"', 'locale_configfile: "test2"']
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-locale"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_locale_locale": "test1",
        "cloud_init_locale_configfile": "test2",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_lxd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init lxd snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-lxd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_mcollective(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init mcollective snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-mcollective"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_mounts(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init mounts snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-mounts"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_network_v1(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init network v1 snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-network v1"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_network_v2(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init network v2 snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-network v2"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ntp(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init ntp snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ntp"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_packages(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-packages"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_phone_home(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init phone home snippet.
    """
    # Arrange
    expected_result = [
        "phone_home:",
        '  url: "https://example.org"',
        '  post: "all"',
        "  tries: 0",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-phone-home"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_phone_home_url": "https://example.org",
        "cloud_init_phone_home_post": "all",
        "cloud_init_phone_home_tries": 0,
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_power_state_change(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init power state change snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-power-state-change"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_puppet(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-puppet"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_redhat_subscription(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init RedHat subscription snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-redhat-subscription"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_resizefs(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init resizefs snippet.
    """
    # Arrange
    expected_result = "resize_rootfs: True"
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-resizefs"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_resizefs": True}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == expected_result


def test_built_in_cloud_init_module_resolveconf(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init resolveconf snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-resolveconf"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_rpi(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Raspberry Pi snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-rpi"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_rsyslog(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init rsyslog snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-rsyslog"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_runcmd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init runcmd snippet.
    """
    # Arrange
    expected_result = [
        "runcmd:",
        '  - ["ls", "-l"]',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-runcmd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_runcmd": [["ls", "-l"]]}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_salt_minion(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Salt Minion snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-salt-minion"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""



def test_built_in_cloud_init_module_seed_random(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init seed random snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-seed-random"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_set_hostname": {}}, []),
        (
            {"cloud_init_set_hostname": {"preserve_hostname": True}},
            ["preserve_hostname: true"],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "hostname": "example-host",
                }
            },
            ["preserve_hostname: true", 'hostname: "example-host"'],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "hostname": "example-host",
                    "fqdn": "example.org",
                }
            },
            [
                "preserve_hostname: true",
                'hostname: "example-host"',
                'fqdn: "example.org"',
            ],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "create_hostname_file": True,
                }
            },
            ["preserve_hostname: true", "create_hostname_file: true"],
        ),
    ],
)
def test_built_in_cloud_init_module_set_hostname(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init set hostname snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-set-hostname"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_set_passwords": {"ssh_pwauth": False}}, ["ssh_pwauth: false"]),
        ({"cloud_init_set_passwords": {"ssh_pwauth": True}}, ["ssh_pwauth: true"]),
        (
            {
                "cloud_init_set_passwords": {
                    "ssh_pwauth": True,
                    "chpasswd": {"expire": False},
                }
            },
            ["ssh_pwauth: true", "chpasswd:", "  expire: false"],
        ),
        (
            {
                "cloud_init_set_passwords": {
                    "ssh_pwauth": True,
                    "chpasswd": {
                        "expire": False,
                        "users": [{"name": "SchoolGuy", "type": "RANDOM"}],
                    },
                }
            },
            [
                "ssh_pwauth: true",
                "chpasswd:",
                "  expire: false",
                "  users:",
                '  - name: "SchoolGuy"',
                '    type: "RANDOM"',
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_set_passwords(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init set passwords snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-set-passwords"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    print(result)
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_snap(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init snap snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-snap"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_spacewalk(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Spacewalk snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-spacewalk"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh_authkey_fingerprints(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH authkey fingerprints snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh-authkey-fingerprints"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh_import_id(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH import ID snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh-import-id"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_timezone(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init timezone snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-timezone"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ubuntu_autoinstall(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu autoinstall snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-autoinstall"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ubuntu_drivers(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu drivers snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-drivers"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ubuntu_pro(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu Pro snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-pro"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_update_etc_hosts(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init update /etc/hosts snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-update-etc-hosts"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_update_hostname(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init update hostname snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-update-hostname"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_user_and_groups(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init user and groups snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-user-and-groups"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_wireguard(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Wireguard snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-wireguard"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_write_files(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init write files snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-write-files"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_yum_add_repo(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init YUM add repo snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-yum-add-repo"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_zypper": {"config": {"download.use_deltarpm": True}}},
            ["zypper:", "  config:", "    download.use_deltarpm: true"],
        ),
        (
            {
                "cloud_init_zypper": {
                    "config": {
                        "download.use_deltarpm": True,
                        "reposdir": "/etc/zypp/repos.dir",
                        "servicesdir": "/etc/zypp/services.d",
                    }
                }
            },
            [
                "zypper:",
                "  config:",
                "    download.use_deltarpm: true",
                "    reposdir: /etc/zypp/repos.dir",
                "    servicesdir: /etc/zypp/services.d",
            ],
        ),
        (
            {
                "cloud_init_zypper": {
                    "config": {"download.use_deltarpm": True},
                    "repos": [
                        {
                            "autorefresh": 1,
                            "baseurl": "http://dl.opensuse.org/dist/leap/v/repo/oss/",
                            "enabled": 1,
                            "id": "opensuse-oss",
                            "name": "os-oss",
                        }
                    ],
                }
            },
            [
                "zypper:",
                "  repos:",
                "    - autorefresh: 1",
                "      baseurl: http://dl.opensuse.org/dist/leap/v/repo/oss/",
                "      enabled: 1",
                "      id: opensuse-oss",
                "      name: os-oss",
                "  config:",
                "    download.use_deltarpm: true",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_zypper_add_repo(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init zypper add repo snippet.
    """
    # Arrange
    # Data validation must happen before data is handed to Jinja.
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-zypper-add-repo"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)
