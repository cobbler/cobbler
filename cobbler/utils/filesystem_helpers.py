"""
TODO
"""

import errno
import glob
import hashlib
import json
import logging
import os
import shutil
import urllib
import pathlib
from typing import Union

from cobbler.cexceptions import CX
from cobbler.utils import log_exc, mtab
from cobbler import utils

logger = logging.getLogger()


def is_safe_to_hardlink(src: str, dst: str, api) -> bool:
    """
    Determine if it is safe to hardlink a file to the destination path.

    :param src: The hardlink source path.
    :param dst: The hardlink target path.
    :param api: The api-instance to resolve needed information with.
    :return: True if selinux is disabled, the file is on the same device, the source in not a link, and it is not a
             remote path. If selinux is enabled the functions still may return true if the object is a kernel or initrd.
             Otherwise returns False.
    """
    # FIXME: Calling this with emtpy strings returns True?!
    (dev1, path1) = mtab.get_file_device_path(src)
    (dev2, _) = mtab.get_file_device_path(dst)
    if dev1 != dev2:
        return False
    # Do not hardlink to a symbolic link! Chances are high the new link will be dangling.
    if pathlib.Path(src).is_symlink():
        return False
    if dev1.find(":") != -1:
        # Is a remote file
        return False
    # Note: This is very Cobbler implementation specific!
    if not api.is_selinux_enabled():
        return True
    path1_basename = str(pathlib.PurePath(path1).name)
    if utils.re_initrd.match(path1_basename):
        return True
    if utils.re_kernel.match(path1_basename):
        return True
    # We're dealing with SELinux and files that are not safe to chown
    return False


def sha1_file(file_path: Union[str, os.PathLike], buffer_size=65536) -> str:
    """
    This function is emulating the functionality of the sha1sum tool.

    :param file_path: The path to the file that should be hashed.
    :param buffer_size: The buffer-size that should be used to hash the file.
    :return: The SHA1 hash as sha1sum would return it.
    """
    # Highly inspired by: https://stackoverflow.com/a/22058673
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as file_fd:
        while True:
            data = file_fd.read(buffer_size)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def hashfile(file_name: str, lcache=None):
    r"""
    Returns the sha1sum of the file

    :param file_name: The file to get the sha1sum of.
    :param lcache: This is a directory where Cobbler would store its ``link_cache.json`` file to speed up the return
                   of the hash. The hash looked up would be checked against the Cobbler internal mtime of the object.
    :return: The sha1 sum or None if the file doesn't exist.
    """
    hashfile_db = {}
    dbfile = pathlib.Path(lcache) / "link_cache.json"
    if lcache is not None:
        if dbfile.exists():
            hashfile_db = json.loads(dbfile.read_text(encoding="utf-8"))

    file = pathlib.Path(file_name)
    if file.exists():
        mtime = file.stat().st_mtime
        if lcache is not None and file_name in hashfile_db:
            if hashfile_db[file_name][0] >= mtime:
                return hashfile_db[file_name][1]

        key = sha1_file(file_name)
        if lcache is not None:
            hashfile_db[file_name] = (mtime, key)
            __create_if_not_exists(lcache)
            dbfile.write_text(json.dumps(hashfile_db), encoding="utf-8")
        return key
    return None


def cachefile(src: str, dst: str):
    """
    Copy a file into a cache and link it into place. Use this with caution, otherwise you could end up copying data
    twice if the cache is not on the same device as the destination.

    :param src: The sourcefile for the copy action.
    :param dst: The destination for the copy action.
    """
    lcache = pathlib.Path(dst).parent.parent / ".link_cache"
    if not lcache.is_dir():
        lcache.mkdir()
    key = hashfile(src, lcache=lcache)
    cachefile_obj = lcache / key
    if not cachefile_obj.exists():
        logger.info("trying to create cache file %s", cachefile_obj)
        copyfile(src, str(cachefile_obj))

    logger.debug("trying cachelink %s -> %s -> %s", src, cachefile_obj, dst)
    os.link(cachefile_obj, dst)


