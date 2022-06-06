import errno
import glob
import json
import logging
import os
import shutil
import urllib
from pathlib import Path
from typing import Optional

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
    (dev2, path2) = mtab.get_file_device_path(dst)
    if dev1 != dev2:
        return False
    # Do not hardlink to a symbolic link! Chances are high the new link will be dangling.
    if os.path.islink(src):
        return False
    if dev1.find(":") != -1:
        # Is a remote file
        return False
    # Note: This is very Cobbler implementation specific!
    if not api.is_selinux_enabled():
        return True
    if utils.re_initrd.match(os.path.basename(path1)):
        return True
    if utils.re_kernel.match(os.path.basename(path1)):
        return True
    # We're dealing with SELinux and files that are not safe to chown
    return False


def hashfile(fn, lcache=None):
    r"""
    Returns the sha1sum of the file

    :param fn: The file to get the sha1sum of.
    :param lcache: This is a directory where Cobbler would store its ``link_cache.json`` file to speed up the return
                   of the hash. The hash looked up would be checked against the Cobbler internal mtime of the object.
    :return: The sha1 sum or None if the file doesn't exist.
    """
    db = {}
    # FIXME: The directory from the following line may not exist.
    dbfile = os.path.join(lcache, "link_cache.json")
    try:
        if os.path.exists(dbfile):
            db = json.load(open(dbfile, "r"))
    except:
        pass

    mtime = os.stat(fn).st_mtime
    if fn in db:
        if db[fn][0] >= mtime:
            return db[fn][1]

    if os.path.exists(fn):
        # TODO: Replace this with the follwing: https://stackoverflow.com/a/22058673
        cmd = "/usr/bin/sha1sum %s" % fn
        key = utils.subprocess_get(cmd).split(" ")[0]
        if lcache is not None:
            db[fn] = (mtime, key)
            # TODO: Safeguard this against above mentioned directory does not exist error.
            json.dump(db, open(dbfile, "w"))
        return key
    else:
        return None


def cachefile(src: str, dst: str):
    """
    Copy a file into a cache and link it into place. Use this with caution, otherwise you could end up copying data
    twice if the cache is not on the same device as the destination.

    :param src: The sourcefile for the copy action.
    :param dst: The destination for the copy action.
    """
    lcache = os.path.join(os.path.dirname(os.path.dirname(dst)), ".link_cache")
    if not os.path.isdir(lcache):
        os.mkdir(lcache)
    key = hashfile(src, lcache=lcache)
    cachefile = os.path.join(lcache, key)
    if not os.path.exists(cachefile):
        logger.info("trying to create cache file %s", cachefile)
        copyfile(src, cachefile)

    logger.debug("trying cachelink %s -> %s -> %s", src, cachefile, dst)
    os.link(cachefile, dst)


def linkfile(
    src: str, dst: str, symlink_ok: bool = False, cache: bool = True, api=None
):
    """
    Attempt to create a link dst that points to src. Because file systems suck we attempt several different methods or
    bail to just copying the file.

    :param src: The source file.
    :param dst: The destination for the link.
    :param symlink_ok: If it is okay to just use a symbolic link.
    :param cache: If it is okay to use a cached file instead of the real one.
    :param api: This parameter is needed to check if a file can be hardlinked. This method fails if this parameter is
                not present.
    :raises CX: Raised in case the API is not given.
    """

    if api is None:
        # FIXME: this really should not be a keyword arg
        raise CX("Internal error: API handle is required")

    if os.path.exists(dst):
        # if the destination exists, is it right in terms of accuracy and context?
        if os.path.samefile(src, dst):
            if not is_safe_to_hardlink(src, dst, api):
                # may have to remove old hardlinks for SELinux reasons as previous implementations were not complete
                logger.info("removing: %s", dst)
                os.remove(dst)
            else:
                return
        elif os.path.islink(dst):
            # existing path exists and is a symlink, update the symlink
            logger.info("removing: %s", dst)
            os.remove(dst)

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
            os.symlink(src, dst)
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
    :raises OSError: Raised in case ``src`` could not be read.
    """
    try:
        logger.info("copying: %s -> %s", src, dst)
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=symlink)
        else:
            shutil.copyfile(src, dst, follow_symlinks=symlink)
    except:
        if not os.access(src, os.R_OK):
            raise OSError("Cannot read: %s" % src)
        if os.path.samefile(src, dst):
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
        srcfile = urllib.request.urlopen(src)
        with open(dst1, "wb") as output:
            output.write(srcfile.read())
    except Exception as error:
        raise OSError(
            "Error while getting remote file (%s -> %s):\n%s" % (src, dst1, error)
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
        raise CX("Could not find files matching %s" % pattern)
    for file in files:
        dst1 = os.path.join(dst, os.path.basename(file))
        linkfile(file, dst1, symlink_ok=symlink_ok, cache=cache, api=api)


def rmfile(path: str):
    """
    Delete a single file.

    :param path: The file to delete.
    """
    try:
        os.remove(path)
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
    what_to_delete = glob.glob("%s/*" % path)
    for x in what_to_delete:
        rmtree(x)


def rmtree(path: str) -> Optional[bool]:
    """
    Delete a complete directory or just a single file.

    :param path: The directory or folder to delete.
    :return: May possibly return true on success or may return None on success.
    :raises CX: Raised in case ``path`` does not exist.
    """
    # TODO: Obsolete bool return value
    try:
        if os.path.isfile(path):
            return rmfile(path)
        logger.info("removing: %s", path)
        return shutil.rmtree(path, ignore_errors=True)
    except OSError as ioe:
        log_exc()
        if ioe.errno != errno.ENOENT:  # doesn't exist
            raise CX("Error deleting %s" % path) from ioe
        return True


def rmglob_files(path: str, glob_pattern: str):
    """
    Deletes all files in ``path`` with ``glob_pattern`` with the help of ``rmfile()``.

    :param path: The folder of the files to remove.
    :param glob_pattern: The glob pattern for the files to remove in ``path``.
    """
    for p in Path(path).glob(glob_pattern):
        rmfile(str(p))


def mkdir(path, mode=0o755):
    """
    Create directory with a given mode.

    :param path: The path to create the directory at.
    :param mode: The mode to create the directory with.
    :raises CX: Raised in case creating the directory fails with something different from error code 17 (directory
                already exists).
    """
    try:
        os.makedirs(path, mode)
    except OSError as os_error:
        # already exists (no constant for 17?)
        if os_error.errno != 17:
            log_exc()
            raise CX("Error creating %s" % path) from os_error


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
