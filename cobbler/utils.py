"""
Misc heavy lifting functions for Cobbler

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

from past.builtins import cmp
from future import standard_library
from functools import reduce
standard_library.install_aliases()
from builtins import map
from builtins import str
from past.utils import old_div
from builtins import object
import copy
import errno
import glob
import netaddr
import os
import random
import re
import shlex
import shutil
import simplejson
import subprocess
import sys
import traceback
import urllib.request
import urllib.error
import urllib.parse
import yaml
import distro

from cobbler.cexceptions import FileNotFoundException, CX
from cobbler import clogger
from cobbler import field_info
from cobbler import validate


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


# placeholder for translation
def _(foo):
    return foo


MODULE_CACHE = {}
SIGNATURE_CACHE = {}

_re_kernel = re.compile(r'(vmlinu[xz]|kernel.img)')
_re_initrd = re.compile(r'(initrd(.*).img|ramdisk.image.gz)')
_re_is_mac = re.compile(':'.join(('[0-9A-Fa-f][0-9A-Fa-f]',) * 6) + '$')
_re_is_ibmac = re.compile(':'.join(('[0-9A-Fa-f][0-9A-Fa-f]',) * 20) + '$')

# all logging from utils.die goes to the main log even if there
# is another log.
main_logger = None  # the logger will be lazy loaded later


def die(logger, msg):
    """
    This method let's Cobbler crash with an exception. Log the exception once in the per-task log or the main log if
    this is not a background op.

    :param logger:
    :param msg:
    """
    global main_logger
    if main_logger is None:
        main_logger = clogger.Logger()

    # log the exception once in the per-task log or the main log if this is not a background op.
    try:
        raise CX(msg)
    except:
        if logger is not None:
            log_exc(logger)
        else:
            log_exc(main_logger)

    # now re-raise it so the error can fail the operation
    raise CX(msg)


def log_exc(logger):
    """
    Log an exception.

    :param logger: The logger to audit all action.
    """
    (t, v, tb) = sys.exc_info()
    logger.info("Exception occured: %s" % t)
    logger.info("Exception value: %s" % v)
    logger.info("Exception Info:\n%s" % "\n".join(traceback.format_list(traceback.extract_tb(tb))))


def get_exc(exc, full=True):
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


def cheetah_exc(exc, full=False):
    """
    Converts an exception thrown by Cheetah3 into a custom error message.

    :param exc: The exception to convert.
    :param full: Unused parameter. May be removed in the future.
    :return: The string representation of the Cheetah3 exception.
    :rtype: str
    """
    lines = get_exc(exc).split("\n")
    buf = ""
    for line in lines:
        buf += "# %s\n" % line
    return CHEETAH_ERROR_DISCLAIMER + buf


def pretty_hex(ip, length=8):
    """
    Pads an IP object with leading zeroes so that the result is _length_ hex digits.  Also do an upper().

    :param ip: The IP address to pretty print.
    :param length: The length of the resulting hexstring. If the number is smaller than the resulting hex-string
                   then no front-padding is done.
    :rtype: str
    """
    hexval = "%x" % ip.value
    if len(hexval) < length:
        hexval = '0' * (length - len(hexval)) + hexval
    return hexval.upper()


def get_host_ip(ip, shorten=True):
    """
    Return the IP encoding needed for the TFTP boot tree.

    :param ip: The IP address to pretty print.
    :param shorten: Whether the IP-Address should be shortened or not.
    :rtype: str
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
            cutoff = old_div((32 - cidr.prefixlen), 4)
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


def is_ip(strdata):
    """
    Return whether the argument is an IP address.

    :param strdata: The IP in a string format. This get's passed to the IP object of Python.
    :type strdata: str
    :rtype: bool
    """
    try:
        _IP(strdata)
    except:
        return False
    return True


def is_mac(strdata):
    """
    Return whether the argument is a mac address.

    :rtype: bool
    """
    if strdata is None:
        return False
    return bool(_re_is_mac.match(strdata) or _re_is_ibmac.match(strdata))


def is_systemd():
    """
    Return whether or not this system uses systemd.

    This method currently checks if the path /usr/lib/systemd/systemd exists.

    :rtype: bool
    """
    if os.path.exists("/usr/lib/systemd/systemd"):
        return True
    return False


def get_random_mac(api_handle, virt_type="xenpv"):
    """
    Generate a random MAC address.

    The code of this method was taken from xend/server/netif.py

    :param api_handle: The main Cobbler api instance.
    :param virt_type: The virtualization provider. Currently possible is 'vmware', 'xen', 'qemu', 'kvm'.
    :returns: MAC address string
    :rtype: str
    """
    if virt_type.startswith("vmware"):
        mac = [
            0x00, 0x50, 0x56,
            random.randint(0x00, 0x3f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)
        ]
    elif virt_type.startswith("xen") or virt_type.startswith("qemu") or virt_type.startswith("kvm"):
        mac = [
            0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)
        ]
    else:
        raise CX("virt mac assignment not yet supported")

    mac = ':'.join(["%02x" % x for x in mac])
    systems = api_handle.systems()
    while (systems.find(mac_address=mac)):
        mac = get_random_mac(api_handle)

    return mac


def find_matching_files(directory, regex):
    """
    Find all files in a given directory that match a given regex. Can't use glob directly as glob doesn't take regexen.
    The search does not include subdirectories.

    :param directory: The directory to search in.
    :param regex: The regex to apply to the found files.
    :return: An array of files which apply to the regex.
    :rtype: list
    """
    files = glob.glob(os.path.join(directory, "*"))
    results = []
    for f in files:
        if regex.match(os.path.basename(f)):
            results.append(f)
    return results


def find_highest_files(directory, unversioned, regex):
    """
    Find the highest numbered file (kernel or initrd numbering scheme) in a given directory that matches a given
    pattern. Used for auto-booting the latest kernel in a directory.

    :param directory: The directory to search in.
    :param unversioned: The base filename which also acts as a last resort if no numbered files are found.
    :param regex: The regex to search for.
    :return: None or the file with the highest number.
    """
    files = find_matching_files(directory, regex)
    get_numbers = re.compile(r'(\d+).(\d+).(\d+)')

    def max2(a, b):
        """Returns the larger of the two values"""
        av = get_numbers.search(os.path.basename(a)).groups()
        bv = get_numbers.search(os.path.basename(b)).groups()

        ret = cmp(av[0], bv[0]) or cmp(av[1], bv[1]) or cmp(av[2], bv[2])
        if ret < 0:
            return b
        return a

    if len(files) > 0:
        return reduce(max2, files)

    # Couldn't find a highest numbered file, but maybe there is just a 'vmlinuz' or an 'initrd.img' in this directory?
    last_chance = os.path.join(directory, unversioned)
    if os.path.exists(last_chance):
        return last_chance
    return None


def find_kernel(path):
    """
    Given a directory or a filename, find if the path can be made to resolve into a kernel, and return that full path if
    possible.

    :param path: The path to check for a kernel.
    :return: None or the path with the kernel.
    """
    if path is None:
        return None

    if os.path.isfile(path):
        # filename = os.path.basename(path)
        # if _re_kernel.match(filename):
        #   return path
        # elif filename == "vmlinuz":
        #   return path
        return path

    elif os.path.isdir(path):
        return find_highest_files(path, "vmlinuz", _re_kernel)

    # For remote URLs we expect an absolute path, and will not do any searching for the latest:
    elif file_is_remote(path) and remote_file_exists(path):
        return path

    return None


def remove_yum_olddata(path, logger=None):
    """
    Delete .olddata files that might be present from a failed run of createrepo.
    # FIXME: verify this is still being used

    :param path: The path to check for .olddata files.
    :param logger: The logger to audit this action with.
    """
    trythese = [
        ".olddata",
        ".repodata/.olddata",
        "repodata/.oldata",
        "repodata/repodata"
    ]
    for pathseg in trythese:
        olddata = os.path.join(path, pathseg)
        if os.path.exists(olddata):
            if logger is not None:
                logger.info("removing: %s" % olddata)
            shutil.rmtree(olddata, ignore_errors=False, onerror=None)


def find_initrd(path):
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
        # if _re_initrd.match(filename):
        #   return path
        # if filename == "initrd.img" or filename == "initrd":
        #   return path
        return path

    elif os.path.isdir(path):
        return find_highest_files(path, "initrd.img", _re_initrd)

    # For remote URLs we expect an absolute path, and will not
    # do any searching for the latest:
    elif file_is_remote(path) and remote_file_exists(path):
        return path

    return None