def linkfile(api, src: str, dst: str, symlink_ok: bool = False, cache: bool = True):
    """
    Attempt to create a link dst that points to src. Because file systems suck we attempt several different methods or
    bail to just copying the file.

    :param api: This parameter is needed to check if a file can be hardlinked. This method fails if this parameter is
                not present.
    :param src: The source file.
    :param dst: The destination for the link.
    :param symlink_ok: If it is okay to just use a symbolic link.
    :param cache: If it is okay to use a cached file instead of the real one.
    :raises CX: Raised in case the API is not given.
    """
    dst_obj = pathlib.Path(dst)
    src_obj = pathlib.Path(src)
    if dst_obj.exists():
        # if the destination exists, is it right in terms of accuracy and context?
        if src_obj.samefile(dst):
            if not is_safe_to_hardlink(src, dst, api):
                # may have to remove old hardlinks for SELinux reasons as previous implementations were not complete
                logger.info("removing: %s", dst)
                dst_obj.unlink()
            else:
                return
        elif dst_obj.is_symlink():
            # existing path exists and is a symlink, update the symlink
            logger.info("removing: %s", dst)
            dst_obj.unlink()

    if is_safe_to_hardlink(src, dst, api):
        # we can try a hardlink if the destination isn't to NFS or Samba this will help save space and sync time.
        try:
            logger.info("trying hardlink %s -> %s", src, dst)
            os.link(src, dst)
            return
        except (IOError, OSError):
            # hardlink across devices, or link already exists we'll just symlink it if we can or otherwise copy it
            pass

    if symlink_ok:
        # we can symlink anywhere except for /tftpboot because that is run chroot, so if we can symlink now, try it.
        try:
            logger.info("trying symlink %s -> %s", src, dst)
            dst_obj.symlink_to(src_obj)
            return
        except (IOError, OSError):
            pass

    if cache:
        try:
            cachefile(src, dst)
            return
        except (IOError, OSError):
            pass

    # we couldn't hardlink and we couldn't symlink so we must copy
    copyfile(src, dst)


def copyfile(src: str, dst: str, symlink=False):
    """
    Copy a file from source to the destination.

    :param src: The source file. This may also be a folder.
    :param dst: The destination for the file or folder.
    :param symlink: If instead of a copy, a symlink is okay, then this may be set explicitly to "True".
    :raises OSError: Raised in case ``src`` could not be read.
    """
    src_obj = pathlib.Path(src)
    dst_obj = pathlib.Path(dst)
    try:
        logger.info("copying: %s -> %s", src, dst)
        if src_obj.is_dir():
            shutil.copytree(src, dst, symlinks=symlink)
        else:
            shutil.copyfile(src, dst, follow_symlinks=symlink)
    except Exception as error:
        if not os.access(src, os.R_OK):
            raise OSError(f"Cannot read: {src}") from error
        if src_obj.samefile(dst_obj):
            # accomodate for the possibility that we already copied
            # the file as a symlink/hardlink
            raise
            # traceback.print_exc()
            # raise CX("Error copying %(src)s to %(dst)s" % { "src" : src, "dst" : dst})


def copyremotefile(src: str, dst1: str, api=None):
    """
    Copys a file from a remote place to the local destionation.

    :param src: The remote file URI.
    :param dst1: The copy destination on the local filesystem.
    :param api: This parameter is not used currently.
    :raises OSError: Raised in case an error occurs when fetching or writing the file.
    """
    try:
        logger.info("copying: %s -> %s", src, dst1)
        with urllib.request.urlopen(src) as srcfile:
            with open(dst1, "wb") as output:
                output.write(srcfile.read())
    except Exception as error:
        raise OSError(
            f"Error while getting remote file ({src} -> {dst1}):\n{error}"
        ) from error


