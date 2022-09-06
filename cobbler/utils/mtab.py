"""
We cache the contents of ``/etc/mtab``. The following module is used to keep our cache in sync.
"""

import os

mtab_mtime = None
mtab_map = []


class MntEntObj:
    mnt_fsname = None  # name of mounted file system
    mnt_dir = None  # file system path prefix
    mnt_type = None  # mount type (see mntent.h)
    mnt_opts = None  # mount options (see mntent.h)
    mnt_freq = 0  # dump frequency in days
    mnt_passno = 0  # pass number on parallel fsck

    def __init__(self, input: str = None):
        """
        This is an object which contains information about a mounted filesystem.

        :param input: This is a string which is separated internally by whitespace. If present it represents the
                      arguments: "mnt_fsname", "mnt_dir", "mnt_type", "mnt_opts", "mnt_freq" and "mnt_passno". The order
                      must be preserved, as well as the separation by whitespace.
        """
        if input and isinstance(input, str):
            (
                self.mnt_fsname,
                self.mnt_dir,
                self.mnt_type,
                self.mnt_opts,
                self.mnt_freq,
                self.mnt_passno,
            ) = input.split()

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
        return "%s %s %s %s %s %s" % (
            self.mnt_fsname,
            self.mnt_dir,
            self.mnt_type,
            self.mnt_opts,
            self.mnt_freq,
            self.mnt_passno,
        )


def get_mtab(mtab="/etc/mtab", vfstype: bool = False) -> list:
    """
    Get the list of mtab entries. If a custom mtab should be read then the location can be overridden via a parameter.

    :param mtab: The location of the mtab. Argument can be omitted if the mtab is at its default location.
    :param vfstype: If this is True, then all filesystems which are nfs are returned. Otherwise this returns all mtab
                    entries.
    :return: The list of requested mtab entries.
    """
    global mtab_mtime, mtab_map

    mtab_stat = os.stat(mtab)
    if mtab_stat.st_mtime != mtab_mtime:
        # cache is stale ... refresh
        mtab_mtime = mtab_stat.st_mtime
        mtab_map = __cache_mtab__(mtab)

    # was a specific fstype requested?
    if vfstype:
        mtab_type_map = []
        for ent in mtab_map:
            if ent.mnt_type == "nfs":
                mtab_type_map.append(ent)
        return mtab_type_map

    return mtab_map


def __cache_mtab__(mtab="/etc/mtab"):
    """
    Open the mtab and cache it inside Cobbler. If it is guessed that the mtab hasn't changed the cache data is used.

    :param mtab: The location of the mtab. Argument can be ommited if the mtab is at its default location.
    :return: The mtab content stripped from empty lines (if any are present).
    """
    with open(mtab) as f:
        mtab = [MntEntObj(line) for line in f.read().split("\n") if len(line) > 0]

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
    except:
        pass

    # find a best match
    fdir = os.path.dirname(fname)
    if fdir in mtab_dict:
        match = True
    else:
        match = False
    chrootfs = False
    while not match:
        if fdir == os.path.sep:
            chrootfs = True
            break
        fdir = os.path.realpath(os.path.join(fdir, os.path.pardir))
        if fdir in mtab_dict:
            match = True
        else:
            match = False

    # construct file path relative to device
    if fdir != os.path.sep:
        fname = fname[len(fdir) :]

    if chrootfs:
        return ":", fname
    else:
        return mtab_dict[fdir], fname


def is_remote_file(file) -> bool:
    """
    This function is trying to detect if the file in the argument is remote or not.

    :param file: The filepath to check.
    :return: If remote True, otherwise False.
    """
    (dev, path) = get_file_device_path(file)
    if dev.find(":") != -1:
        return True
    else:
        return False