def read_file_contents(file_location, logger=None, fetch_if_remote=False):
    """
    Reads the contents of a file, which could be referenced locally or as a URI.

    :param file_location: The location of the file to read.
    :param logger: The logger to autdit this action with.
    :param fetch_if_remote: If True a remote file will be tried to read, otherwise remote files are skipped and None is
                            returned.
    :return: Returns None if file is remote and templating of remote files is disabled.
    :rtype: str or None
    :raises FileNotFoundException: if the file does not exist at the specified location.
    """

    # Local files:
    if file_location.startswith("/"):

        if not os.path.exists(file_location):
            if logger:
                logger.warning("File does not exist: %s" % file_location)
            raise FileNotFoundException("%s: %s" % (_("File not found"), file_location))

        try:
            f = open(file_location)
            data = f.read()
            f.close()
            return data
        except:
            if logger:
                log_exc(logger)
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
            if logger:
                logger.warning("File does not exist: %s" % file_location)
            raise FileNotFoundException("%s: %s" % (_("File not found"), file_location))


def remote_file_exists(file_url):
    """
    Return True if the remote file exists.

    :param file_url: The URL to check.
    :return: True if Cobbler can reach the specified URL, otherwise false.
    :rtype: bool
    """
    try:
        handler = urllib.request.urlopen(file_url)
        handler.close()
        return True
    except urllib.error.HTTPError:
        # File likely doesn't exist
        return False


def file_is_remote(file_location):
    """
    Returns true if the file is remote and referenced via a protocol we support.

    :param file_location: The URI to check.
    :return: True if the URI is http, https or ftp. Otherwise false.
    :rtype: bool
    """
    file_loc_lc = file_location.lower()
    # Check for urllib2 supported protocols
    for prefix in ["http://", "https://", "ftp://"]:
        if file_loc_lc.startswith(prefix):
            return True
    return False


def input_string_or_list(options):
    """
    Accepts a delimited list of stuff or a list, but always returns a list.

    :param options: The object to split into a list.
    :return: str when this functions get's passed <<inherit>>. if option is delete then an empty list is returned.
             Otherwise this function tries to return the arg option or tries to split it into a list.
    :rtype: list or str
    """
    if options == "<<inherit>>":
        return "<<inherit>>"
    if not options or options == "delete":
        return []
    elif isinstance(options, list):
        return options
    elif isinstance(options, str):
        tokens = shlex.split(options)
        return tokens
    else:
        raise CX(_("invalid input type"))


def input_string_or_dict(options, allow_multiples=True):
    """
    Older Cobbler files stored configurations in a flat way, such that all values for strings. Newer versions of Cobbler
    allow dictionaries. This function is used to allow loading of older value formats so new users of Cobbler aren't
    broken in an upgrade.

    :param options: The str or dict to convert.
    :param allow_multiples: True (default) to allow multiple identical keys, otherwise set this false explicitly.
    :return: A tuple of True and a dict.
    """

    if options == "<<inherit>>":
        options = {}

    if options is None or options == "delete":
        return (True, {})
    elif isinstance(options, list):
        raise CX(_("No idea what to do with list: %s") % options)
    elif isinstance(options, str):
        new_dict = {}
        tokens = shlex.split(options)
        for t in tokens:
            tokens2 = t.split("=", 1)
            if len(tokens2) == 1:
                # this is a singleton option, no value
                key = tokens2[0]
                value = None
            else:
                key = tokens2[0]
                value = tokens2[1]

            # If we're allowing multiple values for the same key, check to see if this token has already been inserted
            # into the dictionary of values already.

            if key in list(new_dict.keys()) and allow_multiples:
                # If so, check to see if there is already a list of values otherwise convert the dictionary value to an
                # array, and add the new value to the end of the list.
                if isinstance(new_dict[key], list):
                    new_dict[key].append(value)
                else:
                    new_dict[key] = [new_dict[key], value]
            else:
                new_dict[key] = value
        # make sure we have no empty entries
        new_dict.pop('', None)
        return (True, new_dict)
    elif isinstance(options, dict):
        options.pop('', None)
        return (True, options)
    else:
        raise CX(_("invalid input type"))


def input_boolean(value):
    """
    Convert a str to a boolean. If this is not possible or the value is false return false.

    :param value: The value to convert to boolean.
    :type value: str
    :return: True if the value is in the following list, otherwise false: "true", "1", "on", "yes", "y" .
    :rtype: bool
    """
    value = str(value)
    if value.lower() in ["true", "1", "on", "yes", "y"]:
        return True
    else:
        return False


def update_settings_file(data):
    """
    Write data handed to this function into the settings file of Cobbler. This function overwrites the existing content.

    :param data: The data to put into the settings file.
    :return: True if the action succeeded. Otherwise return nothing.
    :rtype: bool
    """
    if 1:
        # clogger.Logger().debug("in update_settings_file(): value is: %s" % str(value))
        settings_file = open("/etc/cobbler/settings", "w")
        yaml.safe_dump(data, settings_file)
        settings_file.close()
        return True
    # except:
    #    return False


def grab_tree(api_handle, item):
    """
    Climb the tree and get every node.

    :param api_handle: The api to use for checking the tree.
    :param item: The item to check for parents
    :return: The list of items with all parents from that object upwards the tree. Contains at least the item itself.
    :rtype: list
    """
    settings = api_handle.settings()
    results = [item]
    parent = item.get_parent()
    while parent is not None:
        results.append(parent)
        parent = parent.get_parent()
    results.append(settings)
    return results


def blender(api_handle, remove_dicts, root_obj):
    """
    Combine all of the data in an object tree from the perspective of that point on the tree, and produce a merged
    dictionary containing consolidated data.

    :param api_handle: The api to use for collecting the information to blender the item.
    :param remove_dicts: Boolean to decide whether dicts should be converted.
    :param root_obj: The object which should act as the root-node object.
    :return: A dictionary with all the information from the root node downwards.
    """

    tree = grab_tree(api_handle, root_obj)
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node, results)

    # Make interfaces accessible without Cheetah-voodoo in the templates
    # EXAMPLE: $ip == $ip0, $ip1, $ip2 and so on.

    if root_obj.COLLECTION_TYPE == "system":
        for (name, interface) in list(root_obj.interfaces.items()):
            for key in list(interface.keys()):
                results["%s_%s" % (key, name)] = interface[key]

    # If the root object is a profile or system, add in all repo data for repos that belong to the object chain
    if root_obj.COLLECTION_TYPE in ("profile", "system"):
        repo_data = []
        for r in results.get("repos", []):
            repo = api_handle.find_repo(name=r)
            if repo:
                repo_data.append(repo.to_dict())
        # FIXME: sort the repos in the array based on the repo priority field so that lower priority repos come first in
        #  the array
        results["repo_data"] = repo_data

    http_port = results.get("http_port", 80)
    if http_port not in (80, "80"):
        results["http_server"] = "%s:%s" % (results["server"], http_port)
    else:
        results["http_server"] = results["server"]

    mgmt_parameters = results.get("mgmt_parameters", {})
    mgmt_parameters.update(results.get("autoinstall_meta", {}))
    results["mgmt_parameters"] = mgmt_parameters

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


def flatten(data):
    """
    Convert certain nested dicts to strings. This is only really done for the ones koan needs as strings this should
    not be done for everything

    :param data: The dictionary in which various keys should be converted into a string.
    :rtype: dict
    :return: None (if data is None) or the flattened string.
    :rtype: None or dict
    """

    if data is None:
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


def uniquify(seq):
    """
    Remove duplicates from the sequence handed over in the args.

    :param seq: The sequence to check for duplicates.
    :return: The list without duplicates.
    :rtype: list
    """

    # Credit: http://www.peterbe.com/plog/uniqifiers-benchmark
    # FIXME: if this is actually slower than some other way, overhaul it
    seen = {}
    result = []
    for item in seq:
        if item in seen:
            continue
        seen[item] = 1
        result.append(item)
    return result


