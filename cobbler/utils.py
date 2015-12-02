"""
Misc heavy lifting functions for cobbler

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

import copy
import errno
import glob
import hashlib
import netaddr
import os
import random
import re
import shlex
import shutil
import simplejson
import subprocess
import string
import sys
import traceback
import urllib2
import yaml

from cexceptions import FileNotFoundException, CX
from cobbler import clogger
from cobbler import field_info
from cobbler import validate


def md5(key):
    return hashlib.md5(key)


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


# From http://code.activestate.com/recipes/303342/
class Translator:
    allchars = string.maketrans('', '')

    def __init__(self, frm='', to='', delete='', keep=None):
        if len(to) == 1:
            to = to * len(frm)
        self.trans = string.maketrans(frm, to)
        if keep is None:
            self.delete = delete
        else:
            self.delete = self.allchars.translate(self.allchars, keep.translate(self.allchars, delete))

    def __call__(self, s):
        return s.translate(self.trans, self.delete)


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
    global main_logger
    if main_logger is None:
        main_logger = clogger.Logger()

    # log the exception once in the per-task log or the main
    # log if this is not a background op.
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
    """
    (t, v, tb) = sys.exc_info()
    logger.info("Exception occured: %s" % t)
    logger.info("Exception value: %s" % v)
    logger.info("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))


def get_exc(exc, full=True):
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
    lines = get_exc(exc).split("\n")
    buf = ""
    for l in lines:
        buf += "# %s\n" % l
    return CHEETAH_ERROR_DISCLAIMER + buf


def pretty_hex(ip, length=8):
    """
    Pads an IP object with leading zeroes so that the result is
    _length_ hex digits.  Also do an upper().
    """
    hexval = "%x" % ip.value
    if len(hexval) < length:
        hexval = '0' * (length - len(hexval)) + hexval
    return hexval.upper()


def get_host_ip(ip, shorten=True):
    """
    Return the IP encoding needed for the TFTP boot tree.
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
            cutoff = (32 - cidr.prefixlen) / 4
            return pretty[0:-cutoff]


def _IP(ip):
    """
    Returns a netaddr.IP object representing ip.
    If ip is already an netaddr.IP instance just return it.
    Else return a new instance
    """
    ip_class = netaddr.ip.IPAddress
    if isinstance(ip, ip_class) or ip == "":
        return ip
    else:
        return ip_class(ip)


def get_config_filename(sys, interface):
    """
    The configuration file for each system pxe uses is either
    a form of the MAC address of the hex version of the IP.  If none
    of that is available, just use the given name, though the name
    given will be unsuitable for PXE configuration (For this, check
    system.is_management_supported()).  This same file is used to store
    system config information in the Apache tree, so it's still relevant.
    """

    interface = str(interface)
    if interface not in sys.interfaces:
        return None

    if sys.name == "default":
        return "default"
    mac = sys.get_mac_address(interface)
    ip = sys.get_ip_address(interface)
    if mac is not None and mac != "":
        return "01-" + "-".join(mac.split(":")).lower()
    elif ip is not None and ip != "":
        return get_host_ip(ip)
    else:
        return sys.name


def is_ip(strdata):
    """
    Return whether the argument is an IP address.
    """
    try:
        _IP(strdata)
    except:
        return False
    return True


def is_mac(strdata):
    """
    Return whether the argument is a mac address.
    """
    if strdata is None:
        return False
    return bool(_re_is_mac.match(strdata) or _re_is_ibmac.match(strdata))


def get_random_mac(api_handle, virt_type="xenpv"):
    """
    Generate a random MAC address.
    from xend/server/netif.py
    return: MAC address string
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

    mac = ':'.join(map(lambda x: "%02x" % x, mac))
    systems = api_handle.systems()
    while (systems.find(mac_address=mac)):
        mac = get_random_mac(api_handle)

    return mac


def find_matching_files(directory, regex):
    """
    Find all files in a given directory that match a given regex.
    Can't use glob directly as glob doesn't take regexen.
    """
    files = glob.glob(os.path.join(directory, "*"))
    results = []
    for f in files:
        if regex.match(os.path.basename(f)):
            results.append(f)
    return results


def find_highest_files(directory, unversioned, regex):
    """
    Find the highest numbered file (kernel or initrd numbering scheme)
    in a given directory that matches a given pattern.  Used for
    auto-booting the latest kernel in a directory.
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

    # couldn't find a highest numbered file, but maybe there
    # is just a 'vmlinuz' or an 'initrd.img' in this directory?
    last_chance = os.path.join(directory, unversioned)
    if os.path.exists(last_chance):
        return last_chance
    return None


def find_kernel(path):
    """
    Given a directory or a filename, find if the path can be made
    to resolve into a kernel, and return that full path if possible.
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

    # For remote URLs we expect an absolute path, and will not
    # do any searching for the latest:
    elif file_is_remote(path) and remote_file_exists(path):
        return path

    return None


def remove_yum_olddata(path, logger=None):
    """
    Delete .olddata files that might be present from a failed run
    of createrepo.
    # FIXME: verify this is still being used
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
    Given a directory or a filename, see if the path can be made
    to resolve into an intird, return that full path if possible.
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
    Reads the contents of a file, which could be referenced locally
    or as a URI.

    Returns None if file is remote and templating of remote files is
    disabled.

    Throws a FileNotFoundException if the file does not exist at the
    specified location.
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
            handler = urllib2.urlopen(file_location)
            data = handler.read()
            handler.close()
            return data
        except urllib2.HTTPError:
            # File likely doesn't exist
            if logger:
                logger.warning("File does not exist: %s" % file_location)
            raise FileNotFoundException("%s: %s" % (_("File not found"), file_location))


def remote_file_exists(file_url):
    """ Return True if the remote file exists. """
    try:
        handler = urllib2.urlopen(file_url)
        handler.close()
        return True
    except urllib2.HTTPError:
        # File likely doesn't exist
        return False


def file_is_remote(file_location):
    """
    Returns true if the file is remote and referenced via a protocol
    we support.
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
    """
    if options == "<<inherit>>":
        return "<<inherit>>"
    if options is None or options == "" or options == "delete":
        return []
    elif isinstance(options, list):
        return options
    elif isinstance(options, basestring):
        tokens = shlex.split(options)
        return tokens
    else:
        raise CX(_("invalid input type"))


def input_string_or_dict(options, allow_multiples=True):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options == "<<inherit>>":
        options = {}

    if options is None or options == "delete":
        return (True, {})
    elif isinstance(options, list):
        raise CX(_("No idea what to do with list: %s") % options)
    elif isinstance(options, basestring):
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

            # if we're allowing multiple values for the same key,
            # check to see if this token has already been
            # inserted into the dictionary of values already

            if key in new_dict.keys() and allow_multiples:
                # if so, check to see if there is already a list of values
                # otherwise convert the dictionary value to an array, and add
                # the new value to the end of the list
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
    value = str(value)
    if value.lower() in ["true", "1", "on", "yes", "y"]:
        return True
    else:
        return False


def update_settings_file(data):
    if 1:
        # clogger.Logger().debug("in update_settings_file(): value is: %s" % str(value))
        settings_file = file("/etc/cobbler/settings", "w")
        yaml.safe_dump(data, settings_file)
        settings_file.close()
        return True
    # except:
    #    return False


def grab_tree(api_handle, item):
    """
    Climb the tree and get every node.
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
    Combine all of the data in an object tree from the perspective
    of that point on the tree, and produce a merged dictionary containing
    consolidated data.
    """

    tree = grab_tree(api_handle, root_obj)
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node, results)

    # make interfaces accessible without Cheetah-voodoo in the templates
    # EXAMPLE:  $ip == $ip0, $ip1, $ip2 and so on.

    if root_obj.COLLECTION_TYPE == "system":
        for (name, interface) in root_obj.interfaces.iteritems():
            for key in interface.keys():
                results["%s_%s" % (key, name)] = interface[key]

    # if the root object is a profile or system, add in all
    # repo data for repos that belong to the object chain
    if root_obj.COLLECTION_TYPE in ("profile", "system"):
        repo_data = []
        for r in results.get("repos", []):
            repo = api_handle.find_repo(name=r)
            if repo:
                repo_data.append(repo.to_dict())
        # FIXME: sort the repos in the array based on the
        #        repo priority field so that lower priority
        #        repos come first in the array
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

    # add in some variables for easier templating
    # as these variables change based on object type
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
    # convert certain nested dicts to strings.
    # this is only really done for the ones koan needs as strings
    # this should not be done for everything
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

    # note -- we do not need to flatten "interfaces" as koan does not expect
    # it to be a string, nor do we use it on a kernel options line, etc...
    return data


def uniquify(seq):
    # credit: http://www.peterbe.com/plog/uniqifiers-benchmark
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
    Merge data from a given node with the aggregate of all
    data from past scanned nodes.  Dictionaries and arrays are treated
    specially.
    """
    node_data = node.to_dict()

    # if the node has any data items labelled <<inherit>> we need to expunge them.
    # so that they do not override the supernodes.
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
            # now merge data types seperately depending on whether they are dict, list,
            # or scalar.
            fielddata = results[field]

            if isinstance(fielddata, dict):
                # interweave dict results
                results[field].update(data_item.copy())
            elif isinstance(fielddata, list) or isinstance(fielddata, tuple):
                # add to lists (cobbler doesn't have many lists)
                # FIXME: should probably uniqueify list after doing this
                results[field].extend(data_item)
                results[field] = uniquify(results[field])
            else:
                # distro field gets special handling, since we don't
                # want to overwrite it ever.
                # FIXME: should the parent's field too? It will be over-
                #        written if there are multiple sub-profiles in
                #        the chain of inheritance
                if field != "distro":
                    results[field] = data_item
        else:
            results[field] = data_item

    # now if we have any "!foo" results in the list, delete corresponding
    # key entry "foo", and also the entry "!foo", allowing for removal
    # of kernel options set in a distro later in a profile, etc.

    dict_removals(results, "kernel_options")
    dict_removals(results, "kernel_options_post")
    dict_removals(results, "autoinstall_meta")
    dict_removals(results, "template_files")
    dict_removals(results, "boot_files")
    dict_removals(results, "fetchable_files")


def dict_removals(results, subkey):
    if subkey not in results:
        return
    scan = results[subkey].keys()
    for k in scan:
        if str(k).startswith("!") and k != "!":
            remove_me = k[1:]
            if remove_me in results[subkey]:
                del results[subkey][remove_me]
            del results[subkey][k]


def dict_to_string(_dict):
    """
    Convert a dictionary to a printable string.
    used primarily in the kernel options string
    and for some legacy stuff where koan expects strings
    (though this last part should be changed to dictionaries)
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
                buffer += str(key) + "=" + str(item) + " "
        else:
            buffer += str(key) + "=" + str(value) + " "
    return buffer


def rsync_files(src, dst, args, logger=None, quiet=True):
    """
    Sync files from src to dst. The extra arguments specified
    by args are appended to the command
    """

    if args is None:
        args = ''

    RSYNC_CMD = "rsync -a %%s '%%s' %%s %s --exclude-from=/etc/cobbler/rsync.exclude" % args
    if quiet:
        RSYNC_CMD += " --quiet"
    else:
        RSYNC_CMD += " --progress"

    # Make sure we put a "/" on the end of the source
    # and destination to make sure we don't cause any
    # rsync weirdness
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
    """

    my_cmd = cmd % args
    rc = subprocess_call(logger, my_cmd, shell=True)
    if rc != 0:
        die(logger, "Command failed")


def run_triggers(api, ref, globber, additional=[], logger=None):
    """
    Runs all the trigger scripts in a given directory.
    ref can be a cobbler object, if not None, the name will be passed
    to the script.  If ref is None, the script will be called with
    no argumenets.  Globber is a wildcard expression indicating which
    triggers to run.  Example:  "/var/lib/cobbler/triggers/blah/*"

    As of Cobbler 1.5.X, this also runs cobbler modules that match the globbing paths.
    """

    # Python triggers first, before shell

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
            raise CX("cobbler trigger failed: %s" % m.__name__)

    # now do the old shell triggers, which are usually going to be slower, but are easier to write
    # and support any language

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
            raise CX(_("cobbler trigger failed: %(file)s returns %(code)d") % {"file": file, "code": rc})

        if logger is not None:
            logger.debug("shell trigger %s finished successfully" % file)

    if logger is not None:
        logger.debug("shell triggers finished successfully")


def get_family():
    """
    Get family of running operating system.

    Family is the base Linux distribution of a Linux distribution, with a set of common
    """

    redhat_list = ("red hat", "redhat", "scientific linux", "fedora", "centos")

    dist = check_dist()
    for item in redhat_list:
        if item in dist:
            return "redhat"
    if dist in ("debian", "ubuntu"):
        return "debian"
    if "suse" in dist:
        return "suse"
    return dist


def check_dist():
    """
    Determines what distro we're running under.
    """
    import platform
    try:
        return platform.linux_distribution()[0].lower().strip()
    except AttributeError:
        return platform.dist()[0].lower().strip()


def os_release():

    family = get_family()
    if family == "redhat":
        fh = open("/etc/redhat-release")
        data = fh.read().lower()
        if data.find("fedora") != -1:
            make = "fedora"
        elif data.find("centos") != -1:
            make = "centos"
        else:
            make = "redhat"
        release_index = data.find("release")
        rest = data[release_index + 7:-1]
        tokens = rest.split(" ")
        for t in tokens:
            try:
                match = re.match('^\d+(?:\.\d+)?', t)
                if match:
                    return (make, float(match.group(0)))
            except ValueError:
                pass
        raise CX("failed to detect local OS version from /etc/redhat-release")

    elif family == "debian":
        distro = check_dist()
        if distro == "debian":
            import lsb_release
            release = lsb_release.get_distro_information()['RELEASE']
            return ("debian", release)
        elif distro == "ubuntu":
            version = subprocess_get(None, "lsb_release --release --short").rstrip()
            make = "ubuntu"
            return (make, float(version))

    elif family == "suse":
        fd = open("/etc/SuSE-release")
        for line in fd.read().split("\n"):
            if line.find("VERSION") != -1:
                version = line.replace("VERSION = ", "")
            if line.find("PATCHLEVEL") != -1:
                rest = line.replace("PATCHLEVEL = ", "")
        make = "suse"
        return (make, float(version))
    else:
        return ("unknown", 0)


def tftpboot_location():
    """
    Guesses the location of the tftpboot directory,
    based on the distro on which cobblerd is running
    """
    (make, version) = os_release()
    str_version = str(version)

    if make in ("fedora", "redhat", "centos"):
        return "/var/lib/tftpboot"
    elif make == "suse":
        return "/srv/tftpboot"
    # As of Ubuntu 12.04, while they seem to have settled on sticking with
    # /var/lib/tftpboot, they haven't scrubbed all of the packages that came
    # from Debian that use /srv/tftp by default.
    elif make == "ubuntu" and os.path.exists("/var/lib/tftpboot"):
        return "/var/lib/tftpboot"
    elif make == "ubuntu" and os.path.exists("/srv/tftp"):
        return "/srv/tftp"
    elif make == "debian" and int(str_version.split('.')[0]) < 6:
        return "/var/lib/tftpboot"
    elif make == "debian" and int(str_version.split('.')[0]) >= 6:
        return "/srv/tftp"
    else:
        return "/tftpboot"


def is_safe_to_hardlink(src, dst, api):
    (dev1, path1) = get_file_device_path(src)
    (dev2, path2) = get_file_device_path(dst)
    if dev1 != dev2:
        return False
    if dev1.find(":") != -1:
        # is remoted
        return False
    # note: this is very cobbler implementation specific!
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
    Copy a file into a cache and link it into place.
    Use this with caution, otherwise you could end up
    copying data twice if the cache is not on the same device
    as the destination
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
    Attempt to create a link dst that points to src.  Because file
    systems suck we attempt several different methods or bail to
    copyfile()
    """

    if api is None:
        # FIXME: this really should not be a keyword
        # arg
        raise "Internal error: API handle is required"

    if os.path.exists(dst):
        # if the destination exists, is it right in terms of accuracy
        # and context?
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
        # we can try a hardlink if the destination isn't to NFS or Samba
        # this will help save space and sync time.
        try:
            if logger is not None:
                logger.info("trying hardlink %s -> %s" % (src, dst))
            os.link(src, dst)
            return
        except (IOError, OSError):
            # hardlink across devices, or link already exists
            # we'll just symlink it if we can
            # or otherwise copy it
            pass

    if symlink_ok:
        # we can symlink anywhere except for /tftpboot because
        # that is run chroot, so if we can symlink now, try it.
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
    try:
        if logger is not None:
            logger.info("copying: %s -> %s" % (src, dst1))
        srcfile = urllib2.urlopen(src)
        output = open(dst1, 'wb')
        output.write(srcfile.read())
        output.close()
    except Exception, e:
        raise CX(_("Error while getting remote file (%s -> %s):\n%s" % (src, dst1, e.message)))


def copyfile_pattern(pattern, dst, require_match=True, symlink_ok=False, cache=True, api=None, logger=None):
    files = glob.glob(pattern)
    if require_match and not len(files) > 0:
        raise CX(_("Could not find files matching %s") % pattern)
    for file in files:
        dst1 = os.path.join(dst, os.path.basename(file))
        linkfile(file, dst1, symlink_ok=symlink_ok, cache=cache, api=api, logger=logger)


def rmfile(path, logger=None):
    try:
        if logger is not None:
            logger.info("removing: %s" % path)
        os.unlink(path)
        return True
    except OSError, ioe:
        if not ioe.errno == errno.ENOENT:   # doesn't exist
            if logger is not None:
                log_exc(logger)
            raise CX(_("Error deleting %s") % path)
        return True


def rmtree_contents(path, logger=None):
    what_to_delete = glob.glob("%s/*" % path)
    for x in what_to_delete:
        rmtree(x, logger=logger)


def rmtree(path, logger=None):
    try:
        if os.path.isfile(path):
            return rmfile(path, logger=logger)
        else:
            if logger is not None:
                logger.info("removing: %s" % path)
            return shutil.rmtree(path, ignore_errors=True)
    except OSError, ioe:
        if logger is not None:
            log_exc(logger)
        if not ioe.errno == errno.ENOENT:   # doesn't exist
            raise CX(_("Error deleting %s") % path)
        return True


def mkdir(path, mode=0755, logger=None):
    try:
        if logger is not None:
            logger.info("mkdir: %s" % path)
        return os.makedirs(path, mode)
    except OSError, oe:
        if not oe.errno == 17:  # already exists (no constant for 17?)
            if logger is not None:
                log_exc(logger)
            raise CX(_("Error creating %s") % path)


def path_tail(apath, bpath):
    """
    Given two paths (B is longer than A), find the part in B not in A
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
    if arch is None or arch == "" or arch == "standard" or arch == "x86":
        arch = "i386"

    if repo:
        valids = ["i386", "x86_64", "ppc", "ppc64", "ppc64le", "ppc64el", "noarch", "src", "arm"]
    else:
        valids = ["i386", "x86_64", "ppc", "ppc64", "ppc64le", "ppc64el", "arm"]

    if arch in valids:
        self.arch = arch
        return

    raise CX("arch choices include: %s" % ", ".join(valids))


def set_os_version(self, os_version):
    if os_version == "" or os_version is None:
        self.os_version = ""
        return
    self.os_version = os_version.lower()
    if self.breed is None or self.breed == "":
        raise CX(_("cannot set --os-version without setting --breed first"))
    if self.breed not in get_valid_breeds():
        raise CX(_("fix --breed first before applying this setting"))
    matched = SIGNATURE_CACHE["breeds"][self.breed]
    if os_version not in matched:
        nicer = ", ".join(matched)
        raise CX(_("--os-version for breed %s must be one of %s, given was %s") % (self.breed, nicer, os_version))
    self.os_version = os_version


def set_breed(self, breed):
    valid_breeds = get_valid_breeds()
    if breed is not None and breed.lower() in valid_breeds:
        self.breed = breed.lower()
        return
    nicer = ", ".join(valid_breeds)
    raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support") % (breed, nicer))


def set_repo_os_version(self, os_version):
    if os_version == "" or os_version is None:
        self.os_version = ""
        return
    self.os_version = os_version.lower()
    if self.breed is None or self.breed == "":
        raise CX(_("cannot set --os-version without setting --breed first"))
    if self.breed not in validate.REPO_BREEDS:
        raise CX(_("fix --breed first before applying this setting"))
    self.os_version = os_version
    return


def set_repo_breed(self, breed):
    valid_breeds = validate.REPO_BREEDS
    if breed is not None and breed.lower() in valid_breeds:
        self.breed = breed.lower()
        return
    nicer = ", ".join(valid_breeds)
    raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support") % (breed, nicer))


def set_repos(self, repos, bypass_check=False):
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
    For Virt only.
    Specifies the size of the virt image in gigabytes.
    Older versions of koan (x<0.6.3) interpret 0 as "don't care"
    Newer versions (x>=0.6.4) interpret 0 as "no disks"
    """
    # num is a non-negative integer (0 means default)
    # can also be a comma seperated list -- for usage with multiple disks

    if num is None or num == "":
        self.virt_file_size = 0
        return

    if num == "<<inherit>>":
        self.virt_file_size = "<<inherit>>"
        return

    if isinstance(num, basestring) and num.find(",") != -1:
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
    For Virt only.
    Specifies the on-disk format for the virtualized disk
    """
    if driver in validate.VIRT_DISK_DRIVERS:
        self.virt_disk_driver = driver
    else:
        raise CX(_("invalid virt disk driver type (%s)" % driver))


def set_virt_auto_boot(self, num):
    """
    For Virt only.
    Specifies whether the VM should automatically boot upon host reboot
    0 tells Koan not to auto_boot virtuals
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
    Specifies whether the VM should use PXE for booting
    0 tells Koan not to PXE boot virtuals
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
    0 tells Koan to just choose a reasonable default.
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
    """
    if vbridge is None or vbridge == "":
        vbridge = self.settings.default_virt_bridge
    self.virt_bridge = vbridge


def set_virt_path(self, path, for_system=False):
    """
    Virtual storage location suggestion, can be overriden by koan.
    """
    if path is None:
        path = ""
    if for_system:
        if path == "":
            path = "<<inherit>>"
    self.virt_path = path


def set_virt_cpus(self, num):
    """
    For Virt only.  Set the number of virtual CPUs to give to the
    virtual machine.  This is fed to virtinst RAW, so cobbler
    will not yelp if you try to feed it 9999 CPUs.  No formatting
    like 9,999 please :)
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
    if var is None:
        return
    if var.find("..") != -1 or var.find(";") != -1:
        raise CX("Invalid characters found in input")


def is_selinux_enabled():
    if not os.path.exists("/usr/sbin/selinuxenabled"):
        return False
    cmd = "/usr/sbin/selinuxenabled"
    selinuxenabled = subprocess_call(None, cmd)
    if selinuxenabled == 0:
        return True
    else:
        return False

# We cache the contents of /etc/mtab ... the following variables are used
# to keep our cache in sync
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
        if input and isinstance(input, basestring):
            (self.mnt_fsname, self.mnt_dir, self.mnt_type, self.mnt_opts,
             self.mnt_freq, self.mnt_passno) = input.split()

    def __dict__(self):
        return {"mnt_fsname": self.mnt_fsname, "mnt_dir": self.mnt_dir,
                "mnt_type": self.mnt_type, "mnt_opts": self.mnt_opts,
                "mnt_freq": self.mnt_freq, "mnt_passno": self.mnt_passno}

    def __str__(self):
        return "%s %s %s %s %s %s" % (self.mnt_fsname, self.mnt_dir, self.mnt_type,
                                      self.mnt_opts, self.mnt_freq, self.mnt_passno)


def get_mtab(mtab="/etc/mtab", vfstype=None):
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


def __cache_mtab__(mtab="/etc/mtab"):
    f = open(mtab)
    mtab = [MntEntObj(line) for line in f.read().split('\n') if len(line) > 0]
    f.close()

    return mtab


def get_file_device_path(fname):
    '''What this function attempts to do is take a file and return:
         - the device the file is on
         - the path of the file relative to the device.
       For example:
         /boot/vmlinuz -> (/dev/sda3, /vmlinuz)
         /boot/efi/efi/redhat/elilo.conf -> (/dev/cciss0, /elilo.conf)
         /etc/fstab -> (/dev/sda4, /etc/fstab)
    '''

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
    (dev, path) = get_file_device_path(file)
    if dev.find(":") != -1:
        return True
    else:
        return False


def subprocess_sp(logger, cmd, shell=True, input=None):
    if logger is not None:
        logger.info("running: %s" % cmd)

    stdin = None
    if input:
        stdin = subprocess.PIPE

    try:
        sp = subprocess.Popen(cmd, shell=shell, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
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
    data, rc = subprocess_sp(logger, cmd, shell=shell, input=input)
    return rc


def subprocess_get(logger, cmd, shell=True, input=None):
    data, rc = subprocess_sp(logger, cmd, shell=shell, input=input)
    return data


def get_supported_system_boot_loaders():
    return ["<<inherit>>", "grub", "grub2", "pxelinux", "yaboot", "ipxe"]


def get_supported_distro_boot_loaders(distro, api_handle=None):
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
                return {"ppc64": ["grub2", "pxelinux", "yaboot"],
                        "ppc64le": ["grub2"],
                        "ppc64el": ["grub2"],
                        "i386": ["grub", "pxelinux"],
                        "x86_64": ["grub", "pxelinux"]}[distro.arch]
            except:
                # Else return the globally known list
                return get_supported_system_boot_loaders()


def clear_from_fields(item, fields, is_subobject=False):
    """
    Used by various item_*.py classes for automating datastructure boilerplate.
    """
    for elems in fields:
        # if elems startswith * it's an interface field and we do not operate on it.
        if elems[0].startswith("*"):
            continue
        if is_subobject:
            val = elems[2]
        else:
            val = elems[1]
        if isinstance(val, basestring):
            if val.startswith("SETTINGS:"):
                setkey = val.split(":")[-1]
                val = getattr(item.settings, setkey)
        setattr(item, elems[0], val)

    if item.COLLECTION_TYPE == "system":
        item.interfaces = {}


def from_dict_from_fields(item, item_dict, fields):
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
        for interface in item.interfaces.keys():
            for k in item.interfaces[interface].keys():
                if k in field_info.DEPRECATED_FIELDS:
                    if not field_info.DEPRECATED_FIELDS[k] in item.interfaces[interface] or \
                            item.interfaces[interface][field_info.DEPRECATED_FIELDS[k]] == "":
                        item.interfaces[interface][field_info.DEPRECATED_FIELDS[k]] = item.interfaces[interface][k]
            # populate fields that might be missing
            for int_field in int_fields:
                if not int_field[0][1:] in item.interfaces[interface]:
                    item.interfaces[interface][int_field[0][1:]] = int_field[1]


def to_dict_from_fields(item, fields):
    _dict = {}
    for elem in fields:
        k = elem[0]
        if k.startswith("*"):
            continue
        data = getattr(item, k)
        _dict[k] = data
    # interfaces on systems require somewhat special handling
    # they are the only exception in Cobbler.
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
        for iname in item_dict["interfaces"].keys():
            # FIXME: inames possibly not sorted
            buf += "%-30s : %s\n" % ("Interface ===== ", iname)
            for (k, nicename, editable) in keys:
                if editable:
                    buf += "%-30s : %s\n" % (nicename, item_dict["interfaces"][iname].get(k, ""))

    return buf


def get_setter_methods_from_fields(item, fields):
    """
    Return the name of set functions for all fields, keyed by the field name.
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
    Loads the import signatures for distros
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
    """
    if "breeds" in SIGNATURE_CACHE:
        return SIGNATURE_CACHE["breeds"].keys()
    else:
        return []


def get_valid_os_versions_for_breed(breed):
    """
    Return a list of valid os-versions for the given breed
    """
    os_versions = []
    if breed in get_valid_breeds():
        os_versions = SIGNATURE_CACHE["breeds"][breed].keys()
    return os_versions


def get_valid_os_versions():
    """
    Return a list of valid os-versions found in the import signatures
    """
    os_versions = []
    try:
        for breed in get_valid_breeds():
            os_versions += SIGNATURE_CACHE["breeds"][breed].keys()
    except:
        pass
    return uniquify(os_versions)


def get_valid_archs():
    """
    Return a list of valid architectures found in the import signatures
    """
    archs = []
    try:
        for breed in get_valid_breeds():
            for operating_system in SIGNATURE_CACHE["breeds"][breed].keys():
                archs += SIGNATURE_CACHE["breeds"][breed][operating_system]["supported_arches"]
    except:
        pass
    return uniquify(archs)


def get_shared_secret():
    """
    The 'web.ss' file is regenerated each time cobblerd restarts and is
    used to agree on shared secret interchange between mod_python and
    cobblerd, and also the CLI and cobblerd, when username/password
    access is not required.  For the CLI, this enables root users
    to avoid entering username/pass if on the cobbler server.
    """

    try:
        fd = open("/var/lib/cobbler/web.ss")
        data = fd.read()
    except:
        return -1
    return str(data).strip()


def local_get_cobbler_api_url():
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
    Remove "none" entries from datastructures.
    Used prior to communicating with XMLRPC.
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
        for key in data.keys():
            if omit_none and data[key] is None:
                pass
            else:
                data2[str(key)] = strip_none(data[key])
        return data2

    return data

# -------------------------------------------------------


def lod_to_dod(_list, indexkey):
    """
    things like get_distros() returns a list of a dictionaries
    convert this to a dict of dicts keyed off of an arbitrary field

    EX:  [  { "a" : 2 }, { "a : 3 } ]  ->  { "2" : { "a" : 2 }, "3" : { "a" : "3" }

    """
    results = {}
    for item in _list:
        results[item[indexkey]] = item
    return results

# -------------------------------------------------------


def lod_sort_by_key(_list, indexkey):
    """
    Sorts a list of dictionaries by a given key in the dictionaries
    note: this is a destructive operation
    """
    _list.sort(lambda a, b: a[indexkey] < b[indexkey])
    return _list


def dhcpconf_location(api):
    version = api.os_version
    (dist, ver) = api.get_os_details()
    if version[0] in ["redhat", "centos"] and version[1] < 6:
        return "/etc/dhcpd.conf"
    elif version[0] in ["fedora"] and version[1] < 11:
        return "/etc/dhcpd.conf"
    elif dist == "suse":
        return "/etc/dhcpd.conf"
    elif dist == "debian" and int(version[1].split('.')[0]) < 6:
        return "/etc/dhcp3/dhcpd.conf"
    elif dist == "ubuntu" and version[1] < 11.10:
        return "/etc/dhcp3/dhcpd.conf"
    else:
        return "/etc/dhcp/dhcpd.conf"


def namedconf_location(api):
    (dist, ver) = api.os_version
    if dist == "debian" or dist == "ubuntu":
        return "/etc/bind/named.conf"
    else:
        return "/etc/named.conf"


def zonefile_base(api):
    (dist, version) = api.os_version
    if dist == "debian" or dist == "ubuntu":
        return "/etc/bind/db."
    else:
        return "/var/named/"


def dhcp_service_name(api):
    (dist, version) = api.os_version
    if dist == "debian" and int(version.split('.')[0]) < 6:
        return "dhcp3-server"
    elif dist == "debian" and int(version.split('.')[0]) >= 6:
        return "isc-dhcp-server"
    elif dist == "ubuntu" and version < 11.10:
        return "dhcp3-server"
    elif dist == "ubuntu" and version >= 11.10:
        return "isc-dhcp-server"
    else:
        return "dhcpd"


def named_service_name(api):
    (dist, ver) = api.os_version
    if dist == "debian" or dist == "ubuntu":
        return "bind9"
    else:
        return "named"


def link_distro(settings, distro):
    # find the tree location
    base = find_distro_path(settings, distro)
    if not base:
        return

    dest_link = os.path.join(settings.webdir, "links", distro.name)

    # create the links directory only if we are mirroring because with
    # SELinux Apache can't symlink to NFS (without some doing)

    if not os.path.lexists(dest_link):
        try:
            os.symlink(base, dest_link)
        except:
            # this shouldn't happen but I've seen it ... debug ...
            print _("- symlink creation failed: %(base)s, %(dest)s") % {"base": base, "dest": dest_link}


def find_distro_path(settings, distro):
    possible_dirs = glob.glob(settings.webdir + "/distro_mirror/*")
    for dir in possible_dirs:
        if os.path.dirname(distro.kernel).find(dir) != -1:
            return os.path.join(settings.webdir, "distro_mirror", dir)
    # non-standard directory, assume it's the same as the
    # directory in which the given distro's kernel is
    return os.path.dirname(distro.kernel)


def compare_versions_gt(ver1, ver2):
    def versiontuple(v):
        return tuple(map(int, (v.split("."))))
    return versiontuple(ver1) > versiontuple(ver2)

if __name__ == "__main__":
    print os_release()  # returns 2, not 3