def copyfile_pattern(
    pattern,
    dst,
    require_match: bool = True,
    symlink_ok: bool = False,
    cache: bool = True,
    api=None,
):
    """
    Copy 1 or more files with a pattern into a destination.

    :param pattern: The pattern for finding the required files.
    :param dst: The destination for the file(s) found.
    :param require_match: If the glob pattern does not find files should an error message be thrown or not.
    :param symlink_ok: If it is okay to just use a symlink to link the file to the destination.
    :param cache: If it is okay to use a file from the cache (which could be possibly newer) or not.
    :param api: Passed to ``linkfile()``.
    :raises CX: Raised in case files not found according to ``pattern``.
    """
    files = glob.glob(pattern)
    if require_match and not len(files) > 0:
        raise CX(f"Could not find files matching {pattern}")
    dst_obj = pathlib.Path(dst)
    for file in files:
        file_obj = pathlib.Path(file)
        dst1 = dst_obj / file_obj.name
        linkfile(api, file, str(dst1), symlink_ok=symlink_ok, cache=cache)


def rmfile(path: str):
    """
    Delete a single file.

    :param path: The file to delete.
    """
    try:
        pathlib.Path(path).unlink()
        logger.info('Successfully removed "%s"', path)
    except FileNotFoundError:
        pass
    except OSError as ioe:
        logger.warning('Could not remove file "%s": %s', path, ioe.strerror)


def rmtree_contents(path: str):
    """
    Delete the content of a folder with a glob pattern.

    :param path: This parameter presents the glob pattern of what should be deleted.
    """
    what_to_delete = glob.glob(f"{path}/*")
    for rmtree_path in what_to_delete:
        rmtree(rmtree_path)


def rmtree(path: str):
    """
    Delete a complete directory or just a single file.

    :param path: The directory or folder to delete.
    :raises CX: Raised in case ``path`` does not exist.
    """
    try:
        if pathlib.Path(path).is_file():
            rmfile(path)
        logger.info("removing: %s", path)
        shutil.rmtree(path, ignore_errors=True)
    except OSError as ioe:
        log_exc()
        if ioe.errno != errno.ENOENT:  # doesn't exist
            raise CX(f"Error deleting {path}") from ioe


def rmglob_files(path: str, glob_pattern: str):
    """
    Deletes all files in ``path`` with ``glob_pattern`` with the help of ``rmfile()``.

    :param path: The folder of the files to remove.
    :param glob_pattern: The glob pattern for the files to remove in ``path``.
    """
    for rm_path in pathlib.Path(path).glob(glob_pattern):
        rmfile(str(rm_path))


def mkdir(path: str, mode=0o755):
    """
    Create directory with a given mode.

    :param path: The path to create the directory at.
    :param mode: The mode to create the directory with.
    :raises CX: Raised in case creating the directory fails with something different from error code 17 (directory
                already exists).
    """
    try:
        pathlib.Path(path).mkdir(mode=mode)
    except OSError as os_error:
        # already exists (no constant for 17?)
        if os_error.errno != 17:
            log_exc()
            raise CX(f"Error creating {path}") from os_error


def path_tail(apath, bpath) -> str:
    """
    Given two paths (B is longer than A), find the part in B not in A

    :param apath: The first path.
    :param bpath: The second path.
    :return: If the paths are not starting at the same location this function returns an empty string.
    """
    position = bpath.find(apath)
    if position != 0:
        return ""
    rposition = position + len(apath)
    result = bpath[rposition:]
    if not result.startswith("/"):
        result = "/" + result
    return result


def safe_filter(var):
    r"""
    This function does nothing if the argument does not find any semicolons or two points behind each other.

    :param var: This parameter shall not be None or have ".."/";" at the end.
    :raises CX: In case any ``..`` or ``/`` is found in ``var``.
    """
    if var is None:
        return
    if var.find("..") != -1 or var.find(";") != -1:
        raise CX("Invalid characters found in input")


def __create_if_not_exists(path: pathlib.Path):
    """
    Creates a directory if it has not already been created.

    :param path: The path where the directory should be created. Parents directories must exist.
    """
    if not path.exists():
        mkdir(str(path))