def __consolidate(node, results):
    """
    Merge data from a given node with the aggregate of all data from past scanned nodes. Dictionaries and arrays are
    treated specially.

    :param node: The object to merge data into. The data from the node always wins.
    :param results: Merged data as dictionary
    """
    node_data = node.to_dict()

    # If the node has any data items labelled <<inherit>> we need to expunge them. So that they do not override the
    # supernodes.
    node_data_copy = {}
    for key in node_data:
        value = node_data[key]
        if value != "<<inherit>>":
            if isinstance(value, dict):
                node_data_copy[key] = value.copy()
            elif isinstance(value, list):
                node_data_copy[key] = value[:]
            else:
                node_data_copy[key] = value

    for field in node_data_copy:

        data_item = node_data_copy[field]
        if field in results:
            # Now merge data types seperately depending on whether they are dict, list, or scalar.
            fielddata = results[field]

            if isinstance(fielddata, dict):
                # interweave dict results
                results[field].update(data_item.copy())
            elif isinstance(fielddata, list) or isinstance(fielddata, tuple):
                # add to lists (Cobbler doesn't have many lists)
                # FIXME: should probably uniqueify list after doing this
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


def dict_removals(results, subkey):
    """
    Remove entrys from a dictionary starting with a "!".

    :param results: The dictionary to search in
    :param subkey: The subkey to search through.
    """
    if subkey not in results:
        return
    scan = list(results[subkey].keys())
    for k in scan:
        if str(k).startswith("!") and k != "!":
            remove_me = k[1:]
            if remove_me in results[subkey]:
                del results[subkey][remove_me]
            del results[subkey][k]


