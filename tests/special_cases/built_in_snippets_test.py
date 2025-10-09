"""
Test module for verifying built-in snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_download_config_files(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in download_config_files snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start download cobbler managed config files (if applicable)",
        "# End download cobbler managed config files (if applicable)",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-download_config_files"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"template_files": {}}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_keep_files(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_files snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# # # Keep Files (Preserve files during re-build)",
        "",
        "# Allow you to set attributes in the KS-file before calling this snippet.",
        "# Example: ",
        "# Passed external args has precedence.",
        "",
        "   preserve_files=ssh",
        "",
        "# Nifty trick to restore keys without using a nochroot %post",
        "",
        'echo "Saving keys..." > /dev/ttyS0',
        "",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "",
        "function findkeys",
        "{",
        " local disk",
        " local name",
        " local tmpdir",
        " for disk in $DISKS; do",
        "    name=$(basename $disk)",
        "    tmpdir=$(mktemp -d $name.XXXXXX)",
        "    mkdir -p /tmp/$tmpdir",
        "    mount $disk /tmp/$tmpdir",
        "    if [ $? -ne 0 ]; then # Skip to the next partition if the mount fails",
        "      rm -rf /tmp/$tmpdir",
        "      continue",
        "    fi",
        "    # Copy current host keys out to be reused",
        "    if [ -d /tmp/$tmpdir$SEARCHDIR ] && cp -a /tmp/$tmpdir$SEARCHDIR/${PATTERN}* /tmp/$TEMPDIR; then",
        '      keys_found="yes"',
        "      umount /tmp/$tmpdir",
        "      rm -r /tmp/$tmpdir",
        "      break",
        '    elif [ -n "$SHORTDIR" ] && [ -d /tmp/$tmpdir$SHORTDIR ] && cp -a /tmp/$tmpdir$SHORTDIR/${PATTERN}* /tmp/$TEMPDIR; then',
        '      keys_found="yes"',
        "      umount /tmp/$tmpdir",
        "      rm -r /tmp/$tmpdir",
        "      break",
        "    fi",
        "    umount /tmp/$tmpdir",
        "    rm -r /tmp/$tmpdir",
        " done",
        "}",
        "",
        "function search_for_keys",
        "{",
        "",
        " SEARCHDIR=$1",
        " TEMPDIR=$2",
        " PATTERN=$3",
        "",
        " keys_found=no",
        " # /var could be a separate partition",
        " SHORTDIR=${SEARCHDIR#/var}",
        " if [ $SHORTDIR = $SEARCHDIR ]; then",
        "  SHORTDIR=''",
        " fi",
        "",
        " mkdir -p /tmp/$TEMPDIR",
        "",
        ' DISKS=$(awk \'{if ($NF ~ "^[a-zA-Z].*[0-9]$" && $NF !~ "c[0-9]+d[0-9]+$" && $NF !~ "^loop.*") print "/dev/"$NF}\'  /proc/partitions)',
        " # In the awk line above we want to make list of partitions, but not devices/controllers",
        " # cciss raid controllers have partitions like /dev/cciss/cNdMpL, where N,M,L - some digits, we want to make sure 'pL' is there",
        " # No need to scan loopback neither.",
        " # Try to find the keys on ordinary partitions",
        "",
        " findkeys",
        "",
        " # Try software RAID",
        ' if [ "$keys_found" = "no" ]; then',
        "  if mdadm -As; then",
        "      DISKS=$(awk '/md/{print \"/dev/\"$1}' /proc/mdstat)",
        "      findkeys",
        "  fi",
        " fi",
        "",
        "",
        " # Try LVM if that didn't work",
        " local vgs",
        " local vg",
        ' if [ "$keys_found" = "no" ]; then',
        "    lvm lvmdiskscan",
        "    vgs=$(lvm vgs | tail -n +2 | awk '{ print $1 }')",
        "    for vg in $vgs; do",
        "        # Activate any VG we found",
        "        lvm vgchange -ay $vg",
        "    done",
        "",
        '    DISKS=$(lvm lvs | tail -n +2 | awk \'{ print "/dev/" $2 "/" $1 }\')',
        "    findkeys",
        "",
        "    # And clean up..",
        "    for vg in $vgs; do",
        "        lvm vgchange -an $vg",
        "    done",
        " fi",
        "}",
        "",
        "function fix_ssh_key_groups",
        "{",
        " # CentOS 7 has the ssh key-files owned by the group: ssh_keys",
        " # On CentOS 7.4 this results in that the group id may change from the",
        " # Squash-image and when it boots up from the system drive.",
        " # If it's not corrected - SSHD will not start.",
        " # We can't be sure that the existing Group is correct either - assume ssh_keys if group exists.",
        "",
        " local gid_ssh_keys",
        " local re_number",
        " if ls /mnt/sysimage/etc/ssh/ssh_host*key > /dev/null; then",
        '    echo "We have ssh_host -keys to check"',
        "    gid_ssh_keys=$(grep ssh_keys /mnt/sysimage/etc/group | cut -d ':'  -f 3)",
        "    re_number='^[0-9]+$'",
        "    if [[ $gid_ssh_keys =~ $re_number ]]; then",
        "        # On systems where we don't have a ssh_keys group, this will not be run.",
        '        echo "SSH: ssh_keys has group id: $gid_ssh_keys -> setting that on the key-files."',
        "        chown :$gid_ssh_keys /mnt/sysimage/etc/ssh/ssh_host*key",
        "    else",
        '        echo "SSH: ssh_keys -group id not found."',
        "    fi",
        " fi",
        "}",
        "",
        "function restore_keys",
        "{",
        " SEARCHDIR=$1",
        " TEMPDIR=$2",
        " PATTERN=$3",
        " # Loop until the corresponding rpm is installed if the keys are saved",
        ' if [ "$keys_found" = "yes" ] && ls /tmp/${TEMPDIR}/${PATTERN}*; then',
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage${SEARCHDIR} ] ; then",
        "            cp -af /tmp/${TEMPDIR}/${PATTERN}* /mnt/sysimage${SEARCHDIR}",
        '            logger "${TEMPDIR} keys copied to newly installed system"',
        '            if [ "$PATTERN" = "ssh_host_" ]; then',
        "               fix_ssh_key_groups",
        "            fi",
        "            break",
        "        fi",
        "    done &",
        " fi",
        "}",
        "",
        "for key in $preserve_files",
        "do",
        " if [ $key = 'ssh' ]; then",
        "   search_for_keys '/etc/ssh' 'ssh' 'ssh_host_'",
        " elif [ $key = 'cfengine' ]; then",
        "   search_for_keys '/var/cfengine/ppkeys' 'cfengine' 'localhost'",
        " elif [ $key = 'rhn' ]; then",
        "   search_for_keys '/etc/sysconfig/rhn', 'rhn', '*'",
        " elif [ $key = 'puppet' ]; then",
        "   search_for_keys '/etc/puppetlabs/puppet/ssl/certs' 'puppet-certs' '*.pem'",
        "   search_for_keys '/etc/puppetlabs/puppet/ssl/private_keys' 'puppet-keys' '*.pem'",
        " else",
        '   echo "No keys to save!" > /dev/ttyS0',
        " fi",
        "done",
        "",
        "# now restore keys if found",
        "",
        "for key in $preserve_files",
        "do",
        " if [ $key = 'ssh' ]; then",
        "   restore_keys '/etc/ssh' 'ssh' 'ssh_host_'",
        " elif [ $key = 'cfengine' ]; then",
        "   restore_keys '/var/cfengine/ppkeys' 'cfengine' 'localhost'",
        " elif [ $key = 'rhn' ]; then",
        "   restore_keys '/etc/sysconfig/rhn', 'rhn', '*'",
        " elif [ $key = 'puppet' ]; then",
        "   restore_keys '/etc/puppetlabs/puppet/ssl/certs' 'puppet-certs' '*.pem'",
        "   restore_keys '/etc/puppetlabs/puppet/ssl/private_keys' 'puppet-keys' '*.pem'",
        " else",
        '   echo "Nothing to restore!" > /dev/ttyS0',
        " fi",
        "done",
        "",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_files"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_keep_ssh_host_keys(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_ssh_host_keys snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Nifty trick to restore keys without using a nochroot %post",
        "# This is deprecated by the generic 'keep_files' script.",
        "",
        'echo "Saving keys..." > /dev/ttyS0',
        "",
        "SEARCHDIR=/etc/ssh",
        "TEMPDIR=ssh",
        "PATTERN=ssh_host_",
        "",
        "keys_found=no",
        "",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "",
        "mkdir -p /tmp/$TEMPDIR",
        "",
        "",
        "function findkeys",
        "{",
        " for disk in $DISKS; do",
        "    name=$(basename $disk)",
        "    tmpdir=$(mktemp -d $name.XXXXXX)",
        "    mkdir -p /tmp/$tmpdir",
        "    mount $disk /tmp/$tmpdir",
        "    if [ $? -ne 0 ]; then # Skip to the next partition if the mount fails",
        "      rm -rf /tmp/$tmpdir                                                ",
        "      continue                                                           ",
        "    fi                                                                   ",
        "    # Copy current host keys out to be reused",
        "    if [ -d /tmp/$tmpdir$SEARCHDIR ] &&  cp -a /tmp/$tmpdir$SEARCHDIR/${PATTERN}* /tmp/$TEMPDIR; then ",
        '      keys_found="yes"',
        "      umount /tmp/$tmpdir",
        "      rm -r /tmp/$tmpdir",
        "      break",
        "    fi",
        "    umount /tmp/$tmpdir",
        "    rm -r /tmp/$tmpdir",
        " done",
        "}",
        "",
        'DISKS=$(awk \'{if ($NF ~ "^[a-zA-Z].*[0-9]$" && $NF !~ "c[0-9]+d[0-9]+$" && $NF !~ "^loop.*") print "/dev/"$NF}\'  /proc/partitions)',
        "# In the awk line above we want to make list of partitions, but not devices/controllers",
        "# cciss raid controllers have partitions like /dev/cciss/cNdMpL, where N,M,L - some digits, we want to make sure 'pL' is there",
        "# No need to scan loopback niether.",
        "# Try to find the keys on ordinary partitions",
        "",
        "findkeys",
        "",
        "# Try software RAID",
        'if [ "$keys_found" = "no" ]; then',
        "  if mdadm -As; then",
        "      DISKS=$(awk '/md/{print \"/dev/\"$1}' /proc/mdstat)",
        "      findkeys",
        "      # unmount and deactivate all md ",
        "      for md in $DISKS ; do",
        "          umount $md",
        "          mdadm -S $md",
        "      done",
        "  fi",
        "fi",
        "",
        "",
        "# Try LVM if that didn't work",
        'if [ "$keys_found" = "no" ]; then',
        "    lvm lvmdiskscan",
        "    vgs=$(lvm vgs | tail -n +2 | awk '{ print $1 }')",
        "    for vg in $vgs; do",
        "        # Activate any VG we found",
        "        lvm vgchange -ay $vg",
        "    done",
        "    ",
        '    DISKS=$(lvm lvs | tail -n +2 | awk \'{ print "/dev/" $2 "/" $1 }\')',
        "    findkeys    ",
        "",
        "    # And clean up..",
        "    for vg in $vgs; do",
        "        lvm vgchange -an $vg",
        "    done",
        "fi",
        "",
        "# Loop until the corresponding rpm is installed",
        'if [ "$keys_found" = "yes" ]; then',
        '    if [ "$PATTERN" = "ssh_host_" ]; then',
        "        while : ; do",
        "        sleep 10",
        "        if [ -f /etc/ssh/ssh_host_key ] ; then",
        "          cp -af /tmp/$TEMPDIR/${PATTERN}* $SEARCHDIR",
        "          break",
        "        fi",
        "        done 1>/dev/null 2>/dev/null &",
        "    fi",
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage$SEARCHDIR ] ; then",
        "            cp -af /tmp/$TEMPDIR/${PATTERN}* /mnt/sysimage$SEARCHDIR",
        '            if [ -e "/sbin/restorecon"]; then',
        "                /sbin/restorecon -r /etc/ssh",
        "            fi",
        '            logger "keys copied to newly installed system"',
        "            break",
        "        fi",
        "    done 1>/dev/null 2>/dev/null &",
        "fi",
        "",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_ssh_host_keys"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_main_partition_select(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in main_partition_select snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# partition selection",
        "%include /tmp/partinfo",
        "",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-main_partition_select"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_network_config_esxi(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in network_config_esxi snippet.
    """
    # Arrange
    expected_result: List[str] = ["network --bootproto=static --device=default", ""]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-network_config_esxi"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "system_name": "test_name",
        "hostname": "",
        "interfaces": {
            "default": {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "static": True,
                "ip_address": "",
                "netmask": "",
                "interface_type": "",
            }
        },
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_network_config_esx(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in network_config_esx snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "network --bootproto=static --device=aa:bb:cc:dd:ee:ff",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-network_config_esx"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "system_name": "test_name",
        "hostname": "",
        "interfaces": {
            "default": {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "static": True,
                "ip_address": "",
                "netmask": "",
                "interface_type": "",
            }
        },
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_network_config(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in network_config snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "network --bootproto=dhcp --device=eth0 --onboot=on",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_network_disable_interfaces(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in network_disable_interfaces snippet.
    """
    # Arrange
    expected_result: List[str] = [
        'default_mac="aa:bb:cc:dd:ee:ff"',
        "for interface in $(find /sys/class/net -type l -not -lname '*virtual*' -printf '%f\\n'); do",
        '  if ! ip a show "$interface" | grep link/ether | awk \'{print $2}\' |grep -q "$default_mac"; then',
        '    sed -i \'s/ONBOOT=\\("\\)\\?yes\\("\\)\\?/ONBOOT=\\1no\\2/g\' /etc/sysconfig/network-scripts/ifcfg-"$interface"',
        "  fi",
        "done",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-network_disable_interfaces"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "interfaces": {"default": {"mac_address": "aa:bb:cc:dd:ee:ff"}}
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_partition_rhel(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in partition_rhel snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# main partition selection",
        "part /boot/efi --fstype=efi  --size=200",
        "part / --fstype=ext4 --ondisk=sda  --size=1 --grow --fsoptions=defaults --label=root",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-partition_rhel"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_partition_select(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in partition_select snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "%include /tmp/partinfo",
        "",
        "%pre",
        "# Determine how many drives we have",
        "set $(list-harddrives)",
        "let numd=$#/2",
        "d1=$1",
        "d2=$3",
        "",
        "# Determine architecture-specific partitioning needs",
        'EFI_PART=""',
        'PPC_PREP_PART=""',
        'BOOT_PART=""',
        "",
        "case $(uname -m) in",
        "    ppc*)",
        "        PPC_PREP_PART=\"part None --fstype 'PPC PReP Boot' --size 8\"",
        '        BOOT_PART="part /boot --fstype ext3 --size 200 --recommended"',
        "        ;;",
        "    *)",
        '        BOOT_PART="part /boot --fstype ext3 --size 200 --recommended"',
        "        ;;",
        "esac",
        "",
        "cat << EOF > /tmp/partinfo",
        "$EFI_PART",
        "$PPC_PREP_PART",
        "$BOOT_PART",
        "part / --fstype ext3 --size=1024 --grow --ondisk=$d1 --asprimary",
        "part swap --recommended --ondisk=$d1 --asprimary",
        "EOF",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-partition_select"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_install_kernel_options(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_install_kernel_options snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start post install kernel options update",
        "if [ -f /etc/default/grub ]; then",
        '  TMP_GRUB=$(gawk \'match($0,/^GRUB_CMDLINE_LINUX="([^"]+)"/,a) {printf("%s\\n",a[1])}\' /etc/default/grub)',
        "  sed -i '/^GRUB_CMDLINE_LINUX=/d' /etc/default/grub",
        '  echo "GRUB_CMDLINE_LINUX=\\"$TMP_GRUB textmode\\"" >> /etc/default/grub',
        "  grub2-mkconfig -o /boot/grub2/grub.cfg",
        "  if grep -E '/boot/efi (efi|vfat)' /etc/mtab 2>&1 >/dev/null; then",
        "    /bin/cp -f /boot/grub2/grub.cfg /boot/efi/EFI/redhat/grub.cfg",
        "  fi",
        "else",
        '  /sbin/grubby --update-kernel=$(/sbin/grubby --default-kernel) --args="textmode"',
        "  if grep -E '/boot/efi (efi|vfat)' /etc/mtab 2>&1 >/dev/null; then",
        "    /bin/cp -f /boot/grub/grub.conf /boot/efi/EFI/redhat/grub.conf",
        "  fi",
        "fi",
        "# End post install kernel options update",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_install_kernel_options"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "kernel_options_post": "textmode",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_install_network_config(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_install_network_config snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_koan_add_reinstall_entry(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_koan_add_reinstall_entry snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "%post",
        "   koan --server=$server --port=$http_port --replace-self --profile=$profile_name --add-reinstall-entry",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_koan_add_reinstall_entry"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_pre_install_network_config(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in pre_install_network_config snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Start pre_install_network_config generated code",
        "# generic functions to be used later for discovering NICs",
        "mac_exists() {",
        '  [ -z "$1" ] && return 1',
        "",
        "  if which ip 2>/dev/null >/dev/null; then",
        '    ip -o link | grep -i "$1" 2>/dev/null >/dev/null',
        "    return $?",
        "  elif which esxcfg-nics 2>/dev/null >/dev/null; then",
        '    esxcfg-nics -l | grep -i "$1" 2>/dev/null >/dev/null',
        "    return $?",
        "  else",
        '    ifconfig -a | grep -i "$1" 2>/dev/null >/dev/null',
        "    return $?",
        "  fi",
        "}",
        "get_ifname() {",
        "  if which ip 2>/dev/null >/dev/null; then",
        "    IFNAME=$(ip -o link | grep -i \"$1\" | sed -e 's/^[0-9]*: //' -e 's/:.*//')",
        "  elif which esxcfg-nics 2>/dev/null >/dev/null; then",
        '    IFNAME=$(esxcfg-nics -l | grep -i "$1" | cut -d " " -f 1)',
        "  else",
        '    IFNAME=$(ifconfig -a | grep -i "$1" | cut -d " " -f 1)',
        "    if [ -z $IFNAME ]; then",
        "      IFNAME=$(ifconfig -a | grep -i -B 2 \"$1\" | sed -n '/flags/s/:.*$//p')",
        "    fi",
        "  fi",
        "}",
        "",
        "# Start of code to match cobbler system interfaces to physical interfaces by their mac addresses",
        "# End pre_install_network_config generated code",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"system_name": "testsys", "interfaces": {}}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_pre_partition_select(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in pre_partition_select snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# partition details calculation",
        "",
        "# Determine how many drives we have",
        "set $(list-harddrives)",
        "let numd=$#/2",
        "d1=$1",
        "d2=$3",
        "",
        "# Determine architecture-specific partitioning needs",
        'EFI_PART=""',
        'PPC_PREP_PART=""',
        'BOOT_PART=""',
        "",
        "case $(uname -m) in",
        "    ppc*)",
        "        PPC_PREP_PART=\"part None --fstype 'PPC PReP Boot' --size 8\"",
        '        BOOT_PART="part /boot --fstype ext3 --size 200 --recommended"',
        "        ;;",
        "    *)",
        '        BOOT_PART="part /boot --fstype ext3 --size 200 --recommended"',
        "        ;;",
        "esac",
        "",
        "cat << EOF > /tmp/partinfo",
        "$EFI_PART",
        "$PPC_PREP_PART",
        "$BOOT_PART",
        "part / --fstype ext3 --size=1024 --grow --ondisk=$d1 --asprimary",
        "part swap --recommended --ondisk=$d1 --asprimary",
        "EOF",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_partition_select"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_redhat_register(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in redhat_register snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# begin Red Hat management server registration",
        "# not configured to register to any Red Hat management server (ok)",
        "# end Red Hat management server registration",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-redhat_register"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"redhat_management_key": ""}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
