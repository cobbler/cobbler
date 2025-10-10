"""
Test module to extensively verify the built-in Kickstart Templates.
"""

from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.manager import AutoInstallationManager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_default_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in default kickstart template.
    """
    # Arrange
    expected_result = [
        "# this file intentionally left blank",
        "# admins:  edit it as you like, or leave it blank for non-interactive install",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-default.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert isinstance(result, str)
    assert result == "\n".join(expected_result)


def test_built_in_legacy_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in legacy kickstart template.
    """
    # Arrange
    expected_result = [
        "#platform=x86, AMD64, or Intel EM64T",
        "# System authorization information",
        "auth  --useshadow  --enablemd5",
        "# System bootloader configuration",
        "bootloader --location=mbr",
        "# Partition clearing information",
        "clearpart --all --initlabel",
        "# Use text mode install",
        "text",
        "# Firewall configuration",
        "firewall --enabled",
        "# Run the Setup Agent on first boot",
        "firstboot --disable",
        "# System keyboard",
        "keyboard us",
        "# System language",
        "lang en_US",
        "# Use network installation",
        "url --url=$tree",
        "# Network information",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "# Reboot after installation",
        "reboot",
        "",
        "#Root password",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "# SELinux configuration",
        "selinux --disabled",
        "# Do not configure the X Window System",
        "skipx",
        "# System timezone",
        "timezone  America/New_York",
        "# Install OS instead of upgrade",
        "install",
        "# Clear the Master Boot Record",
        "zerombr",
        "# Allow anaconda to partition the system as needed",
        "autopart",
        "",
        "%pre",
        "set -x -v",
        "exec 1>/tmp/ks-pre.log 2>&1",
        "",
        "# Once root's homedir is there, copy over the log.",
        "while : ; do",
        "    sleep 10",
        "    if [ -d /mnt/sysimage/root ]; then",
        "        cp /tmp/ks-pre.log /mnt/sysimage/root/",
        '        logger "Copied %pre section log to system"',
        "        break",
        "    fi",
        "done &",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_legacy_ks" -O /dev/null',
        "",
        "",
        "",
        "%packages",
        "",
        "%post --nochroot",
        "set -x -v",
        "exec 1>/mnt/sysimage/root/ks-post-nochroot.log 2>&1",
        "",
        "%end",
        "",
        "%post",
        "set -x -v",
        "exec 1>/root/ks-post.log 2>&1",
        "",
        "# Begin yum configuration",
        "$yum_config_stanza",
        "# End yum configuration",
        "",
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
        "# Start download cobbler managed config files (if applicable)",
        "# End download cobbler managed config files (if applicable)",
        "",
        "# Start koan environment setup",
        'echo "export COBBLER_SERVER=192.168.1.1" > /etc/profile.d/cobbler.sh',
        'echo "setenv COBBLER_SERVER 192.168.1.1" > /etc/profile.d/cobbler.csh',
        "# End koan environment setup",
        "",
        "# begin Red Hat management server registration",
        "# not configured to register to any Red Hat management server (ok)",
        "# end Red Hat management server registration",
        "",
        "# Begin cobbler registration",
        "# cobbler registration is disabled in /etc/cobbler/settings.yaml",
        "# End cobbler registration",
        "",
        "# Begin final steps",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_legacy_ks" -O /dev/null',
        "# End final steps",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-legacy.ks")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert isinstance(result, str)
    assert result == "\n".join(expected_result)


def test_built_in_powerkvm_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in powerkvm kickstart template.
    """
    # Arrange
    expected_result = [
        "# kickstart template for PowerKVM 2.1 and later",
        "",
        "# Root password",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "# System timezone",
        "timezone  America/Chicago",
        "# Allow anaconda to partition the system as needed",
        "partition / --ondisk=/dev/sda",
        "# network specification is also supported, but if we specify the network",
        "# device on the command-line, we can skip it",
        "",
        "%pre",
        "set -x -v",
        "exec 1>/tmp/ks-pre.log 2>&1",
        "",
        "# Once root's homedir is there, copy over the log.",
        "while : ; do",
        "    sleep 10",
        "    if [ -d /mnt/sysimage/root ]; then",
        "        cp /tmp/ks-pre.log /mnt/sysimage/root/",
        '        logger "Copied %pre section log to system"',
        "        break",
        "    fi",
        "done &",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_powerkvm_ks" -O /dev/null',
        "%end",
        "",
        "%post",
        "set -x -v",
        "exec 1>/root/ks-post.log 2>&1",
        "",
        "# Start yum configuration",
        "$yum_config_stanza",
        "# End yum configuration",
        "",
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
        "# Start final steps",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_powerkvm_ks" -O /dev/null',
        "# End final steps",
        "%end",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-powerkvm.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_pxerescue_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in pxerescue kickstart template.
    """
    # Arrange
    expected_result = [
        "# Rescue Boot Template",
        "",
        "# Set the language and language support",
        "lang en_US",
        "# uncomment for legacy system (e.g. RHEL4)",
        "# langsupport en_US",
        "",
        "# Set the keyboard",
        'keyboard "us"',
        "",
        "# Network kickstart",
        "network --bootproto dhcp",
        "",
        "# Rescue method (only NFS/FTP/HTTP currently supported)",
        "url --url=$tree",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pxerescue.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_esxi4_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample esxi4 kickstart template.
    """
    # Arrange
    expected_result = [
        "# sample Kickstart for ESXi",
        "",
        "install url $tree",
        "",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "",
        "accepteula",
        "reboot",
        "",
        "autopart --firstdisk --overwritevmfs",
        " ",
        "",
        "",
        "",
        "%pre --unsupported --interpreter=busybox",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_esxi4_ks" -O /dev/null',
        "",
        "%post --unsupported --interpreter=busybox",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_esxi4_ks" -O /dev/null',
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_esxi4.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_esxi5_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample esxi5 kickstart template.
    """
    # Arrange
    expected_result = [
        "# Sample scripted installation file",
        "# for ESXi 5+",
        "",
        "vmaccepteula",
        "reboot --noeject",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "",
        "install --firstdisk --overwritevmfs",
        "clearpart --firstdisk --overwritevmfs",
        "",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "",
        "%pre --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_esxi5_ks" -O /dev/null',
        "",
        "",
        "%post --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_esxi5_ks" -O /dev/null',
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_esxi5.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_esxi6_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample esxi6 kickstart template.
    """
    # Arrange
    expected_result = [
        "# Sample scripted installation file",
        "# for ESXi 6+",
        "",
        "vmaccepteula",
        "reboot --noeject",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "",
        "install --firstdisk --overwritevmfs",
        "clearpart --firstdisk --overwritevmfs",
        "",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "",
        "%pre --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_esxi6_ks" -O /dev/null',
        "",
        "",
        "%post --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_esxi6_ks" -O /dev/null',
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_esxi6.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_esxi7_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample esxi7 kickstart template.
    """
    # Arrange
    expected_result = [
        "# Sample scripted installation file",
        "# for ESXi 7+",
        "",
        "vmaccepteula",
        "reboot --noeject",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "",
        "install --firstdisk --overwritevmfs",
        "clearpart --firstdisk --overwritevmfs",
        "",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "",
        "%pre --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_esxi7_ks" -O /dev/null',
        "",
        "",
        "%post --interpreter=busybox",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_esxi7_ks" -O /dev/null',
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_esxi7.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_legacy_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample legacy kickstart template.
    """
    # Arrange
    expected_result = [
        "# This kickstart file can be used on RHEL 4, 5 and Fedora < 8",
        "# Don't use this on current distributions!",
        "",
        "#platform=x86, AMD64, or Intel EM64T",
        "# System authorization information",
        "auth  --useshadow  --enablemd5",
        "# System bootloader configuration",
        "bootloader --location=mbr",
        "# Partition clearing information",
        "clearpart --all --initlabel",
        "# Use text mode install",
        "text",
        "# Firewall configuration",
        "firewall --enabled",
        "# Run the Setup Agent on first boot",
        "firstboot --disable",
        "# System keyboard",
        "keyboard us",
        "# System language",
        "lang en_US",
        "# Use network installation",
        "url --url=$tree",
        "# If any cobbler repo definitions were referenced in the kickstart profile, include them here.",
        "$yum_repo_stanza",
        "# Network information",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "# Reboot after installation",
        "reboot",
        "",
        "#Root password",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "# SELinux configuration",
        "selinux --disabled",
        "# Do not configure the X Window System",
        "skipx",
        "# System timezone",
        "timezone  America/New_York",
        "# Install OS instead of upgrade",
        "install",
        "# Clear the Master Boot Record",
        "zerombr",
        "# Allow anaconda to partition the system as needed",
        "autopart",
        "",
        "",
        "%pre",
        "set -x -v",
        "exec 1>/tmp/ks-pre.log 2>&1",
        "",
        "# Once root's homedir is there, copy over the log.",
        "while : ; do",
        "    sleep 10",
        "    if [ -d /mnt/sysimage/root ]; then",
        "        cp /tmp/ks-pre.log /mnt/sysimage/root/",
        '        logger "Copied %pre section log to system"',
        "        break",
        "    fi",
        "done &",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_legacy_ks" -O /dev/null',
        "",
        "# Enable installation monitoring",
        "",
        "%end",
        "",
        "%packages",
        "",
        "%end",
        "",
        "%post --nochroot",
        "set -x -v",
        "exec 1>/mnt/sysimage/root/ks-post-nochroot.log 2>&1",
        "",
        "%end",
        "",
        "%post",
        "set -x -v",
        "exec 1>/root/ks-post.log 2>&1",
        "",
        "# Start yum configuration ",
        "$yum_config_stanza",
        "# End yum configuration",
        "",
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
        "# start puppet registration ",
        "# end puppet registration",
        "",
        "# Start download cobbler managed config files (if applicable)",
        "# End download cobbler managed config files (if applicable)",
        "",
        "# Start koan environment setup",
        'echo "export COBBLER_SERVER=192.168.1.1" > /etc/profile.d/cobbler.sh',
        'echo "setenv COBBLER_SERVER 192.168.1.1" > /etc/profile.d/cobbler.csh',
        "# End koan environment setup",
        "",
        "# begin Red Hat management server registration",
        "# not configured to register to any Red Hat management server (ok)",
        "# end Red Hat management server registration",
        "",
        "# Begin cobbler registration",
        "# cobbler registration is disabled in /etc/cobbler/settings.yaml",
        "# End cobbler registration",
        "",
        "# Enable post-install boot notification",
        "",
        "# Start final steps",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_legacy_ks" -O /dev/null',
        "# End final steps",
        "%end",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-sample_legacy.ks"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_sample_ks(
    cobbler_api: CobblerAPI,
    autoinstall_manager: AutoInstallationManager,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in sample kickstart template.
    """
    # Arrange
    expected_result = [
        "# Sample kickstart file for current EL, Fedora based distributions.",
        "",
        "#platform=x86, AMD64, or Intel EM64T",
        "# System authorization information",
        "authselect --useshadow --passalgo=SHA512 --kickstart",
        "# Get install destination disk (default sda)",
        "# System bootloader configuration",
        "# bootloader--location=mbr --boot-drive=sda",
        "# Partition clearing information",
        "clearpart --all --initlabel",
        "ignoredisk --only-use=sda",
        "# Use text mode install",
        "text",
        "# Firewall configuration",
        "firewall --enabled",
        "# Run the Setup Agent on first boot",
        "firstboot --disable",
        "# System keyboard",
        "keyboard us",
        "# System language",
        "lang en_US",
        "# Use network installation",
        "url --url=$tree",
        "# If any cobbler repo definitions were referenced in the kickstart profile, include them here.",
        "$yum_repo_stanza",
        "# Network information",
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
        "# Reboot after installation",
        "reboot",
        "",
        "#Root password",
        r"rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
        "# SELinux configuration",
        "selinux --disabled",
        "# Do not configure the X Window System",
        "skipx",
        "# System timezone",
        "timezone  America/New_York",
        "# Clear the Master Boot Record",
        "zerombr",
        "# Allow anaconda to partition the system as needed",
        "autopart",
        "",
        "%pre",
        "set -x -v",
        "exec 1>/tmp/ks-pre.log 2>&1",
        "",
        "# Once root's homedir is there, copy over the log.",
        "while : ; do",
        "    sleep 10",
        "    if [ -d /mnt/sysimage/root ]; then",
        "        cp /tmp/ks-pre.log /mnt/sysimage/root/",
        '        logger "Copied %pre section log to system"',
        "        break",
        "    fi",
        "done &",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_sample_ks" -O /dev/null',
        "",
        "# Enable installation monitoring",
        "",
        "%end",
        "",
        "%packages",
        "%end",
        "",
        "%post --nochroot",
        "set -x -v",
        "exec 1>/mnt/sysimage/root/ks-post-nochroot.log 2>&1",
        "",
        "%end",
        "",
        "%post",
        "set -x -v",
        "exec 1>/root/ks-post.log 2>&1",
        "",
        "# Start yum configuration",
        "$yum_config_stanza",
        "# End yum configuration",
        "",
        "$SNIPPET('built-in-network_disable_interfaces')",
        "# Start download cobbler managed config files (if applicable)",
        "# End download cobbler managed config files (if applicable)",
        "",
        "# Start koan environment setup",
        'echo "export COBBLER_SERVER=192.168.1.1" > /etc/profile.d/cobbler.sh',
        'echo "setenv COBBLER_SERVER 192.168.1.1" > /etc/profile.d/cobbler.csh',
        "# End koan environment setup",
        "",
        "# begin Red Hat management server registration",
        "# not configured to register to any Red Hat management server (ok)",
        "# end Red Hat management server registration",
        "",
        "# Begin cobbler registration",
        "# cobbler registration is disabled in /etc/cobbler/settings.yaml",
        "# End cobbler registration",
        "",
        "# Enable post-install boot notification",
        "",
        "# Start final steps",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_sample_ks" -O /dev/null',
        "# End final steps",
        "%end",
        "",
    ]
    target_template = cobbler_api.find_template(False, False, name="built-in-sample.ks")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall = target_template

    # Act
    result = autoinstall_manager.generate_autoinstall(test_profile, target_template)

    # Assert
    assert result == "\n".join(expected_result)