def __symlink_if_not_exists(source: pathlib.Path, target: pathlib.Path):
    """
    Symlinks a directory if the symlink doesn't exist.

    :param source: The source directory
    :param target: The target directory
    """
    if not target.exists():
        target.symlink_to(source)


def create_web_dirs(api):
    """
    Create directories for HTTP content

    :param api: CobblerAPI
    """
    webdir_obj = pathlib.Path(api.settings().webdir)
    webroot_distro_mirror = webdir_obj / "distro_mirror"
    webroot_misc = webdir_obj / "misc"

    webroot_directory_paths = [
        webdir_obj / "localmirror",
        webdir_obj / "repo_mirror",
        webroot_distro_mirror,
        webroot_distro_mirror / "config",
        webdir_obj / "links",
        webroot_misc,
        webdir_obj / "pub",
        webdir_obj / "rendered",
        webdir_obj / "images",
    ]
    for directory_path in webroot_directory_paths:
        __create_if_not_exists(directory_path)

    # Copy anamon scripts to the webroot
    misc_path = pathlib.Path("/var/lib/cobbler/misc")
    rmtree_contents(str(webroot_misc))
    for file in [f for f in misc_path.iterdir() if (misc_path / f).is_file()]:
        copyfile(str((misc_path / file)), str(webroot_misc))


def create_tftpboot_dirs(api):
    """
    Create directories for tftpboot images

    :param api: CobblerAPI
    """
    bootloc = pathlib.Path(api.settings().tftpboot_location)
    grub_dir = bootloc / "grub"
    esxi_dir = bootloc / "esxi"

    tftpboot_directory_paths = [
        bootloc / "boot",
        bootloc / "etc",
        bootloc / "images2",
        bootloc / "ppc",
        bootloc / "s390x",
        bootloc / "pxelinux.cfg",
        grub_dir,
        grub_dir / "system",
        grub_dir / "system_link",
        bootloc / "images",
        bootloc / "ipxe",
        esxi_dir,
        esxi_dir / "system",
    ]
    for directory_path in tftpboot_directory_paths:
        __create_if_not_exists(directory_path)

    grub_images_link = grub_dir / "images"
    __symlink_if_not_exists(pathlib.Path("../images"), grub_images_link)
    esxi_images_link = esxi_dir / "images"
    __symlink_if_not_exists(pathlib.Path("../images"), esxi_images_link)
    esxi_pxelinux_link = esxi_dir / "pxelinux.cfg"
    __symlink_if_not_exists(pathlib.Path("../pxelinux.cfg"), esxi_pxelinux_link)


