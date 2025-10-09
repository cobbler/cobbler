"""
Test module for verifying built-in cfengine snippets in Cobbler.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


def test_built_in_keep_cfengine_keys(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_cfengine_keys snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Nifty trick to restore cfengine keys without using a nochroot %post",
        "# This is deprecated by the generic 'keep_files' script.",
        "",
        'echo "Saving cfengine  keys..." > /dev/ttyS0',
        "",
        "SEARCHDIR=/var/cfengine/ppkeys",
        "TEMPDIR=cfengine",
        "PATTERN=localhost",
        "",
        "keys_found=no",
        "# /var could be a separate partition",
        "SHORTDIR=${SEARCHDIR#/var}",
        "if [ $SHORTDIR = $SEARCHDIR ]; then",
        "  SHORTDIR=''",
        "fi",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "",
        "mkdir -p /tmp/$TEMPDIR",
        "",
        "function findkeys",
        "{",
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
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage$SEARCHDIR ] ; then",
        "            cp -af /tmp/$TEMPDIR/${PATTERN}* /mnt/sysimage$SEARCHDIR",
        '            logger "keys copied to newly installed system"',
        "            break",
        "        fi",
        "    done &",
        "fi",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_cfengine_keys"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_keep_rudder_keys(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_rudder_keys snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Nifty trick to restore cfengine keys without using a nochroot %post",
        "",
        'echo "Saving rudder  keys..." > /dev/ttyS0',
        "",
        "SEARCHDIR=/var/rudder/cfengine-community/ppkeys",
        "TEMPDIR=rudder",
        "PATTERN=localhost",
        "",
        "keys_found=no",
        "# /var could be a separate partition",
        "SHORTDIR=${SEARCHDIR#/var/rudder}",
        "if [ $SHORTDIR = $SEARCHDIR ]; then",
        "    SHORTDIR=''",
        "fi",
        "",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "insmod /lib/ext4.o",
        "insmod /lib/xfs.o",
        "",
        "mkdir -p /tmp/$TEMPDIR",
        "",
        "function findkeys",
        "{",
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
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage$SEARCHDIR ] ; then",
        "            cp -af /tmp/$TEMPDIR/${PATTERN}* /mnt/sysimage$SEARCHDIR",
        '            logger "keys copied to newly installed system"',
        "            break",
        "        fi",
        "    done &",
        "fi",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_rudder_keys"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_keep_rudder_uuid(cobbler_api: CobblerAPI):
    """
    Test to verify the functionality of the built-in keep_rudder_uuid snippet.
    """
    # Arrange
    expected_result: List[str] = [
        "# Nifty trick to restore cfengine keys without using a nochroot %post",
        "",
        'echo "Saving rudder  keys..." > /dev/ttyS0',
        "",
        "SEARCHDIR=/opt/rudder/etc",
        "TEMPDIR=rudderuuid",
        "PATTERN=uuid",
        "",
        "keys_found=no",
        "# /opt could be a separate partition",
        "SHORTDIR=${SEARCHDIR#/opt}",
        "if [ $SHORTDIR = $SEARCHDIR ]; then",
        "    SHORTDIR=''",
        "fi",
        "",
        "insmod /lib/jbd.o",
        "insmod /lib/ext3.o",
        "insmod /lib/ext4.o",
        "insmod /lib/xfs.o",
        "",
        "mkdir -p /tmp/$TEMPDIR",
        "",
        "function findkeys",
        "{",
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
        "    while : ; do",
        "        sleep 10",
        "        if [ -d /mnt/sysimage$SEARCHDIR ] ; then",
        "            cp -af /tmp/$TEMPDIR/${PATTERN}* /mnt/sysimage$SEARCHDIR",
        '            logger "keys copied to newly installed system"',
        "            break",
        "        fi",
        "    done &",
        "fi",
        "",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-keep_rudder_uuid"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert result == "\n".join(expected_result)
