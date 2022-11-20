"""
We cache the contents of ``/etc/mtab``. The following module is used to keep our cache in sync.
"""

import os
from typing import Optional

MTAB_MTIME = None
MTAB_MAP = []


class MntEntObj:
    """
    TODO
    """

    mnt_fsname = None  # name of mounted file system
    mnt_dir = None  # file system path prefix
    mnt_type = None  # mount type (see mntent.h)
    mnt_opts = None  # mount options (see mntent.h)
    mnt_freq = 0  # dump frequency in days
    mnt_passno = 0  # pass number on parallel fsck

    def __init__(self, input_data: Optional[str] = None):
        """
        This is an object which contains information about a mounted filesystem.

        :param input_data: This is a string which is separated internally by whitespace. If present it represents the
                      arguments: "mnt_fsname", "mnt_dir", "mnt_type", "mnt_opts", "mnt_freq" and "mnt_passno". The order
                      must be preserved, as well as the separation by whitespace.
        """
        if input_data and isinstance(input_data, str):
            (
                self.mnt_fsname,
                self.mnt_dir,
                self.mnt_type,
                self.mnt_opts,
                self.mnt_freq,
                self.mnt_passno,
            ) = input_data.split()

    def __dict__(self) -> dict:
        """
        This maps all variables available in this class to a dictionary. The name of the keys is identical to the names
        of the variables.

        :return: The dictionary representation of an instance of this class.
        """
        return {
            "mnt_fsname": self.mnt_fsname,
            "mnt_dir": self.mnt_dir,
            "mnt_type": self.mnt_type,
            "mnt_opts": self.mnt_opts,
            "mnt_freq": self.mnt_freq,
            "mnt_passno": self.mnt_passno,
        }

    def __str__(self):
        """
        This is the object representation of a mounted filesystem as a string. It can be fed to the constructor of this
        class.

        :return: The space separated list of values of this object.
        """
        return f"{self.mnt_fsname} {self.mnt_dir} {self.mnt_type} {self.mnt_opts} {self.mnt_freq} {self.mnt_passno}"


def get_mtab(mtab="/etc/mtab", vfstype: bool = False) -> list:
    """
    Get the list of mtab entries. If a custom mtab should be read then the location can be overridden via a parameter.

    :param mtab: The location of the mtab. Argument can be omitted if the mtab is at its default location.
    :param vfstype: If this is True, then all filesystems which are nfs are returned. Otherwise this returns all mtab
                    entries.
    :return: The list of requested mtab entries.
    """
    # These two variables are required to be caches on the module level to be persistent during runtime.
    global MTAB_MTIME, MTAB_MAP  # pylint: disable=global-statement

    mtab_stat = os.stat(mtab)
    if mtab_stat.st_mtime != MTAB_MTIME:
        # cache is stale ... refresh
        MTAB_MTIME = mtab_stat.st_mtime
        MTAB_MAP = __cache_mtab__(mtab)

    # was a specific fstype requested?
    if vfstype:
        mtab_type_map = []
        for ent in MTAB_MAP:
            if ent.mnt_type == "nfs":
                mtab_type_map.append(ent)
        return mtab_type_map

    return MTAB_MAP


def __cache_mtab__(mtab="/etc/mtab"):
    """
    Open the mtab and cache it inside Cobbler. If it is guessed that the mtab hasn't changed the cache data is used.

    :param mtab: The location of the mtab. Argument can be ommited if the mtab is at its default location.
    :return: The mtab content stripped from empty lines (if any are present).
    """
    with open(mtab, encoding="UTF-8") as mtab_fd:
        mtab = [MntEntObj(line) for line in mtab_fd.read().split("\n") if len(line) > 0]

    return mtab


def get_file_device_path(fname):
    """
    What this function attempts to do is take a file and return:
        - the device the file is on
        - the path of the file relative to the device.
    For example:
         /boot/vmlinuz -> (/dev/sda3, /vmlinuz)
         /boot/efi/efi/redhat/elilo.conf -> (/dev/cciss0, /elilo.conf)
         /etc/fstab -> (/dev/sda4, /etc/fstab)

    :param fname: The filename to split up.
    :return: A tuple containing the device and relative filename.
    """

    # resolve any symlinks
    fname = os.path.realpath(fname)

    # convert mtab to a dict
    mtab_dict = {}
    try:
        for ent in get_mtab():
            mtab_dict[ent.mnt_dir] = ent.mnt_fsname
    except Exception:
        pass

    # find a best match
    fdir = os.path.dirname(fname)
    match = fdir in mtab_dict
    chrootfs = False
    while not match:
        if fdir == os.path.sep:
            chrootfs = True
            break
        fdir = os.path.realpath(os.path.join(fdir, os.path.pardir))
        match = fdir in mtab_dict

    # construct file path relative to device
    if fdir != os.path.sep:
        fname = fname[len(fdir) :]

    if chrootfs:
        return ":", fname
    return mtab_dict[fdir], fname


def is_remote_file(file) -> bool:
    """
    This function is trying to detect if the file in the argument is remote or not.

    :param file: The filepath to check.
    :return: If remote True, otherwise False.
    """
    (dev, _) = get_file_device_path(file)
    if dev.find(":") != -1:
        return True
    return False
