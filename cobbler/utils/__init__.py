"""
Misc heavy lifting functions for Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from functools import reduce
from pathlib import Path
from typing import List, Optional, Pattern, Union

import distro
import netaddr

from cobbler import enums, settings
from cobbler.cexceptions import CX
from cobbler.utils import mtab, process_management

CHEETAH_ERROR_DISCLAIMER = """
# *** ERROR ***
#
# There is a templating error preventing this file from rendering correctly.
#
# This is most likely not due to a bug in Cobbler and is something you can fix.
#
# Look at the message below to see what things are causing problems.
#
# (1) Does the template file reference a $variable that is not defined?
# (2) is there a formatting error in a Cheetah directive?
# (3) Should dollar signs ($) be escaped that are not being escaped?
#
# Try fixing the problem and then investigate to see if this message goes
# away or changes.
#
"""

re_kernel = re.compile(
    r"(vmlinu[xz]|(kernel|linux(\.img)?)|pxeboot\.n12|wimboot|mboot\.c32|.+\.kernel)"
)
re_initrd = re.compile(r"(initrd(.*)\.img|ramdisk\.image\.gz|boot\.sdi|imgpayld\.tgz)")


# all logging from utils.die goes to the main log even if there
# is another log.
logger = logging.getLogger()


def die(msg: str):
    """
    This method let's Cobbler crash with an exception. Log the exception once in the per-task log or the main log if
    this is not a background op.

    :param msg: The message to send for raising the exception
    :raises CX: Raised in all cases with ``msg``.
    """

    # log the exception once in the per-task log or the main log if this is not a background op.
    try:
        raise CX(msg)
    except CX:
        log_exc()

    # now re-raise it so the error can fail the operation
    raise CX(msg)


def log_exc():
    """
    Log an exception.
    """
    (t, v, tb) = sys.exc_info()
    logger.info("Exception occurred: %s", t)
    logger.info("Exception value: %s", v)
    logger.info(
        "Exception Info:\n%s",
        "\n".join(traceback.format_list(traceback.extract_tb(tb))),
    )


def get_exc(exc, full: bool = True):
    """
    This tries to analyze if an exception comes from Cobbler and potentially enriches or shortens the exception.

    :param exc: The exception which should be analyzed.
    :param full: If the full exception should be returned or only the most important information.
    :return: The exception which has been converted into a string which then can be logged easily.
    """
    (t, v, tb) = sys.exc_info()
    buf = ""
    try:
        getattr(exc, "from_cobbler")
        buf = str(exc)[1:-1] + "\n"
    except:
        if not full:
            buf += str(t)
        buf = "%s\n%s" % (buf, v)
        if full:
            buf += "\n" + "\n".join(traceback.format_list(traceback.extract_tb(tb)))
    return buf


def cheetah_exc(exc) -> str:
    """
    Converts an exception thrown by Cheetah3 into a custom error message.

    :param exc: The exception to convert.
    :return: The string representation of the Cheetah3 exception.
    """
    lines = get_exc(exc).split("\n")
    buf = ""
    for line in lines:
        buf += "# %s\n" % line
    return CHEETAH_ERROR_DISCLAIMER + buf


def pretty_hex(ip, length=8) -> str:
    """
    Pads an IP object with leading zeroes so that the result is _length_ hex digits.  Also do an upper().

    :param ip: The IP address to pretty print.
    :param length: The length of the resulting hexstring. If the number is smaller than the resulting hex-string
                   then no front-padding is done.
    """
    hexval = "%x" % ip.value
    if len(hexval) < length:
        hexval = "0" * (length - len(hexval)) + hexval
    return hexval.upper()


def get_host_ip(ip, shorten=True) -> str:
    """
    Return the IP encoding needed for the TFTP boot tree.

    :param ip: The IP address to pretty print.
    :param shorten: Whether the IP-Address should be shortened or not.
    :return: The IP encoded as a hexadecimal value.
    """

    ip = netaddr.ip.IPAddress(ip)
    cidr = netaddr.ip.IPNetwork(ip)

    if len(cidr) == 1:  # Just an IP, e.g. a /32
        return pretty_hex(ip)
    else:
        pretty = pretty_hex(cidr[0])
        if not shorten or len(cidr) <= 8:
            # not enough to make the last nibble insignificant
            return pretty
        else:
            cutoff = (32 - cidr.prefixlen) // 4
            return pretty[0:-cutoff]


def _IP(ip):
    """
    Returns a netaddr.IP object representing an ip.
    If ip is already an netaddr.IP instance just return it.
    Else return a new instance
    """
    ip_class = netaddr.ip.IPAddress
    if isinstance(ip, ip_class) or ip == "":
        return ip
    else:
        return ip_class(ip)


def is_ip(strdata: str) -> bool:
    """
    Return whether the argument is an IP address.

    :param strdata: The IP in a string format. This get's passed to the IP object of Python.
    """
    try:
        _IP(strdata)
    except:
        return False
    return True


def get_random_mac(api_handle, virt_type="xenpv") -> str:
    """
    Generate a random MAC address.

    The code of this method was taken from xend/server/netif.py

    :param api_handle: The main Cobbler api instance.
    :param virt_type: The virtualization provider. Currently possible is 'vmware', 'xen', 'qemu', 'kvm'.
    :returns: MAC address string
    :raises CX: Raised in case unsupported ``virt_type`` given.
    """
    if virt_type.startswith("vmware"):
        mac = [
            0x00,
            0x50,
            0x56,
            random.randint(0x00, 0x3F),
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
        ]
    elif (
        virt_type.startswith("xen")
        or virt_type.startswith("qemu")
        or virt_type.startswith("kvm")
    ):
        mac = [
            0x00,
            0x16,
            0x3E,
            random.randint(0x00, 0x7F),
            random.randint(0x00, 0xFF),
            random.randint(0x00, 0xFF),
        ]
    else:
        raise CX("virt mac assignment not yet supported")

    mac = ":".join(["%02x" % x for x in mac])
    systems = api_handle.systems()
    while systems.find(mac_address=mac):
        mac = get_random_mac(api_handle)

    return mac


def find_matching_files(directory: str, regex: Pattern[str]) -> list:
    """
    Find all files in a given directory that match a given regex. Can't use glob directly as glob doesn't take regexen.
    The search does not include subdirectories.

    :param directory: The directory to search in.
    :param regex: The regex to apply to the found files.
    :return: An array of files which apply to the regex.
    """
    files = glob.glob(os.path.join(directory, "*"))
    results = []
    for f in files:
        if regex.match(os.path.basename(f)):
            results.append(f)
    return results


def find_highest_files(directory: str, unversioned: str, regex: Pattern[str]) -> str:
    """
    Find the highest numbered file (kernel or initrd numbering scheme) in a given directory that matches a given
    pattern. Used for auto-booting the latest kernel in a directory.

    :param directory: The directory to search in.
    :param unversioned: The base filename which also acts as a last resort if no numbered files are found.
    :param regex: The regex to search for.
    :return: The file with the highest number or an empty string.
    """
    files = find_matching_files(directory, regex)
    get_numbers = re.compile(r"(\d+).(\d+).(\d+)")

    def max2(a, b):
        """
        Returns the larger of the two values
        """
        av = get_numbers.search(os.path.basename(a)).groups()
        bv = get_numbers.search(os.path.basename(b)).groups()

        if av > bv:
            return a
        return b

    if len(files) > 0:
        return reduce(max2, files)

    # Couldn't find a highest numbered file, but maybe there is just a 'vmlinuz' or an 'initrd.img' in this directory?
    last_chance = os.path.join(directory, unversioned)
    if os.path.exists(last_chance):
        return last_chance
    return ""


def find_kernel(path: str) -> str:
    """
    Given a filename, find if the path can be made to resolve into a kernel, and return that full path if possible.

    :param path: The path to check for a kernel.
    :return: path if at the specified location a possible match for a kernel was found, otherwise an empty string.
    """
    if not isinstance(path, str):
        raise TypeError("path must be of type str!")

    if os.path.isfile(path):
        filename = os.path.basename(path)
        if re_kernel.match(filename) or filename == "vmlinuz":
            return path
    elif os.path.isdir(path):
        return find_highest_files(path, "vmlinuz", re_kernel)
    # For remote URLs we expect an absolute path, and will not do any searching for the latest:
    elif file_is_remote(path) and remote_file_exists(path):
        return path
    return ""


def remove_yum_olddata(path: os.PathLike):
    """
    Delete .olddata folders that might be present from a failed run of createrepo.

    :param path: The path to check for .olddata files.
    """
    directories_to_try = [
        ".olddata",
        ".repodata/.olddata",
        "repodata/.oldata",
        "repodata/repodata",
    ]
    for pathseg in directories_to_try:
        olddata = Path(path, pathseg)
        if olddata.is_dir() and olddata.exists():
            logger.info('Removing: "%s"', olddata)
            shutil.rmtree(olddata, ignore_errors=False, onerror=None)


def find_initrd(path: str) -> Optional[str]:
    """
    Given a directory or a filename, see if the path can be made to resolve into an intird, return that full path if
    possible.

    :param path: The path to check for initrd files.
    :return: None or the path to the found initrd.
    """
    # FUTURE: try to match kernel/initrd pairs?
    if path is None:
        return None

    if os.path.isfile(path):
        # filename = os.path.basename(path)
        # if re_initrd.match(filename):
        #   return path
        # if filename == "initrd.img" or filename == "initrd":
        #   return path
        return path

    elif os.path.isdir(path):
        return find_highest_files(path, "initrd.img", re_initrd)

    # For remote URLs we expect an absolute path, and will not do any searching for the latest:
    elif file_is_remote(path) and remote_file_exists(path):
        return path

    return None


def read_file_contents(file_location, fetch_if_remote=False) -> Optional[str]:
    """
    Reads the contents of a file, which could be referenced locally or as a URI.

    :param file_location: The location of the file to read.
    :param fetch_if_remote: If True a remote file will be tried to read, otherwise remote files are skipped and None is
                            returned.
    :return: Returns None if file is remote and templating of remote files is disabled.
    :raises FileNotFoundError: if the file does not exist at the specified location.
    """

    # Local files:
    if file_location.startswith("/"):

        if not os.path.exists(file_location):
            logger.warning("File does not exist: %s", file_location)
            raise FileNotFoundError("%s: %s" % ("File not found", file_location))

        try:
            with open(file_location) as f:
                data = f.read()
            return data
        except:
            log_exc()
            raise

    # Remote files:
    if not fetch_if_remote:
        return None

    if file_is_remote(file_location):
        try:
            handler = urllib.request.urlopen(file_location)
            data = handler.read()
            handler.close()
            return data
        except urllib.error.HTTPError:
            # File likely doesn't exist
            logger.warning("File does not exist: %s", file_location)
            raise FileNotFoundError("%s: %s" % ("File not found", file_location))


def remote_file_exists(file_url) -> bool:
    """
    Return True if the remote file exists.

    :param file_url: The URL to check.
    :return: True if Cobbler can reach the specified URL, otherwise false.
    """
    try:
        handler = urllib.request.urlopen(file_url)
        handler.close()
        return True
    except urllib.error.HTTPError:
        # File likely doesn't exist
        return False


def file_is_remote(file_location) -> bool:
    """
    Returns true if the file is remote and referenced via a protocol we support.

    :param file_location: The URI to check.
    :return: True if the URI is http, https or ftp. Otherwise false.
    """
    file_loc_lc = file_location.lower()
    # Check for urllib2 supported protocols
    for prefix in ["http://", "https://", "ftp://"]:
        if file_loc_lc.startswith(prefix):
            return True
    return False


def blender(api_handle, remove_dicts: bool, root_obj):
    """
    Combine all of the data in an object tree from the perspective of that point on the tree, and produce a merged
    dictionary containing consolidated data.

    :param api_handle: The api to use for collecting the information to blender the item.
    :param remove_dicts: Boolean to decide whether dicts should be converted.
    :param root_obj: The object which should act as the root-node object.
    :return: A dictionary with all the information from the root node downwards.
    """
    tree = root_obj.grab_tree()
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node, results)

    # Make interfaces accessible without Cheetah-voodoo in the templates
    # EXAMPLE: $ip == $ip0, $ip1, $ip2 and so on.

    if root_obj.COLLECTION_TYPE == "system":
        for (name, interface) in list(root_obj.interfaces.items()):
            intf_dict = interface.to_dict()
            for key in intf_dict:
                results["%s_%s" % (key, name)] = intf_dict[key]

    # If the root object is a profile or system, add in all repo data for repos that belong to the object chain
    if root_obj.COLLECTION_TYPE in ("profile", "system"):
        repo_data = []
        for r in results.get("repos", []):
            repo = api_handle.find_repo(name=r)
            if repo:
                repo_data.append(repo.to_dict())
        # Sorting is courtesy of https://stackoverflow.com/a/73050/4730773
        results["repo_data"] = sorted(
            repo_data, key=lambda repo_dict: repo_dict["priority"], reverse=True
        )

    http_port = results.get("http_port", 80)
    if http_port in (80, "80"):
        results["http_server"] = results["server"]
    else:
        results["http_server"] = "%s:%s" % (results["server"], http_port)

    mgmt_parameters = results.get("mgmt_parameters", {})
    mgmt_parameters.update(results.get("autoinstall_meta", {}))
    results["mgmt_parameters"] = mgmt_parameters

    if "children" in results:
        child_names = results["children"]
        results["children"] = {}
        # logger.info("Children: %s", child_names)
        for key in child_names:
            child = api_handle.find_items("", name=key, return_list=False)
            if child is None:
                raise ValueError(
                    'Child with the name "%s" of parent object "%s" did not exist!'
                    % (key, root_obj.name)
                )
            results["children"][key] = child.to_dict()

    # sanitize output for koan and kernel option lines, etc
    if remove_dicts:
        results = flatten(results)

    # Add in some variables for easier templating as these variables change based on object type.
    if "interfaces" in results:
        # is a system object
        results["system_name"] = results["name"]
        results["profile_name"] = results["profile"]
        if "distro" in results:
            results["distro_name"] = results["distro"]
        elif "image" in results:
            results["distro_name"] = "N/A"
            results["image_name"] = results["image"]
    elif "distro" in results:
        # is a profile or subprofile object
        results["profile_name"] = results["name"]
        results["distro_name"] = results["distro"]
    elif "kernel" in results:
        # is a distro object
        results["distro_name"] = results["name"]
    elif "file" in results:
        # is an image object
        results["distro_name"] = "N/A"
        results["image_name"] = results["name"]

    return results


def flatten(data: dict) -> Optional[dict]:
    """
    Convert certain nested dicts to strings. This is only really done for the ones koan needs as strings this should
    not be done for everything

    :param data: The dictionary in which various keys should be converted into a string.
    :return: None (if data is None) or the flattened string.
    """

    if data is None or not isinstance(data, dict):
        return None
    if "environment" in data:
        data["environment"] = dict_to_string(data["environment"])
    if "kernel_options" in data:
        data["kernel_options"] = dict_to_string(data["kernel_options"])
    if "kernel_options_post" in data:
        data["kernel_options_post"] = dict_to_string(data["kernel_options_post"])
    if "yumopts" in data:
        data["yumopts"] = dict_to_string(data["yumopts"])
    if "autoinstall_meta" in data:
        data["autoinstall_meta"] = dict_to_string(data["autoinstall_meta"])
    if "template_files" in data:
        data["template_files"] = dict_to_string(data["template_files"])
    if "boot_files" in data:
        data["boot_files"] = dict_to_string(data["boot_files"])
    if "fetchable_files" in data:
        data["fetchable_files"] = dict_to_string(data["fetchable_files"])
    if "repos" in data and isinstance(data["repos"], list):
        data["repos"] = " ".join(data["repos"])
    if "rpm_list" in data and isinstance(data["rpm_list"], list):
        data["rpm_list"] = " ".join(data["rpm_list"])

    # Note -- we do not need to flatten "interfaces" as koan does not expect it to be a string, nor do we use it on a
    # kernel options line, etc...
    return data


def uniquify(seq: list) -> list:
    """
    Remove duplicates from the sequence handed over in the args.

    :param seq: The sequence to check for duplicates.
    :return: The list without duplicates.
    """

    # Credit: https://www.peterbe.com/plog/uniqifiers-benchmark
    # FIXME: if this is actually slower than some other way, overhaul it
    # For above there is a better version: https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
    seen = {}
    result = []
    for item in seq:
        if item in seen:
            continue
        seen[item] = 1
        result.append(item)
    return result


def __consolidate(node, results: dict) -> dict:
    """
    Merge data from a given node with the aggregate of all data from past scanned nodes. Dictionaries and arrays are
    treated specially.

    :param node: The object to merge data into. The data from the node always wins.
    :return: A dictionary with the consolidated data.
    """
    node_data = node.to_dict()

    # If the node has any data items labelled <<inherit>> we need to expunge them. So that they do not override the
    # supernodes.
    node_data_copy = {}
    for key in node_data:
        value = node_data[key]
        if value == enums.VALUE_INHERITED:
            if key not in results:
                # We need to add at least one value per key, use the property getter to resolve to the
                # settings or wherever we inherit from.
                node_data_copy[key] = getattr(node, key)
            # Old keys should have no inherit and thus are not a real property
            if key == "kickstart":
                node_data_copy[key] = getattr(type(node), "autoinstall").fget(node)
            elif key == "ks_meta":
                node_data_copy[key] = getattr(type(node), "autoinstall_meta").fget(node)
        else:
            if isinstance(value, dict):
                node_data_copy[key] = value.copy()
            elif isinstance(value, list):
                node_data_copy[key] = value[:]
            else:
                node_data_copy[key] = value

    for field in node_data_copy:
        data_item = node_data_copy[field]
        if field in results:
            # Now merge data types separately depending on whether they are dict, list, or scalar.
            fielddata = results[field]
            if isinstance(fielddata, dict):
                # interweave dict results
                results[field].update(data_item.copy())
            elif isinstance(fielddata, list) or isinstance(fielddata, tuple):
                # add to lists (Cobbler doesn't have many lists)
                # FIXME: should probably uniquify list after doing this
                results[field].extend(data_item)
                results[field] = uniquify(results[field])
            else:
                # distro field gets special handling, since we don't want to overwrite it ever.
                # FIXME: should the parent's field too? It will be overwritten if there are multiple sub-profiles in
                #        the chain of inheritance
                if field != "distro":
                    results[field] = data_item
        else:
            results[field] = data_item

    # Now if we have any "!foo" results in the list, delete corresponding key entry "foo", and also the entry "!foo",
    # allowing for removal of kernel options set in a distro later in a profile, etc.

    dict_removals(results, "kernel_options")
    dict_removals(results, "kernel_options_post")
    dict_removals(results, "autoinstall_meta")
    dict_removals(results, "template_files")
    dict_removals(results, "boot_files")
    dict_removals(results, "fetchable_files")
    return results


def dict_removals(results: dict, subkey: str):
    """
    Remove entries from a dictionary starting with a "!".

    :param results: The dictionary to search in
    :param subkey: The subkey to search through.
    """
    if subkey not in results:
        return
    return dict_annihilate(results[subkey])


def dict_annihilate(dictionary: dict):
    """
    Annihilate entries marked for removal. This method removes all entries with
    key names starting with "!". If a ``dictionary`` contains keys "!xxx" and
    "xxx", then both will be removed.

    :param dictionary: A dictionary to clean up.
    """
    for k in list(dictionary.keys()):
        if str(k).startswith("!") and k != "!":
            rk = k[1:]
            if rk in dictionary:
                del dictionary[rk]
            del dictionary[k]


def dict_to_string(_dict: dict) -> Union[str, dict]:
    """
    Convert a dictionary to a printable string. Used primarily in the kernel options string and for some legacy stuff
    where koan expects strings (though this last part should be changed to dictionaries)

    A KV-Pair is joined with a "=". Values are enclosed in single quotes.

    :param _dict: The dictionary to convert to a string.
    :return: The string which was previously a dictionary.
    """

    buffer = ""
    if not isinstance(_dict, dict):
        return _dict
    for key in _dict:
        value = _dict[key]
        if not value:
            buffer += str(key) + " "
        elif isinstance(value, list):
            # this value is an array, so we print out every
            # key=value
            for item in value:
                # strip possible leading and trailing whitespaces
                _item = str(item).strip()
                if " " in _item:
                    buffer += str(key) + "='" + _item + "' "
                else:
                    buffer += str(key) + "=" + _item + " "
        else:
            _value = str(value).strip()
            if " " in _value:
                buffer += str(key) + "='" + _value + "' "
            else:
                buffer += str(key) + "=" + _value + " "
    return buffer


def rsync_files(src: str, dst: str, args: str, quiet: bool = True) -> bool:
    r"""
    Sync files from src to dst. The extra arguments specified by args are appended to the command.

    :param src: The source for the copy process.
    :param dst: The destination for the copy process.
    :param args: The extra arguments are appended to our standard arguments.
    :param quiet: If ``True`` no progress is reported. If ``False`` then progress will be reported by rsync.
    :return: ``True`` on success, otherwise ``False``.
    """

    if args is None:
        args = ""

    RSYNC_CMD = (
        "rsync -a %%s '%%s' %%s %s --exclude-from=/etc/cobbler/rsync.exclude" % args
    )
    if quiet:
        RSYNC_CMD += " --quiet"
    else:
        RSYNC_CMD += " --progress"

    # Make sure we put a "/" on the end of the source and destination to make sure we don't cause any rsync weirdness.
    if not dst.endswith("/"):
        dst = "%s/" % dst
    if not src.endswith("/"):
        src = "%s/" % src

    spacer = ""
    if not src.startswith("rsync://") and not src.startswith("/"):
        spacer = ' -e "ssh" '

    rsync_cmd = RSYNC_CMD % (spacer, src, dst)
    try:
        res = subprocess_call(rsync_cmd)
        if res != 0:
            die("Failed to run the rsync command: '%s'" % rsync_cmd)
    except:
        return False

    return True


def run_this(cmd: str, args: Union[str, tuple]):
    """
    A simple wrapper around subprocess calls.

    :param cmd: The command to run in a shell process.
    :param args: The arguments to attach to the command.
    """

    my_cmd = cmd % args
    rc = subprocess_call(my_cmd, shell=True)
    if rc != 0:
        die("Command failed")


def run_triggers(api, ref, globber, additional: list = None):
    """Runs all the trigger scripts in a given directory.
    Example: ``/var/lib/cobbler/triggers/blah/*``

    As of Cobbler 1.5.X, this also runs Cobbler modules that match the globbing paths.

    Python triggers are always run before shell triggers.

    :param api: The api object to use for resolving the actions.
    :param ref: Can be a Cobbler object, if not None, the name will be passed to the script. If ref is None, the script
                will be called with no arguments.
    :param globber: is a wildcard expression indicating which triggers to run.
    :param additional: Additional arguments to run the triggers with.
    :raises CX: Raised in case the trigger failed.
    """
    logger.debug("running python triggers from %s", globber)
    modules = api.get_modules_in_category(globber)
    if additional is None:
        additional = []
    for m in modules:
        arglist = []
        if ref:
            arglist.append(ref.name)
        for x in additional:
            arglist.append(x)
        logger.debug("running python trigger %s", m.__name__)
        rc = m.run(api, arglist)
        if rc != 0:
            raise CX("Cobbler trigger failed: %s" % m.__name__)

    # Now do the old shell triggers, which are usually going to be slower, but are easier to write and support any
    # language.

    logger.debug("running shell triggers from %s", globber)
    triggers = glob.glob(globber)
    triggers.sort()
    for file in triggers:
        try:
            if file.startswith(".") or file.find(".rpm") != -1:
                # skip dotfiles or .rpmnew files that may have been installed in the triggers directory
                continue
            arglist = [file]
            if ref:
                arglist.append(ref.name)
            for x in additional:
                if x:
                    arglist.append(x)
            logger.debug("running shell trigger %s", file)
            rc = subprocess_call(arglist, shell=False)  # close_fds=True)
        except:
            logger.warning("failed to execute trigger: %s", file)
            continue

        if rc != 0:
            raise CX(
                "Cobbler trigger failed: %(file)s returns %(code)d"
                % {"file": file, "code": rc}
            )

        logger.debug("shell trigger %s finished successfully", file)

    logger.debug("shell triggers finished successfully")


def get_family() -> str:
    """
    Get family of running operating system.

    Family is the base Linux distribution of a Linux distribution, with a set of common parents.

    :return: May be "redhat", "debian" or "suse" currently. If none of these are detected then just the distro name is
             returned.
    """
    # TODO: Refactor that this is purely reliant on the distro module or obsolete it.
    redhat_list = (
        "red hat",
        "redhat",
        "scientific linux",
        "fedora",
        "centos",
        "virtuozzo",
        "almalinux",
        "rocky linux",
        "anolis os",
        "oracle linux server",
    )

    distro_name = distro.name().lower()
    for item in redhat_list:
        if item in distro_name:
            return "redhat"
    if "debian" in distro_name or "ubuntu" in distro_name:
        return "debian"
    if "suse" in distro.like():
        return "suse"
    return distro_name


def os_release():
    """
    Get the os version of the linux distro. If the get_family() method succeeds then the result is normalized.

    :return: The os-name and os version.
    """
    family = get_family()
    distro_name = distro.name().lower()
    distro_version = distro.version()
    if family == "redhat":
        if "fedora" in distro_name:
            make = "fedora"
        elif "centos" in distro_name:
            make = "centos"
        elif "almalinux" in distro_name:
            make = "centos"
        elif "rocky linux" in distro_name:
            make = "centos"
        elif "anolis os" in distro_name:
            make = "centos"
        elif "virtuozzo" in distro_name:
            make = "virtuozzo"
        elif "oracle linux server" in distro_name:
            make = "centos"
        else:
            make = "redhat"
        return make, float(distro_version)

    elif family == "debian":
        if "debian" in distro_name:
            return "debian", float(distro_version)
        elif "ubuntu" in distro_name:
            return "ubuntu", float(distro_version)

    elif family == "suse":
        make = "suse"
        if "suse" not in distro.like():
            make = "unknown"
        return make, float(distro_version)


def is_selinux_enabled() -> bool:
    """
    This check is achieved via a subprocess call to ``selinuxenabled``. Default return is false.

    :return: Whether selinux is enabled or not.
    """
    if not os.path.exists("/usr/sbin/selinuxenabled"):
        return False
    selinuxenabled = subprocess_call(["/usr/sbin/selinuxenabled"], shell=False)
    if selinuxenabled == 0:
        return True
    else:
        return False


def command_existing(cmd: str) -> bool:
    r"""
    This takes a command which should be known to the system and checks if it is available.

    :param cmd: The executable to check
    :return: If the binary does not exist ``False``, otherwise ``True``.
    """
    # https://stackoverflow.com/a/28909933
    return shutil.which(cmd) is not None


def subprocess_sp(cmd, shell: bool = True, input=None):
    """
    Call a shell process and redirect the output for internal usage.

    :param cmd: The command to execute in a subprocess call.
    :param shell: Whether to use a shell or not for the execution of the command.
    :param input: If there is any input needed for that command to stdin.
    :return: A tuple of the output and the return code.
    """
    logger.info("running: %s", cmd)

    stdin = None
    if input:
        stdin = subprocess.PIPE

    try:
        sp = subprocess.Popen(
            cmd,
            shell=shell,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            close_fds=True,
        )
    except OSError:
        log_exc()
        die("OS Error, command not found?  While running: %s" % cmd)

    (out, err) = sp.communicate(input)
    rc = sp.returncode
    logger.info("received on stdout: %s", out)
    logger.debug("received on stderr: %s", err)
    return out, rc


def subprocess_call(cmd, shell: bool = True, input=None):
    """
    A simple subprocess call with no output capturing.

    :param cmd: The command to execute.
    :param shell: Whether to use a shell or not for the execution of the command.
    :param input: If there is any input needed for that command to stdin.
    :return: The return code of the process
    """
    _, rc = subprocess_sp(cmd, shell=shell, input=input)
    return rc


def subprocess_get(cmd, shell: bool = True, input=None):
    """
    A simple subprocess call with no return code capturing.

    :param cmd: The command to execute.
    :param shell: Whether to use a shell or not for the execution of the command.
    :param input: If there is any input needed for that command to stdin.
    :return: The data which the subprocess returns.
    """
    data, _ = subprocess_sp(cmd, shell=shell, input=input)
    return data


def get_supported_system_boot_loaders() -> List[str]:
    """
    Return the list of currently supported bootloaders.

    :return: The list of currently supported bootloaders.
    """
    return ["grub", "pxe", "ipxe"]


def get_shared_secret() -> Union[str, int]:
    """
    The 'web.ss' file is regenerated each time cobblerd restarts and is used to agree on shared secret interchange
    between the web server and cobblerd, and also the CLI and cobblerd, when username/password access is not required.
    For the CLI, this enables root users to avoid entering username/pass if on the Cobbler server.

    :return: The Cobbler secret which enables full access to Cobbler.
    """

    try:
        with open("/var/lib/cobbler/web.ss", "rb", encoding="utf-8") as fd:
            data = fd.read()
    except:
        return -1
    return str(data).strip()


def local_get_cobbler_api_url() -> str:
    """
    Get the URL of the Cobbler HTTP API from the Cobbler settings file.

    :return: The api entry point. This does not respect modifications from Loadbalancers or API-Gateways.
    """
    # Load server and http port
    # TODO: Replace with Settings access
    data = settings.read_settings_file()

    ip = data.get("server", "127.0.0.1")
    if data.get("client_use_localhost", False):
        # this overrides the server setting
        ip = "127.0.0.1"
    port = data.get("http_port", "80")
    protocol = "http"
    if data.get("client_use_https", False):
        protocol = "https"

    return "%s://%s:%s/cobbler_api" % (protocol, ip, port)


def local_get_cobbler_xmlrpc_url() -> str:
    """
    Get the URL of the Cobbler XMLRPC API from the Cobbler settings file.

    :return: The api entry point.
    """
    # Load xmlrpc port
    data = settings.read_settings_file()
    return "http://%s:%s" % ("127.0.0.1", data.get("xmlrpc_port", "25151"))


def strip_none(data, omit_none: bool = False):
    """
    Remove "None" entries from datastructures. Used prior to communicating with XMLRPC.

    :param data: The data to strip None away.
    :param omit_none: If the datastructure is not a single item then None items will be skipped instead of replaced if
                      set to "True".
    :return: The modified data structure without any occurrence of None.
    """
    if data is None:
        data = "~"

    elif isinstance(data, list):
        data2 = []
        for x in data:
            if omit_none and x is None:
                pass
            else:
                data2.append(strip_none(x))
        return data2

    elif isinstance(data, dict):
        data2 = {}
        for key in list(data.keys()):
            if omit_none and data[key] is None:
                pass
            else:
                data2[str(key)] = strip_none(data[key])
        return data2

    return data


def revert_strip_none(data):
    """
    Does the opposite to strip_none. If a value which represents None is detected, it replaces it with None.

    :param data: The data to check.
    :return: The data without None.
    """
    if isinstance(data, str) and data.strip() == "~":
        return None

    if isinstance(data, list):
        data2 = []
        for x in data:
            data2.append(revert_strip_none(x))
        return data2

    if isinstance(data, dict):
        data2 = {}
        for key in list(data.keys()):
            data2[key] = revert_strip_none(data[key])
        return data2

    return data


def lod_to_dod(_list: list, indexkey) -> dict:
    r"""
    Things like ``get_distros()`` returns a list of a dictionaries. Convert this to a dict of dicts keyed off of an
    arbitrary field.

    Example:  ``[ { "a" : 2 }, { "a" : 3 } ]``  ->  ``{ "2" : { "a" : 2 }, "3" : { "a" : "3" } }``

    :param _list: The list of dictionaries to use for the conversion.
    :param indexkey: The position to use as dictionary keys.
    :return: The converted dictionary. It is not guaranteed that the same key is not used multiple times.
    """
    results = {}
    for item in _list:
        results[item[indexkey]] = item
    return results


def lod_sort_by_key(list_to_sort: list, indexkey) -> list:
    """
    Sorts a list of dictionaries by a given key in the dictionaries.

    Note: This is a destructive operation and does not sort the dictionaries.

    :param list_to_sort: The list of dictionaries to sort.
    :param indexkey: The key to index to dicts in the list.
    :return: The sorted list.
    """
    return sorted(list_to_sort, key=lambda k: k[indexkey])


def dhcpconf_location(protocol: enums.DHCP, filename: str = "dhcpd.conf") -> str:
    """
    This method returns the location of the dhcpd.conf file.

    :param protocol: The DHCP protocol version (v4/v6) that is used.
    :param filename: The filename of the DHCP configuration file.
    :raises AttributeError: If the protocol is not v4/v6.
    :return: The path possibly used for the dhcpd.conf file.
    """
    if protocol not in enums.DHCP:
        logger.info(
            "DHCP configuration location could not be determined due to unknown protocol version."
        )
        raise AttributeError("DHCP must be version 4 or 6!")
    if protocol == enums.DHCP.V6 and filename == "dhcpd.conf":
        filename = "dhcpd6.conf"
    (dist, version) = os_release()
    if (
        (dist in ("redhat", "centos") and version < 6)
        or (dist == "fedora" and version < 11)
        or (dist == "suse")
    ):
        return os.path.join("/etc", filename)
    elif (dist == "debian" and int(version) < 6) or (
        dist == "ubuntu" and version < 11.10
    ):
        return os.path.join("/etc/dhcp3", filename)
    else:
        return os.path.join("/etc/dhcp/", filename)


def namedconf_location() -> str:
    """
    This returns the location of the named.conf file.

    :return: If the distro is Debian/Ubuntu then this returns "/etc/bind/named.conf". Otherwise "/etc/named.conf"
    """
    (dist, _) = os_release()
    if dist == "debian" or dist == "ubuntu":
        return "/etc/bind/named.conf"
    else:
        return "/etc/named.conf"


def dhcp_service_name() -> str:
    """
    Determine the dhcp service which is different on various distros. This is currently a hardcoded detection.

    :return: This will return one of the following names: "dhcp3-server", "isc-dhcp-server", "dhcpd"
    """
    (dist, version) = os_release()
    if dist == "debian" and int(version) < 6:
        return "dhcp3-server"
    elif dist == "debian" and int(version) >= 6:
        return "isc-dhcp-server"
    elif dist == "ubuntu" and version < 11.10:
        return "dhcp3-server"
    elif dist == "ubuntu" and version >= 11.10:
        return "isc-dhcp-server"
    else:
        return "dhcpd"


def named_service_name() -> str:
    """
    Determine the named service which is normally different on various distros.

    :return: This will return for debian/ubuntu bind9 and on other distros named-chroot or named.
    """
    (dist, _) = os_release()
    if dist == "debian" or dist == "ubuntu":
        return "bind9"
    else:
        if process_management.is_systemd():
            rc = subprocess_call(
                ["/usr/bin/systemctl", "is-active", "named-chroot"], shell=False
            )
            if rc == 0:
                return "named-chroot"
        return "named"


def compare_versions_gt(ver1: str, ver2: str) -> bool:
    """
    Compares versions like "0.9.3" with each other and decides if ver1 is greater than ver2.

    :param ver1: The first version.
    :param ver2: The second version.
    :return: True if ver1 is greater, otherwise False.
    """

    def versiontuple(v):
        return tuple(map(int, (v.split("."))))

    return versiontuple(ver1) > versiontuple(ver2)


def kopts_overwrite(
    kopts: dict,
    cobbler_server_hostname: str = "",
    distro_breed: str = "",
    system_name: str = "",
):
    """
    SUSE is not using 'text'. Instead 'textmode' is used as kernel option.

    :param kopts: The kopts of the system.
    :param cobbler_server_hostname: The server setting from our Settings.
    :param distro_breed: The distro for the system to change to kopts for.
    :param system_name: The system to overwrite the kopts for.
    """
    # Type checks
    if not isinstance(kopts, dict):
        raise TypeError("kopts needs to be of type dict")
    if not isinstance(cobbler_server_hostname, str):
        raise TypeError("cobbler_server_hostname needs to be of type str")
    if not isinstance(distro_breed, str):
        raise TypeError("distro_breed needs to be of type str")
    if not isinstance(system_name, str):
        raise TypeError("system_name needs to be of type str")
    # Function logic
    if distro_breed == "suse":
        if "textmode" in list(kopts.keys()):
            kopts.pop("text", None)
        elif "text" in list(kopts.keys()):
            kopts.pop("text", None)
            kopts["textmode"] = ["1"]
        if system_name and cobbler_server_hostname:
            # only works if pxe_just_once is enabled in global settings
            kopts["info"] = "http://%s/cblr/svc/op/nopxe/system/%s" % (
                cobbler_server_hostname,
                system_name,
            )


def is_str_int(value: str) -> bool:
    """
    Checks if the string value could be converted into an integer.
    This is necessary since the CLI only works with strings but many methods and checks expects an integer.

    :param value: The value to check
    :return: True if conversion is successful
    """
    if not isinstance(value, str):
        raise TypeError("value needs to be of type string")
    try:
        converted = int(value)
        return str(converted) == value
    except ValueError:
        pass
    return False


def is_str_float(value: str) -> bool:
    """
    Checks if the string value could be converted into a float.
    This is necessary since the CLI only works with strings but many methods and checks expects a float.

    :param value: The value to check
    :return: True if conversion is successful
    """
    if not isinstance(value, str):
        raise TypeError("value needs to be of type string")
    if is_str_int(value):
        return True
    try:
        converted = float(value)
        return str(converted) == value
    except ValueError:
        pass
    return False