def dict_to_string(_dict):
    """
    Convert a dictionary to a printable string. Used primarily in the kernel options string and for some legacy stuff
    where koan expects strings (though this last part should be changed to dictionaries)

    A KV-Pair is joined with a "=". Values are enclosed in single quotes.

    :param _dict: The dictionary to convert to a string.
    :return: The string which was previously a dictionary.
    :rtype: str
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
                if ' ' in _item:
                    buffer += str(key) + "='" + _item + "' "
                else:
                    buffer += str(key) + "=" + _item + " "
        else:
            _value = str(value).strip()
            if ' ' in _value:
                buffer += str(key) + "='" + _value + "' "
            else:
                buffer += str(key) + "=" + _value + " "
    return buffer


def rsync_files(src, dst, args, logger=None, quiet=True):
    """
    Sync files from src to dst. The extra arguments specified by args are appended to the command.

    :param src: The source for the copy process.
    :param dst: The destination for the copy process.
    :param args: The extra arguments are appended to our standard arguements.
    :param logger: The logger to audit the action with.
    :param quiet: If "True" no progress is reported. If "False" then progress will be reported by rsync.
    :type quiet: bool
    :return: ``True`` on success, otherwise ``False``.
    """

    if args is None:
        args = ''

    RSYNC_CMD = "rsync -a %%s '%%s' %%s %s --exclude-from=/etc/cobbler/rsync.exclude" % args
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
        res = subprocess_call(logger, rsync_cmd)
        if res != 0:
            die(logger, "Failed to run the rsync command: '%s'" % rsync_cmd)
    except:
        return False

    return True


def run_this(cmd, args, logger):
    """
    A simple wrapper around subprocess calls.

    :param cmd: The command to run in a shell process.
    :param args: The arguments to attach to the command.
    :param logger: The logger to audit the shell call with.
    """

    my_cmd = cmd % args
    rc = subprocess_call(logger, my_cmd, shell=True)
    if rc != 0:
        die(logger, "Command failed")


def run_triggers(api, ref, globber, additional=[], logger=None):
    """Runs all the trigger scripts in a given directory.
    Example: ``/var/lib/cobbler/triggers/blah/*``

    As of Cobbler 1.5.X, this also runs Cobbler modules that match the globbing paths.

    Python triggers are always run before shell triggers.

    :param api: The api object to use for resolving the actions.
    :param ref: Can be a Cobbler object, if not None, the name will be passed to the script. If ref is None, the script
                will be called with no argumenets.
    :param globber: is a wildcard expression indicating which triggers to run.
    :param additional: Additional arguments to run the triggers with.
    :type additional: list
    :param logger: The logger to audit the action with.
    """

    if logger is not None:
        logger.debug("running python triggers from %s" % globber)
    modules = api.get_modules_in_category(globber)
    for m in modules:
        arglist = []
        if ref:
            arglist.append(ref.name)
        for x in additional:

            arglist.append(x)
        if logger is not None:
            logger.debug("running python trigger %s" % m.__name__)
        rc = m.run(api, arglist, logger)
        if rc != 0:
            raise CX("Cobbler trigger failed: %s" % m.__name__)

    # Now do the old shell triggers, which are usually going to be slower, but are easier to write and support any
    # language.

    if logger is not None:
        logger.debug("running shell triggers from %s" % globber)
    triggers = glob.glob(globber)
    triggers.sort()
    for file in triggers:
        try:
            if file.startswith(".") or file.find(".rpm") != -1:
                # skip dotfiles or .rpmnew files that may have been installed
                # in the triggers directory
                continue
            arglist = [file]
            if ref:
                arglist.append(ref.name)
            for x in additional:
                if x:
                    arglist.append(x)
            if logger is not None:
                logger.debug("running shell trigger %s" % file)
            rc = subprocess_call(logger, arglist, shell=False)  # close_fds=True)
        except:
            if logger is not None:
                logger.warning("failed to execute trigger: %s" % file)
            continue

        if rc != 0:
            raise CX(_("Cobbler trigger failed: %(file)s returns %(code)d") % {"file": file, "code": rc})

        if logger is not None:
            logger.debug("shell trigger %s finished successfully" % file)

    if logger is not None:
        logger.debug("shell triggers finished successfully")


def get_family():
    """
    Get family of running operating system.

    Family is the base Linux distribution of a Linux distribution, with a set of common parents.

    :return: May be "redhat", "debian" or "suse" currently. If none of these are detected then just the distro name is
             returned.
    :rtype: str
    """

    redhat_list = ("red hat", "redhat", "scientific linux", "fedora", "centos", "virtuozzo")

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
        elif "virtuozzo" in distro_name:
            make = "virtuozzo"
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


def is_safe_to_hardlink(src, dst, api):
    """
    Determine if it is safe to hardlink a file to the destination path.

    :param src: The hardlink source path.
    :param dst: The hardlink target path.
    :param api: The api-instance to resolve needed information with.
    :return: True if selinux is disabled, the file is on the same device, the source in not a link, and it is not a
             remote path. If selinux is enabled the functions still may return true if the object is a kernel or initrd.
             Otherwise returns False.
    :rtype: bool
    """
    (dev1, path1) = get_file_device_path(src)
    (dev2, path2) = get_file_device_path(dst)
    if dev1 != dev2:
        return False
    # do not hardlink to a symbolic link; chances are high the new link will be dangling
    if os.path.islink(src):
        return False
    if dev1.find(":") != -1:
        # is remoted
        return False
    # note: this is very Cobbler implementation specific!
    if not api.is_selinux_enabled():
        return True
    if _re_initrd.match(os.path.basename(path1)):
        return True
    if _re_kernel.match(os.path.basename(path1)):
        return True
    # we're dealing with SELinux and files that are not safe to chcon
    return False


def hashfile(fn, lcache=None, logger=None):
    """
    Returns the sha1sum of the file

    :param fn: The file to get the sha1sum of.
    :param lcache: Not known what this is exactly for.
    :param logger: The logger to audit the action with.
    :return: The sha1 sum or None if the file doesn't exist.
    """
    db = {}
    try:
        dbfile = os.path.join(lcache, 'link_cache.json')
        if os.path.exists(dbfile):
            db = simplejson.load(open(dbfile, 'r'))
    except:
        pass

    mtime = os.stat(fn).st_mtime
    if fn in db:
        if db[fn][0] >= mtime:
            return db[fn][1]

    if os.path.exists(fn):
        cmd = '/usr/bin/sha1sum %s' % fn
        key = subprocess_get(logger, cmd).split(' ')[0]
        if lcache is not None:
            db[fn] = (mtime, key)
            simplejson.dump(db, open(dbfile, 'w'))
        return key
    else:
        return None


def cachefile(src, dst, api=None, logger=None):
    """
    Copy a file into a cache and link it into place. Use this with caution, otherwise you could end up copying data
    twice if the cache is not on the same device as the destination.

    :param src: The sourcefile for the copy action.
    :param dst: The destination for the copy action.
    :param api: The api to resolve basic information with.
    :param logger: The logger to audit the action with.
    """
    lcache = os.path.join(os.path.dirname(os.path.dirname(dst)), '.link_cache')
    if not os.path.isdir(lcache):
        os.mkdir(lcache)
    key = hashfile(src, lcache=lcache, logger=logger)
    cachefile = os.path.join(lcache, key)
    if not os.path.exists(cachefile):
        logger.info("trying to create cache file %s" % cachefile)
        copyfile(src, cachefile, api=api, logger=logger)

    logger.debug("trying cachelink %s -> %s -> %s" % (src, cachefile, dst))
    os.link(cachefile, dst)


def linkfile(src, dst, symlink_ok=False, cache=True, api=None, logger=None):
    """
    Attempt to create a link dst that points to src. Because file systems suck we attempt several different methods or
    bail to just copying the file.

    :param src: The source file.
    :param dst: The destination for the link.
    :param symlink_ok: If it is okay to just use a symbolic link.
    :type symlink_ok: bool
    :param cache: If it is okay to use a cached file instead of the real one.
    :type cache: bool
    :param api: This parameter is needed to check if a file can be hardlinked. This method fails if this parameter is
                not present.
    :param logger: If a logger instance is present, then it is used to audit what this method is doing to the
                   filesystem.
    """

    if api is None:
        # FIXME: this really should not be a keyword arg
        raise CX("Internal error: API handle is required")

    if os.path.exists(dst):
        # if the destination exists, is it right in terms of accuracy and context?
        if os.path.samefile(src, dst):
            if not is_safe_to_hardlink(src, dst, api):
                # may have to remove old hardlinks for SELinux reasons
                # as previous implementations were not complete
                if logger is not None:
                    logger.info("removing: %s" % dst)
                os.remove(dst)
            else:
                return
        elif os.path.islink(dst):
            # existing path exists and is a symlink, update the symlink
            if logger is not None:
                logger.info("removing: %s" % dst)
            os.remove(dst)

    if is_safe_to_hardlink(src, dst, api):
        # we can try a hardlink if the destination isn't to NFS or Samba this will help save space and sync time.
        try:
            if logger is not None:
                logger.info("trying hardlink %s -> %s" % (src, dst))
            os.link(src, dst)
            return
        except (IOError, OSError):
            # hardlink across devices, or link already exists we'll just symlink it if we can or otherwise copy it
            pass

    if symlink_ok:
        # we can symlink anywhere except for /tftpboot because that is run chroot, so if we can symlink now, try it.
        try:
            if logger is not None:
                logger.info("trying symlink %s -> %s" % (src, dst))
            os.symlink(src, dst)
            return
        except (IOError, OSError):
            pass

    if cache:
        try:
            cachefile(src, dst, api=api, logger=logger)
            return
        except (IOError, OSError):
            pass

    # we couldn't hardlink and we couldn't symlink so we must copy
    copyfile(src, dst, api=api, logger=logger)


def copyfile(src, dst, api=None, logger=None):
    """
    Copy a file from source to the destination.

    :param src: The source file. This may also be a folder.
    :param dst: The destination for the file or folder.
    :param api: This parameter is not used currently.
    :param logger: The logger to audit the action with.
    """
    try:
        if logger is not None:
            logger.info("copying: %s -> %s" % (src, dst))
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)
    except:
        if not os.access(src, os.R_OK):
            raise CX(_("Cannot read: %s") % src)
        if os.path.samefile(src, dst):
            # accomodate for the possibility that we already copied
            # the file as a symlink/hardlink
            raise
            # traceback.print_exc()
            # raise CX(_("Error copying %(src)s to %(dst)s") % { "src" : src, "dst" : dst})


def copyremotefile(src, dst1, api=None, logger=None):
    """
    Copys a file from a remote place to the local destionation.

    :param src: The remote file URI.
    :param dst1: The copy destination on the local filesystem.
    :param api: This parameter is not used currently.
    :param logger: The logger to audit the action with.
    """
    try:
        if logger is not None:
            logger.info("copying: %s -> %s" % (src, dst1))
        srcfile = urllib.request.urlopen(src)
        output = open(dst1, 'wb')
        output.write(srcfile.read())
        output.close()
    except Exception as e:
        raise CX(_("Error while getting remote file (%s -> %s):\n%s" % (src, dst1, e)))


def copyfile_pattern(pattern, dst, require_match=True, symlink_ok=False, cache=True, api=None, logger=None):
    """
    Copy 1 or more files with a pattern into a destination.

    :param pattern: The pattern for finding the required files.
    :param dst: The destination for the file(s) found.
    :param require_match: If the glob pattern does not find files should an error message be thrown or not.
    :type require_match: bool
    :param symlink_ok: If it is okay to just use a symlink to link the file to the destination.
    :type symlink_ok: bool
    :param cache: If it is okay to use a file from the cache (which could be possibly newer) or not.
    :type cache: bool
    :param api:
    :param logger: The logger to audit the action with.
    """
    files = glob.glob(pattern)
    if require_match and not len(files) > 0:
        raise CX(_("Could not find files matching %s") % pattern)
    for file in files:
        dst1 = os.path.join(dst, os.path.basename(file))
        linkfile(file, dst1, symlink_ok=symlink_ok, cache=cache, api=api, logger=logger)


def rmfile(path, logger=None):
    """
    Delete a single file.

    :param path: The file to delete.
    :param logger: The logger to audit the action with.
    :return: True if the action succeeded.
    :rtype: bool
    """
    try:
        if logger is not None:
            logger.info("removing: %s" % path)
        os.unlink(path)
        return True
    except OSError as ioe:
        # doesn't exist
        if not ioe.errno == errno.ENOENT:
            if logger is not None:
                log_exc(logger)
            raise CX(_("Error deleting %s") % path)
        return True


def rmtree_contents(path, logger=None):
    """
    Delete the content of a folder with a glob pattern.

    :param path: This parameter presents the glob pattern of what should be deleted.
    :param logger: The logger to audit the action with.
    """
    what_to_delete = glob.glob("%s/*" % path)
    for x in what_to_delete:
        rmtree(x, logger=logger)


def rmtree(path, logger=None):
    """
    Delete a complete directory or just a single file.

    :param path: The directory or folder to delete.
    :param logger: The logger to audit the action with.
    :return: May possibly return true on success or may return None on success.
    """
    try:
        if os.path.isfile(path):
            return rmfile(path, logger=logger)
        else:
            if logger is not None:
                logger.info("removing: %s" % path)
            return shutil.rmtree(path, ignore_errors=True)
    except OSError as ioe:
        if logger is not None:
            log_exc(logger)
        if not ioe.errno == errno.ENOENT:   # doesn't exist
            raise CX(_("Error deleting %s") % path)
        return True


def mkdir(path, mode=0o755, logger=None):
    """
    Create directory with a given mode.

    :param path: The path to create the directory at.
    :param mode: The mode to create the directory with.
    :param logger: The logger to audit the action with.
    """
    try:
        if logger is not None:
            logger.info("mkdir: %s" % path)
        return os.makedirs(path, mode)
    except OSError as oe:
        # already exists (no constant for 17?)
        if not oe.errno == 17:
            if logger is not None:
                log_exc(logger)
            raise CX(_("Error creating %s") % path)


def path_tail(apath, bpath):
    """
    Given two paths (B is longer than A), find the part in B not in A

    :param apath: The first path.
    :param bpath: The second path.
    :return: If the paths are not starting at the same location this function returns an empty string.
    :rtype: str
    """
    position = bpath.find(apath)
    if position != 0:
        return ""
    rposition = position + len(apath)
    result = bpath[rposition:]
    if not result.startswith("/"):
        result = "/" + result
    return result


def set_arch(self, arch, repo=False):
    """
    This is a setter for system architectures. If the arch is not valid then an exception is raised.

    :param self: The object where the arch will be set.
    :param arch: The desired architecture to set for the object.
    :param repo: If the object where the arch will be set is a repo or not.
    :type repo: bool
    """
    if not arch or arch == "standard" or arch == "x86":
        arch = "i386"

    if repo:
        valids = ["i386", "x86_64", "ia64", "ppc", "ppc64", "ppc64le", "ppc64el", "s390", "s390x", "noarch", "src",
                  "arm", "aarch64"]
    else:
        valids = ["i386", "x86_64", "ia64", "ppc", "ppc64", "ppc64le", "ppc64el", "s390", "s390x", "arm", "aarch64"]

    if arch in valids:
        self.arch = arch
        return

    raise CX("arch choices include: %s" % ", ".join(valids))


def set_os_version(self, os_version):
    """
    This is a setter for the operating system version of an object.

    :param self: The object to set the os-version for.
    :param os_version: The version which shall be set.
    """
    if not os_version:
        self.os_version = ""
        return
    self.os_version = os_version.lower()
    if not self.breed:
        raise CX(_("cannot set --os-version without setting --breed first"))
    if self.breed not in get_valid_breeds():
        raise CX(_("fix --breed first before applying this setting"))
    matched = SIGNATURE_CACHE["breeds"][self.breed]
    if os_version not in matched:
        nicer = ", ".join(matched)
        raise CX(_("--os-version for breed %s must be one of %s, given was %s") % (self.breed, nicer, os_version))
    self.os_version = os_version


def set_breed(self, breed):
    """
    This is a setter for the operating system breed.

    :param self: The object to set the os-breed for.
    :param breed: The os-breed which shall be set.
    """
    valid_breeds = get_valid_breeds()
    if breed is not None and breed.lower() in valid_breeds:
        self.breed = breed.lower()
        return
    nicer = ", ".join(valid_breeds)
    raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support")
             % (breed, nicer))


def set_repo_os_version(self, os_version):
    """
    This is a setter for the os-version of a repository.

    :param self: The repo to set the os-version for.
    :param os_version: The os-version which should be set.
    """
    if not os_version:
        self.os_version = ""
        return
    self.os_version = os_version.lower()
    if not self.breed:
        raise CX(_("cannot set --os-version without setting --breed first"))
    if self.breed not in validate.REPO_BREEDS:
        raise CX(_("fix --breed first before applying this setting"))
    self.os_version = os_version
    return


def set_repo_breed(self, breed):
    """
    This is a setter for the repository breed.

    :param self: The object to set the breed of.
    :param breed: The new value for breed.
    """
    valid_breeds = validate.REPO_BREEDS
    if breed is not None and breed.lower() in valid_breeds:
        self.breed = breed.lower()
        return
    nicer = ", ".join(valid_breeds)
    raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support")
             % (breed, nicer))


def set_repos(self, repos, bypass_check=False):
    """
    This is a setter for the repository.

    :param self: The object to set the repositories of.
    :param repos: The repositories to set for the object.
    :param bypass_check: If the newly set repos should be checked for existence.
    :type bypass_check: bool
    """
    # allow the magic inherit string to persist
    if repos == "<<inherit>>":
        self.repos = "<<inherit>>"
        return

    # store as an array regardless of input type
    if repos is None:
        self.repos = []
    else:
        self.repos = input_string_or_list(repos)
    if bypass_check:
        return

    for r in self.repos:
        if self.collection_mgr.repos().find(name=r) is None:
            raise CX(_("repo %s is not defined") % r)


def set_virt_file_size(self, num):
    """
    For Virt only: Specifies the size of the virt image in gigabytes. Older versions of koan (x<0.6.3) interpret 0 as
    "don't care". Newer versions (x>=0.6.4) interpret 0 as "no disks"

    :param self: The object where the virt file size should be set for.
    :param num: is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                multiple disks
    """

    if num is None or num == "":
        self.virt_file_size = 0
        return

    if num == "<<inherit>>":
        self.virt_file_size = "<<inherit>>"
        return

    if isinstance(num, str) and num.find(",") != -1:
        tokens = num.split(",")
        for t in tokens:
            # hack to run validation on each
            self.set_virt_file_size(t)
        # if no exceptions raised, good enough
        self.virt_file_size = num
        return

    try:
        inum = int(num)
        if inum != float(num):
            raise CX(_("invalid virt file size (%s)" % num))
        if inum >= 0:
            self.virt_file_size = inum
            return
        raise CX(_("invalid virt file size (%s)" % num))
    except:
        raise CX(_("invalid virt file size (%s)" % num))


def set_virt_disk_driver(self, driver):
    """
    For Virt only. Specifies the on-disk format for the virtualized disk

    :param self: The object where the virt disk driver should be set for.
    :param driver: The virt driver to set.
    """
    if driver in validate.VIRT_DISK_DRIVERS:
        self.virt_disk_driver = driver
    else:
        raise CX(_("invalid virt disk driver type (%s)" % driver))


def set_virt_auto_boot(self, num):
    """
    For Virt only.
    Specifies whether the VM should automatically boot upon host reboot 0 tells Koan not to auto_boot virtuals.

    :param self: The object where the virt auto boot should be set for.
    :param num: May be "0" (disabled) or "1" (enabled)
    :type num: int
    """

    if num == "<<inherit>>":
        self.virt_auto_boot = "<<inherit>>"
        return

    # num is a non-negative integer (0 means default)
    try:
        inum = int(num)
        if (inum == 0) or (inum == 1):
            self.virt_auto_boot = inum
            return
        raise CX(_("invalid virt_auto_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % inum))
    except:
        raise CX(_("invalid virt_auto_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % num))


def set_virt_pxe_boot(self, num):
    """
    For Virt only.
    Specifies whether the VM should use PXE for booting 0 tells Koan not to PXE boot virtuals

    :param self: The object where the virt pxe boot should be set for.
    :param num: May be "0" (disabled) or "1" (enabled)
    :type num: int
    """

    # num is a non-negative integer (0 means default)
    try:
        inum = int(num)
        if (inum == 0) or (inum == 1):
            self.virt_pxe_boot = inum
            return
        raise CX(_("invalid virt_pxe_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % inum))
    except:
        raise CX(_("invalid virt_pxe_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % num))


def set_virt_ram(self, num):
    """
    For Virt only.
    Specifies the size of the Virt RAM in MB.

    :param self: The object where the virtual RAM should be set for.
    :param num: 0 tells Koan to just choose a reasonable default.
    :type num: int
    """

    if num == "<<inherit>>":
        self.virt_ram = "<<inherit>>"
        return

    # num is a non-negative integer (0 means default)
    try:
        inum = int(num)
        if inum != float(num):
            raise CX(_("invalid virt ram size (%s)" % num))
        if inum >= 0:
            self.virt_ram = inum
            return
        raise CX(_("invalid virt ram size (%s)" % num))
    except:
        raise CX(_("invalid virt ram size (%s)" % num))


def set_virt_type(self, vtype):
    """
    Virtualization preference, can be overridden by koan.

    :param self: The object where the virtual machine type should be set for.
    :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto"
    """

    if vtype == "<<inherit>>":
        self.virt_type = "<<inherit>>"
        return

    if vtype.lower() not in ["qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz", "auto"]:
        raise CX(_("invalid virt type (%s)" % vtype))
    self.virt_type = vtype


def set_virt_bridge(self, vbridge):
    """
    The default bridge for all virtual interfaces under this profile.

    :param self: The object to adjust the virtual interfaces of.
    :param vbridge: The bridgename to set for the object.
    """
    if not vbridge:
        vbridge = self.settings.default_virt_bridge
    self.virt_bridge = vbridge


def set_virt_path(self, path, for_system=False):
    """
    Virtual storage location suggestion, can be overriden by koan.

    :param self: The object to adjust the virtual storage location.
    :param path: The path to the storage.
    :param for_system: If this is set to True then the value is inherited from a profile.
    :type for_system: bool
    """
    if path is None:
        path = ""
    if for_system:
        if path == "":
            path = "<<inherit>>"
    self.virt_path = path


def set_virt_cpus(self, num):
    """
    For Virt only. Set the number of virtual CPUs to give to the virtual machine. This is fed to virtinst RAW, so
    Cobbler will not yelp if you try to feed it 9999 CPUs. No formatting like 9,999 please :)

    :param self: The object to adjust the virtual cpu cores.
    :param num: The number of cpu cores.
    """
    if num == "" or num is None:
        self.virt_cpus = 1
        return

    if num == "<<inherit>>":
        self.virt_cpus = "<<inherit>>"
        return

    try:
        num = int(str(num))
    except:
        raise CX(_("invalid number of virtual CPUs (%s)" % num))

    self.virt_cpus = num


def safe_filter(var):
    """
    Not know what this function exactly does.

    :param var: This parameter shall not be None or have ".."/";" at the end.
    """
    if var is None:
        return
    if var.find("..") != -1 or var.find(";") != -1:
        raise CX("Invalid characters found in input")


def is_selinux_enabled():
    """
    This check is achieved via a subprocess call to ``selinuxenabled``. Default return is false.

    :return: Whether selinux is enabled or not.
    :rtype: bool
    """
    if not os.path.exists("/usr/sbin/selinuxenabled"):
        return False
    cmd = "/usr/sbin/selinuxenabled"
    selinuxenabled = subprocess_call(None, cmd)
    if selinuxenabled == 0:
        return True
    else:
        return False


# We cache the contents of /etc/mtab ... the following variables are used to keep our cache in sync.
mtab_mtime = None
mtab_map = []


class MntEntObj(object):
    mnt_fsname = None   # name of mounted file system
    mnt_dir = None      # file system path prefix
    mnt_type = None     # mount type (see mntent.h)
    mnt_opts = None     # mount options (see mntent.h)
    mnt_freq = 0        # dump frequency in days
    mnt_passno = 0      # pass number on parallel fsck

    def __init__(self, input=None):
        """
        This is an object which contains information about a mounted filesystem.

        :param input: This is a string which is seperated internally by whitespace. If present it represents the
                      arguments: "mnt_fsname", "mnt_dir", "mnt_type", "mnt_opts", "mnt_freq" and "mnt_passno". The order
                      must be preserved, as well as the separation by whitespace.
        :type input: str
        """
        if input and isinstance(input, str):
            (self.mnt_fsname, self.mnt_dir, self.mnt_type, self.mnt_opts,
             self.mnt_freq, self.mnt_passno) = input.split()

    def __dict__(self):
        """
        This maps all variables available in this class to a dictionary. The name of the keys is identical to the names
        of the variables.

        :return: The dictionary representation of an instance of this class.
        :rtype: dict
        """
        return {"mnt_fsname": self.mnt_fsname, "mnt_dir": self.mnt_dir, "mnt_type": self.mnt_type,
                "mnt_opts": self.mnt_opts, "mnt_freq": self.mnt_freq, "mnt_passno": self.mnt_passno}

    def __str__(self):
        """
        This is the object representation of a mounted filesystem as a string. It can be fed to the constructor of this
        class.

        :return: The space separated list of values of this object.
        """
        return "%s %s %s %s %s %s" % (self.mnt_fsname, self.mnt_dir, self.mnt_type,
                                      self.mnt_opts, self.mnt_freq, self.mnt_passno)


def get_mtab(mtab="/etc/mtab", vfstype=None):
    """
    Get the list of mtab entries. If a custum mtab should be read then the location can be overriden via a parameter.

    :param mtab: The location of the mtab. Argument can be ommited if the mtab is at its default location.
    :param vfstype: If this is True, then all filesystems which are nfs are returned. Otherwise this returns all mtab
                    entries.
    :type vfstype: bool
    :return: The list of requested mtab entries.
    :rtype: list
    """
    global mtab_mtime, mtab_map

    mtab_stat = os.stat(mtab)
    if mtab_stat.st_mtime != mtab_mtime:
        '''cache is stale ... refresh'''
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


def set_serial_device(self, device_number):
    """
    Set the serial device for an object.

    :param self: The object to set the device number for.
    :param device_number: The number of the serial device.
    :type device_number: int
    :return: True if the action succeeded.
    :rtype: bool
    """
    if device_number == "" or device_number is None:
        device_number = None
    else:
        try:
            device_number = int(str(device_number))
        except:
            raise CX(_("invalid value for serial device (%s)" % device_number))

    self.serial_device = device_number
    return True


def set_serial_baud_rate(self, baud_rate):
    """
    The baud rate is very import that the communication between the two devices can be established correctly. This is
    the setter for this parameter. This effectively is the speed of the connection.

    :param self: The object to set the serial baud rate for.
    :param baud_rate: The baud rate to set.
    :type baud_rate: int
    :return: True if the action succeeded.
    :rtype: bool
    """
    if baud_rate == "" or baud_rate is None:
        baud_rate = None
    else:
        try:
            baud_rate = int(str(baud_rate))
        except:
            raise CX(_("invalid value for serial baud (%s)" % baud_rate))

    self.serial_baud_rate = baud_rate
    return True


def __cache_mtab__(mtab="/etc/mtab"):
    """
    Open the mtab and cache it inside Cobbler. If it is guessed that the mtab hasn't changed the cache data is used.

    :param mtab: The location of the mtab. Argument can be ommited if the mtab is at its default location.
    :return: The mtab content stripped from empty lines (if any are present).
    """
    f = open(mtab)
    mtab = [MntEntObj(line) for line in f.read().split('\n') if len(line) > 0]
    f.close()

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
        fname = fname[len(fdir):]

    if chrootfs:
        return (":", fname)
    else:
        return (mtab_dict[fdir], fname)


def is_remote_file(file):
    """
    This function is trying to detect if the file in the argument is remote or not.

    :param file: The filepath to check.
    :return: If remote True, otherwise False.
    :rtype: bool
    """
    (dev, path) = get_file_device_path(file)
    if dev.find(":") != -1:
        return True
    else:
        return False


def subprocess_sp(logger, cmd, shell=True, input=None):
    """
    Call a shell process and redirect the output for internal usage.

    :param logger: The logger to audit the action with.
    :param cmd: The command to execute in a subprocess call.
    :param shell: Whether to use a shell or not for the execution of the commmand.
    :type shell: bool
    :param input: If there is any input needed for that command to stdin.
    :return: A tuple of the output and the return code.
    """
    if logger is not None:
        logger.info("running: %s" % cmd)

    stdin = None
    if input:
        stdin = subprocess.PIPE

    try:
        sp = subprocess.Popen(cmd, shell=shell, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
                              close_fds=True)
    except OSError:
        if logger is not None:
            log_exc(logger)
        die(logger, "OS Error, command not found?  While running: %s" % cmd)

    (out, err) = sp.communicate(input)
    rc = sp.returncode
    if logger is not None:
        logger.info("received on stdout: %s" % out)
        logger.debug("received on stderr: %s" % err)
    return out, rc


def subprocess_call(logger, cmd, shell=True, input=None):
    """
    A simple subprocess call with no output capturing.

    :param logger: The logger to audit the action with.
    :param cmd: The command to execute.
    :param shell: Whether to use a shell or not for the execution of the commmand.
    :type shell: bool
    :param input: If there is any input needed for that command to stdin.
    :return: The return code of the process
    """
    data, rc = subprocess_sp(logger, cmd, shell=shell, input=input)
    return rc


def subprocess_get(logger, cmd, shell=True, input=None):
    """
    A simple subprocess call with no return code capturing.

    :param logger: The logger to audit the action with.
    :param cmd: The command to execute.
    :param shell: Whether to use a shell or not for the execution of the commmand.
    :type shell: bool
    :param input: If there is any input needed for that command to stdin.
    :return: The data which the subprocess returns.
    """
    data, rc = subprocess_sp(logger, cmd, shell=shell, input=input)
    return data


def get_supported_system_boot_loaders():
    """
    Return the list of currently supported bootloaders.

    :return: The list of currently supported bootloaders.
    :rtype: list
    """
    return ["<<inherit>>", "grub", "pxelinux", "yaboot", "ipxe"]


def get_supported_distro_boot_loaders(distro, api_handle=None):
    """
    This is trying to return you the list of known bootloaders if all resorts fail. Otherwise this returns a list which
    contains only the subset of bootloaders which are available by the distro in the argument.

    :param distro: The distro to check for.
    :param api_handle: The api instance to resolve metadata and settings from.
    :return: The list of bootloaders or a dict of well known bootloaders.
    """
    try:
        # Try to read from the signature
        return api_handle.get_signatures()["breeds"][distro.breed][distro.os_version]["boot_loaders"][distro.arch]
    except:
        try:
            # Try to read directly from the cache
            return SIGNATURE_CACHE["breeds"][distro.breed][distro.os_version]["boot_loaders"][distro.arch]
        except:
            try:
                # Else use some well-known defaults
                return {"ppc64": ["grub", "pxelinux", "yaboot"],
                        "ppc64le": ["grub"],
                        "ppc64el": ["grub"],
                        "aarch64": ["grub"],
                        "i386": ["grub", "pxelinux"],
                        "x86_64": ["grub", "pxelinux"]}[distro.arch]
            except:
                # Else return the globally known list
                return get_supported_system_boot_loaders()


def clear_from_fields(item, fields, is_subobject=False):
    """
    Used by various item_*.py classes for automating datastructure boilerplate.

    :param item: The item to clear the fields of.
    :param fields: Not known what magic this actually does.
    :param is_subobject: If in the Cobbler inheritance tree the item is considered a subobject (True) or not (False).
    :type is_subobject: bool
    """
    for elems in fields:
        # if elems startswith * it's an interface field and we do not operate on it.
        if elems[0].startswith("*"):
            continue
        if is_subobject:
            val = elems[2]
        else:
            val = elems[1]
        if isinstance(val, str):
            if val.startswith("SETTINGS:"):
                setkey = val.split(":")[-1]
                val = getattr(item.settings, setkey)
        setattr(item, elems[0], val)

    if item.COLLECTION_TYPE == "system":
        item.interfaces = {}


def from_dict_from_fields(item, item_dict, fields):
    """
    Not known what this method does exactly.

    :param item: Not known what this is needed for exactly.
    :param item_dict: Not known what this is needed for exactly.
    :param fields: Not known what this is needed for exactly.
    """
    int_fields = []
    for elems in fields:
        # we don't have to load interface fields here
        if elems[0].startswith("*"):
            if elems[0].startswith("*"):
                int_fields.append(elems)
            continue
        src_k = dst_k = elems[0]
        # deprecated field switcheroo
        if src_k in field_info.DEPRECATED_FIELDS:
            dst_k = field_info.DEPRECATED_FIELDS[src_k]
        if src_k in item_dict:
            setattr(item, dst_k, item_dict[src_k])

    if item.uid == '':
        item.uid = item.config.generate_uid()

    # special handling for interfaces
    if item.COLLECTION_TYPE == "system":
        item.interfaces = copy.deepcopy(item_dict["interfaces"])
        # deprecated field switcheroo for interfaces
        for interface in list(item.interfaces.keys()):
            for k in list(item.interfaces[interface].keys()):
                if k in field_info.DEPRECATED_FIELDS:
                    if not field_info.DEPRECATED_FIELDS[k] in item.interfaces[interface] or \
                            item.interfaces[interface][field_info.DEPRECATED_FIELDS[k]] == "":
                        item.interfaces[interface][field_info.DEPRECATED_FIELDS[k]] = item.interfaces[interface][k]
            # populate fields that might be missing
            for int_field in int_fields:
                if not int_field[0][1:] in item.interfaces[interface]:
                    item.interfaces[interface][int_field[0][1:]] = int_field[1]


def to_dict_from_fields(item, fields):
    """
    Not known what this method does exactly.

    :param item: Not known what this is needed for exactly.
    :param fields: Not known what this is needed for exactly.
    :return: Returns a dictionary of the fields of an item (distro, profile,..).
    :rtype: dict
    """
    _dict = {}
    for elem in fields:
        k = elem[0]
        if k.startswith("*"):
            continue
        data = getattr(item, k)
        _dict[k] = data
    # Interfaces on systems require somewhat special handling they are the only exception in Cobbler.
    if item.COLLECTION_TYPE == "system":
        _dict["interfaces"] = copy.deepcopy(item.interfaces)
        # for interface in _dict["interfaces"].keys():
        #    for k in _dict["interfaces"][interface].keys():
        #        if field_info.DEPRECATED_FIELDS.has_key(k):
        #            _dict["interfaces"][interface][field_info.DEPRECATED_FIELDS[k]] = _dict["interfaces"][interface][k]

    return _dict


def to_string_from_fields(item_dict, fields, interface_fields=None):
    """
    item_dict is a dictionary, fields is something like item_distro.FIELDS

    :param item_dict: Not known what this is needed for exactly.
    :param fields: Not known what this is needed for exactly.
    :param interface_fields: Not known what this is needed for exactly.
    :return: Not known what this is returning exactly.
    :rtype: str
    """
    buf = ""
    keys = []
    for elem in fields:
        keys.append((elem[0], elem[3], elem[4]))
    keys.sort()
    buf += "%-30s : %s\n" % ("Name", item_dict["name"])
    for (k, nicename, editable) in keys:
        # FIXME: supress fields users don't need to see?
        # FIXME: interfaces should be sorted
        # FIXME: print ctime, mtime nicely
        if not editable:
            continue

        if k != "name":
            # FIXME: move examples one field over, use description here.
            buf += "%-30s : %s\n" % (nicename, item_dict[k])

    # somewhat brain-melting special handling to print the dicts
    # inside of the interfaces more neatly.
    if "interfaces" in item_dict and interface_fields is not None:
        keys = []
        for elem in interface_fields:
            keys.append((elem[0], elem[3], elem[4]))
        keys.sort()
        for iname in list(item_dict["interfaces"].keys()):
            # FIXME: inames possibly not sorted
            buf += "%-30s : %s\n" % ("Interface ===== ", iname)
            for (k, nicename, editable) in keys:
                if editable:
                    buf += "%-30s : %s\n" % (nicename, item_dict["interfaces"][iname].get(k, ""))

    return buf


def get_setter_methods_from_fields(item, fields):
    """
    Return the name of set functions for all fields, keyed by the field name.

    :param item: The item to search for setters.
    :param fields: The fields to search for setters.
    :return: The dictionary with the setter methods.
    """
    setters = {}
    for elem in fields:
        name = elem[0].replace("*", "")
        setters[name] = getattr(item, "set_%s" % name)
    if item.COLLECTION_TYPE == "system":
        setters["modify_interface"] = getattr(item, "modify_interface")
        setters["delete_interface"] = getattr(item, "delete_interface")
        setters["rename_interface"] = getattr(item, "rename_interface")
    return setters


def load_signatures(filename, cache=True):
    """
    Loads the import signatures for distros.

    :param filename: Loads the file with the given name.
    :param cache: If the cache should be set with the newly read data.
    :type cache: bool
    """
    global SIGNATURE_CACHE

    f = open(filename, "r")
    sigjson = f.read()
    f.close()
    sigdata = simplejson.loads(sigjson)
    if cache:
        SIGNATURE_CACHE = sigdata


def get_valid_breeds():
    """
    Return a list of valid breeds found in the import signatures

    :rtype: list
    """
    if "breeds" in SIGNATURE_CACHE:
        return list(SIGNATURE_CACHE["breeds"].keys())
    else:
        return []


def get_valid_os_versions_for_breed(breed):
    """
    Return a list of valid os-versions for the given breed

    :param breed: The operating system breed to check for.
    :return: All operating system version which are known to Cobbler according to the signature cache filtered by a
             os-breed.
    :rtype: list
    """
    os_versions = []
    if breed in get_valid_breeds():
        os_versions = list(SIGNATURE_CACHE["breeds"][breed].keys())
    return os_versions


def get_valid_os_versions():
    """
    Return a list of valid os-versions found in the import signatures

    :return: All operating system versions which are known to Cobbler according to the signature cache.
    :rtype: list
    """
    os_versions = []
    try:
        for breed in get_valid_breeds():
            os_versions += list(SIGNATURE_CACHE["breeds"][breed].keys())
    except:
        pass
    return uniquify(os_versions)


def get_valid_archs():
    """
    Return a list of valid architectures found in the import signatures

    :return: All architectures which are known to Cobbler according to the signature cache.
    """
    archs = []
    try:
        for breed in get_valid_breeds():
            for operating_system in list(SIGNATURE_CACHE["breeds"][breed].keys()):
                archs += SIGNATURE_CACHE["breeds"][breed][operating_system]["supported_arches"]
    except:
        pass
    return uniquify(archs)


def get_shared_secret():
    """
    The 'web.ss' file is regenerated each time cobblerd restarts and is used to agree on shared secret interchange
    between the web server and cobblerd, and also the CLI and cobblerd, when username/password access is not required.
    For the CLI, this enables root users to avoid entering username/pass if on the Cobbler server.

    :return: The Cobbler secret which enables full access to Cobbler.
    :rtype: str
    """

    try:
        fd = open("/var/lib/cobbler/web.ss", 'rb', encoding='utf-8')
        data = fd.read()
    except:
        return -1
    return str(data).strip()


def local_get_cobbler_api_url():
    """
    Get the URL of the Cobbler HTTP API from the Cobbler settings file.

    :return: The api entry point. This does not respect modifications from Loadbalancers or API-Gateways.
    :rtype: str
    """
    # Load server and http port
    try:
        fh = open("/etc/cobbler/settings")
        data = yaml.safe_load(fh.read())
        fh.close()
    except:
        traceback.print_exc()
        raise CX("/etc/cobbler/settings is not a valid YAML file")

    ip = data.get("server", "127.0.0.1")
    if data.get("client_use_localhost", False):
        # this overrides the server setting
        ip = "127.0.0.1"
    port = data.get("http_port", "80")
    protocol = "http"
    if data.get("client_use_https", False):
        protocol = "https"

    return "%s://%s:%s/cobbler_api" % (protocol, ip, port)


def local_get_cobbler_xmlrpc_url():
    """
    Get the URL of the Cobbler XMLRPC API from the Cobbler settings file.

    :return: The api entry point.
    :rtype: str
    """
    # Load xmlrpc port
    try:
        fh = open("/etc/cobbler/settings")
        data = yaml.safe_load(fh.read())
        fh.close()
    except:
        traceback.print_exc()
        raise CX("/etc/cobbler/settings is not a valid YAML file")
    return "http://%s:%s" % ("127.0.0.1", data.get("xmlrpc_port", "25151"))


def strip_none(data, omit_none=False):
    """
    Remove "None" entries from datastructures. Used prior to communicating with XMLRPC.

    :param data: The data to strip None away.
    :param omit_none: If the datastructure is not a single item then None items will be skipped instead of replaced if
                      set to "True".
    :type omit_none: bool
    :return: The modified data structure without any occurrence of None.
    """
    if data is None:
        data = '~'

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

# -------------------------------------------------------


def revert_strip_none(data):
    """
    Does the opposite to strip_none. If a value which represents None is detected, it replaces it with None.

    :param data: The data to check.
    :return: The data without None.
    """
    if isinstance(data, str) and data.strip() == '~':
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

# -------------------------------------------------------


def lod_to_dod(_list, indexkey):
    """
    things like get_distros() returns a list of a dictionaries
    convert this to a dict of dicts keyed off of an arbitrary field

    EX:  [  { "a" : 2 }, { "a : 3 } ]  ->  { "2" : { "a" : 2 }, "3" : { "a" : "3" }

    :param _list: The list of dictionaries to use for the conversion.
    :type _list: list
    :param indexkey: The position to use as dictionary keys.
    :type indexkey: int
    :return: The converted dictionary. It is not guaranteed that the same key is not used multiple times.
    :rtype: dict
    """
    results = {}
    for item in _list:
        results[item[indexkey]] = item
    return results

# -------------------------------------------------------


from functools import cmp_to_key


def mycmp(x, y):
    """
    Compares if x is smaller than y.

    :param x: The first parameter.
    :param y: The second parameter.
    :return: The bool of the action.
    :rtype: bool
    """
    return (x < y)


def lod_sort_by_key(_list, indexkey):
    """
    Sorts a list of dictionaries by a given key in the dictionaries.

    Note: This is a destructive operation and does not sort the dictionaries.

    :param _list: The list of dictionaries to sort.
    :type _list: list
    :param indexkey: The key to index to dicts in the list.
    :return: The sorted list.
    :rtype: list
    """
    _list.sort(key=cmp_to_key(lambda a, b: mycmp(a[indexkey], b[indexkey])))
    return _list


def dhcpconf_location(api):
    """
    This method returns the location of the dhcpd.conf file.

    :param api: This parameter is currently unused.
    :return: The path possibly used for the dhcpd.conf file.
    """
    (dist, version) = os_release()
    if dist in ("redhat", "centos") and version < 6:
        return "/etc/dhcpd.conf"
    elif dist == "fedora" and version < 11:
        return "/etc/dhcpd.conf"
    elif dist == "suse":
        return "/etc/dhcpd.conf"
    elif dist == "debian" and int(version) < 6:
        return "/etc/dhcp3/dhcpd.conf"
    elif dist == "ubuntu" and version < 11.10:
        return "/etc/dhcp3/dhcpd.conf"
    else:
        return "/etc/dhcp/dhcpd.conf"


def namedconf_location(api):
    """
    This returns the location of the named.conf file.

    :param api: This parameter is currently unused.
    :return: If the distro is Debian/Ubuntu then this returns "/etc/bind/named.conf". Otherwise "/etc/named.conf"
    """
    (dist, _) = os_release()
    if dist == "debian" or dist == "ubuntu":
        return "/etc/bind/named.conf"
    else:
        return "/etc/named.conf"


def zonefile_base(api):
    """
    This determines the base directory for the zone files which are important for the named service which Cobbler tries
    to configure.

    :param api: This parameter is currently unused.
    :return: One of "/etc/bind/db.", "/var/lib/named/", "/var/named/". The result depends on the distro used.
    """
    (dist, _) = os_release()
    if dist == "debian" or dist == "ubuntu":
        return "/etc/bind/db."
    if dist == "suse":
        return "/var/lib/named/"
    else:
        return "/var/named/"


def dhcp_service_name(api):
    """
    Determine the dhcp service which is different on various distros. This is currently a hardcoded detection.

    :param api: This parameter is currently unused.
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


def named_service_name(api, logger=None):
    """
    Determine the named service which is normally different on various distros.

    :param api: This parameter is currently unused.
    :param logger: The logger to audit the action with.
    :return: This will return for debian/ubuntu bind9 and on other distros named-chroot or named.
    :rtype: str
    """
    (dist, _) = os_release()
    if dist == "debian" or dist == "ubuntu":
        return "bind9"
    else:
        if is_systemd():
            rc = subprocess_call(logger, ["/usr/bin/systemctl", "is-active", "named-chroot"], shell=False)
            if rc == 0:
                return "named-chroot"
        return "named"


def link_distro(settings, distro):
    """
    Link a Cobbler distro from its source into the web directory to make it reachable from the outside.

    :param settings: The settings to resolve user configurable actions with.
    :param distro: The distro to link into the Cobbler web directory.
    """
    # find the tree location
    base = find_distro_path(settings, distro)
    if not base:
        return

    dest_link = os.path.join(settings.webdir, "links", distro.name)

    # create the links directory only if we are mirroring because with SELinux Apache can't symlink to NFS (without some
    # doing)

    if not os.path.lexists(dest_link):
        try:
            os.symlink(base, dest_link)
        except:
            # this shouldn't happen but I've seen it ... debug ...
            print(_("- symlink creation failed: %(base)s, %(dest)s") % {"base": base, "dest": dest_link})


def find_distro_path(settings, distro):
    """
    This returns the absolute path to the distro under the ``distro_mirror`` directory. If that directory doesn't
    contain the kernel, the directory of the kernel in the distro is returned.

    :param settings: The settings to resolve user configurable actions with.
    :param distro: The distribution to find the path of.
    :return: The path to the distribution files.
    """
    possible_dirs = glob.glob(settings.webdir + "/distro_mirror/*")
    for dir in possible_dirs:
        if os.path.dirname(distro.kernel).find(dir) != -1:
            return os.path.join(settings.webdir, "distro_mirror", dir)
    # non-standard directory, assume it's the same as the directory in which the given distro's kernel is
    return os.path.dirname(distro.kernel)


def compare_versions_gt(ver1, ver2):
    """
    Compares versions like "0.9.3" with each other and decides if ver1 is greater than ver2.

    :param ver1: The first version.
    :param ver2: The second version.
    :return: True if ver1 is greater, otherwise False.
    :rtype: bool
    """
    def versiontuple(v):
        return tuple(map(int, (v.split("."))))
    return versiontuple(ver1) > versiontuple(ver2)


def kopts_overwrite(system, distro, kopts, settings):
    """
    SUSE is not using 'text'. Instead 'textmode' is used as kernel option.

    :param system: The system to overwrite the kopts for.
    :param distro: The distro for the system to change to kopts for.
    :param kopts: The kopts of the system.
    :param settings: The settings instance of Cobbler.
    """
    if distro and distro.breed == "suse":
        if 'textmode' in list(kopts.keys()):
            kopts.pop('text', None)
        elif 'text' in list(kopts.keys()):
            kopts.pop('text', None)
            kopts['textmode'] = ['1']
        if system and settings:
            # only works if pxe_just_once is enabled in global settings
            kopts['info'] = 'http://%s/cblr/svc/op/nopxe/system/%s' % (settings.server, system.name)


if __name__ == "__main__":
    print(os_release())  # returns 2, not 3
