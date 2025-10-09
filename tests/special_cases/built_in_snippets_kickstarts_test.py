"""
Test module for verifying built-in kickstart snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_keep_rhn_keys(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_rhn_keys snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "## this snippet should NOT be used with systems subscribed",
        "## to Red Hat Satellite Server or Spacewalk as these",
        '## have a concept of "reactivation keys" to keep the systems',
        "## appearing to be the same.  Also do not use if changing",
        "## base channels, i.e. RHEL4 -> RHEL5 upgrades.",
        "",
        'echo "Saving RHN keys..." > /dev/ttyS0',
        "",
        "rhn_keys_found=no",
        "",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "",
        "mkdir -p /tmp/rhn",
        "",
        "drives=$(list-harddrives | awk '{print $1}')",
        "for disk in $drives; do",
        "    DISKS=\"$DISKS $(fdisk -l /dev/$disk | awk '/^\\/dev/{print $1}')\"",
        "done",
        "",
        "# Try to find the keys on ordinary partitions",
        "for disk in $DISKS; do",
        "    name=$(basename $disk)",
        "    mkdir -p /tmp/$name",
        "    mount $disk /tmp/$name",
        "    [ $? -eq 0 ] || continue # Skip to the next partition if the mount fails",
        "",
        "    # Copy current RHN host keys out to be reused",
        "    if [ -d /tmp/${name}/etc/sysconfig/rhn ]; then",
        "        cp -a /tmp/${name}/etc/sysconfig/rhn/install-num /tmp/rhn",
        "        cp -a /tmp/${name}/etc/sysconfig/rhn/systemid /tmp/rhn",
        "        cp -a /tmp/${name}/etc/sysconfig/rhn/up2date /tmp/rhn",
        '        rhn_keys_found="yes"',
        "        umount /tmp/$name",
        "        break",
        "    fi",
        "    umount /tmp/$name",
        "    rm -r /tmp/$name",
        "done",
        "",
        "# Try LVM if that didn't work",
        'if [ "$rhn_keys_found" = "no" ]; then',
        "    lvm lvmdiskscan",
        "    vgs=$(lvm vgs | tail -n +2 | awk '{ print $1 }')",
        "    for vg in $vgs; do",
        "        # Activate any VG we found",
        "        lvm vgchange -ay $vg",
        "    done",
        "    ",
        '    lvs=$(lvm lvs | tail -n +2 | awk \'{ print "/dev/" $2 "/" $1 }\')',
        "    for lv in $lvs; do",
        "        tmpdir=$(mktemp -d findkeys.XXXXXX)",
        "        mkdir -p /tmp/${tmpdir}",
        "        mount $lv /tmp/${tmpdir} || continue # Skip to next volume if this fails",
        "",
        "        # Let's see if the keys are in there",
        "        if [ -d /tmp/${tmpdir}/etc/sysconfig/rhn ]; then",
        "            cp -a /tmp/${tmpdir}/etc/sysconfig/rhn/install-num* /tmp/rhn/",
        "            cp -a /tmp/${tmpdir}/etc/sysconfig/rhn/systemid* /tmp/rhn/",
        "            cp -a /tmp/${tmpdir}/etc/sysconfig/rhn/up2date /tmp/rhn/",
        '            rhn_keys_found="yes"',
        "            umount /tmp/${tmpdir}",
        "            break # We're done!",
        "        fi",
        "        umount /tmp/${tmpdir}",
        "        rm -r /tmp/${tmpdir}",
        "    done",
        "    ",
        "    # And clean up..",
        "    for vg in $vgs; do",
        "        lvm vgchange -an $vg",
        "    done",
        "fi",
        "",
        "# Loop until the RHN rpm is installed",
        'if [ "$rhn_keys_found" = "yes" ]; then',
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage/etc/sysconfig/rhn ] ; then",
        "            cp -af /tmp/rhn/* /mnt/sysimage/etc/sysconfig/rhn/",
        '            logger "RHN KEY copied to newly installed system"',
        "            break",
        "        fi",
        "    done &",
        "fi",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_rhn_keys"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_log_ks_post_nochroot(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in log_ks_post_nochroot snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "set -x -v",
        "exec 1>/mnt/sysimage/root/ks-post-nochroot.log 2>&1",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-log_ks_post_nochroot"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_log_ks_post(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in log_ks_post snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "set -x -v",
        "exec 1>/root/ks-post.log 2>&1",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-log_ks_post"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_log_ks_pre(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in log_ks_pre snippet.
    """
    # Arrange
    expected_result: List[str] = [
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
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-log_ks_pre"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_post_anamon(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in post_anamon snippet.
    """
    # Arrange
    expected_result: List[str] = [
        'curl -o /usr/local/sbin/anamon "http://example.org:80/cobbler/misc/anamon"',
        'curl -o /etc/rc.d/init.d/anamon "http://example.org:80/cobbler/misc/anamon.init"',
        "",
        "chmod 755 /etc/rc.d/init.d/anamon /usr/local/sbin/anamon",
        "test -d /selinux && restorecon /etc/rc.d/init.d/anamon /usr/local/sbin/anamon",
        "",
        "chkconfig --add anamon",
        "",
        "cat << __EOT__ > /etc/sysconfig/anamon",
        'COBBLER_SERVER="example.org"',
        'COBBLER_PORT="80"',
        'COBBLER_NAME="testobject"',
        'LOGFILES="/var/log/boot.log /var/log/messages /var/log/dmesg /root/ks-post.log"',
        "__EOT__",
        "",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-post_anamon"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "anamon_enabled": True,
        "server": "example.org",
        "http_port": "80",
        "name": "testobject",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_pre_anamon(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in pre_anamon snippet.
    """
    # Arrange
    expected_result: List[str] = [
        'curl -o /tmp/anamon "http://example.org:80/cobbler/misc/anamon"',
        "python=python",
        "[ -x /usr/libexec/platform-python ] && python=/usr/libexec/platform-python",
        "[ -x /usr/bin/python3 ] && python=/usr/bin/python3",
        '$python /tmp/anamon --name "testobject" --server "example.org" --port "80"',
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_anamon"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "anamon_enabled": True,
        "server": "example.org",
        "http_port": "80",
        "name": "testobject",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
