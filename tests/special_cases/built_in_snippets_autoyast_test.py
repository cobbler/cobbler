"""
Test module for built-in AutoYaST snippets in Cobbler.
"""

from typing import Any, Dict

import pytest

from cobbler.api import CobblerAPI


def test_built_in_autoyast_addons_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST addons XML snippet.
    """
    # Arrange
    expected_result = [
        "<add-on>",
        '    <add_on_products config:type="list">',
        "    </add_on_products>",
        "  </add-on>",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-addons.xml"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"repos": []}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_hosts_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST hosts XML snippet.
    """
    # Arrange
    expected_result = [
        "<host>",
        '    <hosts config:type="list">',
        "      <hosts_entry>",
        "        <host_address>127.0.0.1</host_address>",
        '        <names config:type="list">',
        "          <name>localhost</name>",
        "        </names>",
        "      </hosts_entry>",
        "    </hosts>",
        "  </host>",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-hosts.xml")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_kdump_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST kdump XML snippet.
    """
    # Arrange
    expected_result = [
        "<kdump>",
        "    <!-- memory reservation -->",
        "    <!-- reserve 64 MB with 256MB to 2GB Memory and 128MB with more then 2GB Memory -->",
        '    <add_crash_kernel config:type="boolean">true</add_crash_kernel>',
        "    <crash_kernel>256M-2G:64M,2G-:128M</crash_kernel>",
        "  ",
        "    <general>",
        "      <!-- dump target settings -->",
        "      <KDUMP_SAVEDIR>file:///var/crash</KDUMP_SAVEDIR>",
        "      <KDUMP_COPY_KERNEL>true</KDUMP_COPY_KERNEL>",
        "      <KDUMP_FREE_DISK_SIZE>64</KDUMP_FREE_DISK_SIZE>",
        "      <KDUMP_KEEP_OLD_DUMPS>4</KDUMP_KEEP_OLD_DUMPS>",
        "  ",
        "      <!-- filtering and compression -->",
        "      <KDUMP_DUMPFORMAT>compressed</KDUMP_DUMPFORMAT>",
        "      <KDUMP_DUMPLEVEL>31</KDUMP_DUMPLEVEL>",
        "  ",
        "      <!-- notification -->",
        "      <KDUMP_NOTIFICATION_TO></KDUMP_NOTIFICATION_TO>",
        "      <KDUMP_NOTIFICATION_CC></KDUMP_NOTIFICATION_CC>",
        "      <KDUMP_SMTP_SERVER></KDUMP_SMTP_SERVER>",
        "      <KDUMP_SMTP_USER></KDUMP_SMTP_USER>",
        "      <KDUMP_SMTP_PASSWORD></KDUMP_SMTP_PASSWORD>",
        "  ",
        "      <!-- kdump kernel -->",
        "      <KDUMP_KERNELVER></KDUMP_KERNELVER>",
        "      <KDUMP_COMMANDLINE></KDUMP_COMMANDLINE>",
        "      <KDUMP_COMMANDLINE_APPEND></KDUMP_COMMANDLINE_APPEND>",
        "  ",
        "      <!-- expert settings -->",
        "      <KDUMP_IMMEDIATE_REBOOT>yes</KDUMP_IMMEDIATE_REBOOT>",
        "      <KDUMP_VERBOSE>3</KDUMP_VERBOSE>",
        "      <KEXEC_OPTIONS></KEXEC_OPTIONS>",
        "    </general>",
        "  </kdump> ",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-kdump.xml")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_networking_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST networking XML snippet.
    """
    # Arrange
    expected_result = [
        "<networking>",
        '    <keep_install_network config:type="boolean">false</keep_install_network>',
        "    <dhcp_options>",
        "      <dhclient_client_id></dhclient_client_id>",
        "      <dhclient_hostname_option></dhclient_hostname_option>",
        "    </dhcp_options>",
        "    <dns>",
        '      <dhcp_hostname config:type="boolean">false</dhcp_hostname>',
        '      <dhcp_resolv config:type="boolean">false</dhcp_resolv>',
        '      <write_hostname config:type="boolean">false</write_hostname>',
        "      <resolv_conf_policy></resolv_conf_policy>",
        "      <hostname>cobbler</hostname>",
        "      <domain>site</domain>",
        '      <nameservers config:type="list">',
        "      </nameservers>",
        "    </dns>",
        '    <interfaces config:type="list">',
        "    </interfaces>",
        '    <managed config:type="boolean">false</managed>',
        '    <net-udev config:type="list">',
        "    </net-udev>",
        "    <routing>",
        '      <ip_forward config:type="boolean">false</ip_forward>',
        "    </routing>",
        "  </networking>",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-networking.xml"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"dns": {"name_servers": []}}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_proxy_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in AutoYaST proxy XML snippet.
    """
    # Arrange
    expected_result = [
        "<proxy>",
        '  <enabled config:type="boolean">true</enabled>',
        "  <ftp_proxy></ftp_proxy>",
        "  <http_proxy></http_proxy>",
        "  <https_proxy></https_proxy>",
        "  <no_proxy>localhost, 127.0.0.1</no_proxy>",
        "  <proxy_password></proxy_password>",
        "  <proxy_user></proxy_user>",
        "</proxy>",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-proxy.xml")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"proxy": ""}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_suse_scriptwrapper_xml(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in SUSE script wrapper XML snippet.
    """
    # Arrange
    expected_result = [
        "<script>",
        '        <network_needed config:type="boolean">true</network_needed>',
        "        <interpreter>shell</interpreter>",
        "        <filename>built-in-save_boot_device</filename>",
        "        <source><![CDATA[",
        "",
        "        ]]></source>",
        "      </script>",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-suse_scriptwrapper.xml"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "wrappedscript": "built-in-save_boot_device",
        "arch": "x86_64",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