def create_trigger_dirs(api):
    """
    Creates the directories that the user/admin can fill with dynamically executed scripts.

    :param api: CobblerAPI
    """
    # This is not yet a setting
    libpath = pathlib.Path("/var/lib/cobbler")
    trigger_directory = libpath / "triggers"
    trigger_directories = [
        trigger_directory,
        trigger_directory / "add",
        trigger_directory / "add" / "distro",
        trigger_directory / "add" / "distro" / "pre",
        trigger_directory / "add" / "distro" / "post",
        trigger_directory / "add" / "profile",
        trigger_directory / "add" / "profile" / "pre",
        trigger_directory / "add" / "profile" / "post",
        trigger_directory / "add" / "system",
        trigger_directory / "add" / "system" / "pre",
        trigger_directory / "add" / "system" / "post",
        trigger_directory / "add" / "repo",
        trigger_directory / "add" / "repo" / "pre",
        trigger_directory / "add" / "repo" / "post",
        trigger_directory / "add" / "mgmtclass",
        trigger_directory / "add" / "mgmtclass" / "pre",
        trigger_directory / "add" / "mgmtclass" / "post",
        trigger_directory / "add" / "package",
        trigger_directory / "add" / "package" / "pre",
        trigger_directory / "add" / "package" / "post",
        trigger_directory / "add" / "file",
        trigger_directory / "add" / "file" / "pre",
        trigger_directory / "add" / "file" / "post",
        trigger_directory / "add" / "menu",
        trigger_directory / "add" / "menu" / "pre",
        trigger_directory / "add" / "menu" / "post",
        trigger_directory / "delete",
        trigger_directory / "delete" / "distro",
        trigger_directory / "delete" / "distro" / "pre",
        trigger_directory / "delete" / "distro" / "post",
        trigger_directory / "delete" / "profile",
        trigger_directory / "delete" / "profile" / "pre",
        trigger_directory / "delete" / "profile" / "post",
        trigger_directory / "delete" / "system",
        trigger_directory / "delete" / "system" / "pre",
        trigger_directory / "delete" / "system" / "post",
        trigger_directory / "delete" / "repo",
        trigger_directory / "delete" / "repo" / "pre",
        trigger_directory / "delete" / "repo" / "post",
        trigger_directory / "delete" / "mgmtclass",
        trigger_directory / "delete" / "mgmtclass" / "pre",
        trigger_directory / "delete" / "mgmtclass" / "post",
        trigger_directory / "delete" / "package",
        trigger_directory / "delete" / "package" / "pre",
        trigger_directory / "delete" / "package" / "post",
        trigger_directory / "delete" / "file",
        trigger_directory / "delete" / "file" / "pre",
        trigger_directory / "delete" / "file" / "post",
        trigger_directory / "delete" / "menu",
        trigger_directory / "delete" / "menu" / "pre",
        trigger_directory / "delete" / "menu" / "post",
        trigger_directory / "install",
        trigger_directory / "install" / "pre",
        trigger_directory / "install" / "post",
        trigger_directory / "install" / "firstboot",
        trigger_directory / "sync",
        trigger_directory / "sync" / "pre",
        trigger_directory / "sync" / "post",
        trigger_directory / "change",
        trigger_directory / "task",
        trigger_directory / "task" / "distro",
        trigger_directory / "task" / "distro" / "pre",
        trigger_directory / "task" / "distro" / "post",
        trigger_directory / "task" / "profile",
        trigger_directory / "task" / "profile" / "pre",
        trigger_directory / "task" / "profile" / "post",
        trigger_directory / "task" / "system",
        trigger_directory / "task" / "system" / "pre",
        trigger_directory / "task" / "system" / "post",
        trigger_directory / "task" / "repo",
        trigger_directory / "task" / "repo" / "pre",
        trigger_directory / "task" / "repo" / "post",
        trigger_directory / "task" / "mgmtclass",
        trigger_directory / "task" / "mgmtclass" / "pre",
        trigger_directory / "task" / "mgmtclass" / "post",
        trigger_directory / "task" / "package",
        trigger_directory / "task" / "package" / "pre",
        trigger_directory / "task" / "package" / "post",
        trigger_directory / "task" / "file",
        trigger_directory / "task" / "file" / "pre",
        trigger_directory / "task" / "file" / "post",
        trigger_directory / "task" / "menu",
        trigger_directory / "task" / "menu" / "pre",
        trigger_directory / "task" / "menu" / "post",
    ]

    for directory_path in trigger_directories:
        __create_if_not_exists(directory_path)


def create_json_database_dirs(api):
    """
    Creates the database directories for the file serializer

    :param api: CobblerAPI
    """
    # This is not yet a setting
    libpath = pathlib.Path("/var/lib/cobbler")
    database_directories = [
        libpath / "collections",
        libpath / "collections" / "distros",
        libpath / "collections" / "images",
        libpath / "collections" / "profiles",
        libpath / "collections" / "repos",
        libpath / "collections" / "systems",
        libpath / "collections" / "mgmtclasses",
        libpath / "collections" / "packages",
        libpath / "collections" / "files",
        libpath / "collections" / "menus",
    ]

    for directory_path in database_directories:
        __create_if_not_exists(directory_path)
