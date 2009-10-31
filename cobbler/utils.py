"""
Misc heavy lifting functions for cobbler

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import sys
import os
import re
import copy
import socket
import glob
import random
import sub_process
import shutil
import string
import traceback
import errno
import logging
import shutil
import tempfile
import signal
from cexceptions import *
import codes
import time
import netaddr
import shlex
import field_info
import clogger
import yaml

try:
    import hashlib as fiver
    def md5(key):
        return fiver.md5(key)
except ImportError: 
    # for Python < 2.5
    import md5 as fiver
    def md5(key):
        return fiver.md5(key)

# python-netaddr 0.7 broke backward compatability, try to use the old IP
# classes, and fallback on the newer if there's an import error.
NETADDR_PRE_0_7 = True
try:
    # Try importing the old (pre-0.7) netaddr IP class:
    from netaddr import IP
except ImportError:
    NETADDR_PRE_0_7 = False

CHEETAH_ERROR_DISCLAIMER="""
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
    allchars = string.maketrans('','')
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


#placeholder for translation
def _(foo):
   return foo

MODULE_CACHE = {}

_re_kernel = re.compile(r'(vmlinu[xz]|kernel.img)')
_re_initrd = re.compile(r'(initrd(.*).img|ramdisk.image.gz)')

# all logging from utils.die goes to the main log even if there
# is another log.
main_logger = clogger.Logger()

def die(logger, msg):

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
    logger.info("Exception occured: %s" % t )
    logger.info("Exception value: %s" % v)
    logger.info("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))
   

def get_exc(exc,full=True):
   (t, v, tb) = sys.exc_info()
   buf = ""
   try:
      getattr(exc, "from_cobbler")
      buf = str(exc)[1:-1] + "\n"
   except:
      if not full:
          buf = buf + str(t)
      buf = "%s\n%s" % (buf,v)
      if full:
          buf = buf + "\n" + "\n".join(traceback.format_list(traceback.extract_tb(tb)))
   return buf

def cheetah_exc(exc,full=False):
   lines = get_exc(exc).split("\n")
   buf = ""
   for l in lines:
      buf = buf + "# %s\n" % l
   return CHEETAH_ERROR_DISCLAIMER + buf

def trace_me():
   x = traceback.extract_stack()
   bar = string.join(traceback.format_list(x))
   return bar

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
    cidr = None

    if NETADDR_PRE_0_7:
        ip = netaddr.IP(ip)
        cidr = ip.cidr()
    else:
        ip = netaddr.ip.IPAddress(ip)
        cidr = netaddr.ip.IPNetwork(ip)

    if len(cidr) == 1: # Just an IP, e.g. a /32
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
   ip_class = None
   if NETADDR_PRE_0_7:
       ip_class = netaddr.IP
   else:
        ip_class = netaddr.ip.IPAddress
   if isinstance(ip, ip_class) or ip == "":
      return ip
   else:
      return ip_class(ip)

def get_config_filename(sys,interface):
    """
    The configuration file for each system pxe uses is either
    a form of the MAC address of the hex version of the IP.  If none
    of that is available, just use the given name, though the name
    given will be unsuitable for PXE configuration (For this, check
    system.is_management_supported()).  This same file is used to store
    system config information in the Apache tree, so it's still relevant.
    """

    interface = str(interface)
    if not sys.interfaces.has_key(interface):
        return None

    if sys.name == "default":
        return "default"
    mac = sys.get_mac_address(interface)
    ip  = sys.get_ip_address(interface)
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
    # needs testcase
    if strdata is None:
        return False
    if re.search(r'[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F:0-9]{2}:[A-F:0-9]{2}',strdata, re.IGNORECASE):
        return True
    return False

def get_random_mac(api_handle,virt_type="xenpv"):
    """
    Generate a random MAC address.
    from xend/server/netif.py
    return: MAC address string
    """
    if virt_type.startswith("vmware"):
        mac = [ 0x00, 0x50, 0x56,
            random.randint(0x00, 0x3f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)
        ]
    elif virt_type.startswith("xen") or virt_type.startswith("qemu"):
        mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) 
        ]
    else:
        raise CX("virt mac assignment not yet supported")

        
    mac = ':'.join(map(lambda x: "%02x" % x, mac))
    systems = api_handle.systems()
    while ( systems.find(mac_address=mac) ):
        mac = get_random_mac(api_handle)

    return mac


def resolve_ip(strdata):
    """
    Resolve the IP address and handle errors...
    """
    try:
        return socket.gethostbyname(strdata)
    except:
        return None


def find_matching_files(directory,regex):
    """
    Find all files in a given directory that match a given regex.
    Can't use glob directly as glob doesn't take regexen.
    """
    files = glob.glob(os.path.join(directory,"*"))
    results = []
    for f in files:
       if regex.match(os.path.basename(f)):
           results.append(f)
    return results


def find_highest_files(directory,unversioned,regex):
    """
    Find the highest numbered file (kernel or initrd numbering scheme)
    in a given directory that matches a given pattern.  Used for
    auto-booting the latest kernel in a directory.
    """
    files = find_matching_files(directory, regex)
    get_numbers = re.compile(r'(\d+).(\d+).(\d+)')
    def max2(a, b):
        """Returns the larger of the two values"""
        av  = get_numbers.search(os.path.basename(a)).groups()
        bv  = get_numbers.search(os.path.basename(b)).groups()

        ret = cmp(av[0], bv[0]) or cmp(av[1], bv[1]) or cmp(av[2], bv[2])
        if ret < 0:
            return b
        return a

    if len(files) > 0:
        return reduce(max2, files)

    # couldn't find a highest numbered file, but maybe there
    # is just a 'vmlinuz' or an 'initrd.img' in this directory?
    last_chance = os.path.join(directory,unversioned)
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
        #filename = os.path.basename(path)
        #if _re_kernel.match(filename):
        #   return path
        #elif filename == "vmlinuz":
        #   return path
        return path
    elif os.path.isdir(path):
        return find_highest_files(path,"vmlinuz",_re_kernel)
    return None

def remove_yum_olddata(path,logger=None):
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
        #filename = os.path.basename(path)
        #if _re_initrd.match(filename):
        #   return path
        #if filename == "initrd.img" or filename == "initrd":
        #   return path
        return path
    elif os.path.isdir(path):
        return find_highest_files(path,"initrd.img",_re_initrd)
    return None


def find_kickstart(url):
    """
    Check if a kickstart url looks like an http, ftp, nfs or local path.
    If a local path is used, cobbler will copy the kickstart and serve
    it over http.
    """
    if url is None:
        return None
    x = url.lower()
    for y in ["http://","nfs://","ftp://","/"]:
       if x.startswith(y):
           if x.startswith("/") and not os.path.isfile(url):
               return None
           return url
    return None

def input_string_or_list(options):
    """
    Accepts a delimited list of stuff or a list, but always returns a list.
    """
    delim = None
    if options == "<<inherit>>":
       return "<<inherit>>"
    if options is None or options == "" or options == "delete":
       return []
    elif type(options) == list:
       return options
    elif isinstance(options,basestring):
       tokens = options.split(delim)
       return tokens
    else:
       raise CX(_("invalid input type"))

def input_string_or_hash(options,allow_multiples=True):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options == "<<inherit>>":
        options = {}

    if options is None or options == "delete":
        return (True, {})
    elif type(options) == list:
        raise CX(_("No idea what to do with list: %s") % options)
    elif type(options) == str:
        new_dict = {}
        tokens = shlex.split(options)
        for t in tokens:
            tokens2 = t.split("=",1)
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
                if type(new_dict[key]) == list:
                    new_dict[key].append(value)
                else:
                    new_dict[key] = [new_dict[key], value]
            else:
                new_dict[key] = value
        # make sure we have no empty entries
        new_dict.pop('', None)
        return (True, new_dict)
    elif type(options) == dict:
        options.pop('',None)
        return (True, options)
    else:
        raise CX(_("invalid input type"))

def input_boolean(value):
    value = str(value)
    if value.lower() in [ "true", "1", "on", "yes", "y" ]:
       return True
    else:
       return False

def grab_tree(api_handle, obj):
    """
    Climb the tree and get every node.
    """
    settings = api_handle.settings()
    results = [ obj ]
    parent = obj.get_parent()
    while parent is not None:
       results.append(parent)
       parent = parent.get_parent()
    results.append(settings)  
    return results

def blender(api_handle,remove_hashes, root_obj):
    """
    Combine all of the data in an object tree from the perspective
    of that point on the tree, and produce a merged hash containing
    consolidated data.
    """
 
    settings = api_handle.settings()
    tree = grab_tree(api_handle, root_obj)
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node,results)

    # hack -- s390 nodes get additional default kernel options
    arch = results.get("arch","?")
    if arch.startswith("s390"):
        keyz = settings.kernel_options_s390x.keys()
        for k in keyz:
           if not results.has_key(k):
               results["kernel_options"][k] = settings.kernel_options_s390x[k]

    # Get topmost object to determine which breed we're dealing with
    parent = root_obj.get_parent()
    if parent is None:
        parent = root_obj

    while parent.COLLECTION_TYPE is "profile" or parent.COLLECTION_TYPE is "system":
        parent = parent.get_parent()

    breed = parent.breed

    if breed == "redhat":
        # determine if we have room to add kssendmac to the kernel options line
        kernel_txt = hash_to_string(results["kernel_options"])
        if len(kernel_txt) < 244:
            results["kernel_options"]["kssendmac"] = None

    # convert post kernel options to string
    if results.has_key("kernel_options_post"):
        results["kernel_options_post"] = hash_to_string(results["kernel_options_post"])


    # make interfaces accessible without Cheetah-voodoo in the templates
    # EXAMPLE:  $ip == $ip0, $ip1, $ip2 and so on.
 
    if root_obj.COLLECTION_TYPE == "system":
        for (name,interface) in root_obj.interfaces.iteritems():
            for key in interface.keys():
                results["%s_%s" % (key,name)] = interface[key]
                # just to keep templates backwards compatibile
                if name == "intf0":
                    # prevent stomping on profile variables, which really only happens
                    # with the way we check for virt_bridge, which is a profile setting
                    # and an interface setting
                    if not results.has_key(key):
                        results[key] = interface[key]

    http_port = results.get("http_port",80)
    if http_port not in (80, "80"):
       results["http_server"] = "%s:%s" % (results["server"] , http_port)
    else:
       results["http_server"] = results["server"]

    mgmt_parameters = results.get("mgmt_parameters",{})
    mgmt_parameters.update(results.get("ks_meta", {}))
    results["mgmt_parameters"] = mgmt_parameters
 
    # sanitize output for koan and kernel option lines, etc
    if remove_hashes:
        results = flatten(results)

    # the password field is inputed as escaped strings but Cheetah
    # does weird things when expanding it due to multiple dollar signs
    # so this is the workaround
    if results.has_key("default_password_crypted"):
        results["default_password_crypted"] = results["default_password_crypted"].replace("\$","$")

    # add in some variables for easier templating
    # as these variables change based on object type
    if results.has_key("interfaces"):
        # is a system object
        results["system_name"]  = results["name"]
        results["profile_name"] = results["profile"]
        if results.has_key("distro"):
            results["distro_name"]  = results["distro"]
        elif results.has_key("image"):
            results["distro_name"]  = "N/A"
            results["image_name"]   = results["image"]
    elif results.has_key("distro"):
        # is a profile or subprofile object
        results["profile_name"] = results["name"]
        results["distro_name"]  = results["distro"]
    elif results.has_key("kernel"):
        # is a distro object
        results["distro_name"]  = results["name"]
    elif results.has_key("file"):
        # is an image object
        results["distro_name"]  = "N/A"
        results["image_name"]   = results["name"]

    return results

def flatten(data):
    # convert certain nested hashes to strings.
    # this is only really done for the ones koan needs as strings
    # this should not be done for everything
    if data is None:
        return None
    if data.has_key("environment"):
        data["environment"] = hash_to_string(data["environment"])
    if data.has_key("kernel_options"):
        data["kernel_options"] = hash_to_string(data["kernel_options"])
    if data.has_key("kernel_options_post"):
        data["kernel_options_post"] = hash_to_string(data["kernel_options_post"])
    if data.has_key("yumopts"):
        data["yumopts"]        = hash_to_string(data["yumopts"])
    if data.has_key("ks_meta"):
        data["ks_meta"] = hash_to_string(data["ks_meta"])
    if data.has_key("template_files"):
        data["template_files"] = hash_to_string(data["template_files"])
    if data.has_key("repos") and type(data["repos"]) == list:
        data["repos"]   = " ".join(data["repos"])
    if data.has_key("rpm_list") and type(data["rpm_list"]) == list:
        data["rpm_list"] = " ".join(data["rpm_list"])

    # note -- we do not need to flatten "interfaces" as koan does not expect
    # it to be a string, nor do we use it on a kernel options line, etc...
 
    return data

def uniquify(seq, idfun=None): 
    # credit: http://www.peterbe.com/plog/uniqifiers-benchmark
    # FIXME: if this is actually slower than some other way, overhaul it
    if idfun is None:
        def idfun(x): 
           return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result

def __consolidate(node,results):
    """
    Merge data from a given node with the aggregate of all
    data from past scanned nodes.  Hashes and arrays are treated
    specially.
    """
    node_data =  node.to_datastruct()

    # if the node has any data items labelled <<inherit>> we need to expunge them.
    # so that they do not override the supernodes.
    node_data_copy = {}
    for key in node_data:
       value = node_data[key]
       if value != "<<inherit>>":
          if type(value) == type({}):
              node_data_copy[key] = value.copy()
          elif type(value) == type([]):
              node_data_copy[key] = value[:]
          else:
              node_data_copy[key] = value

    for field in node_data_copy:

       data_item = node_data_copy[field] 
       if results.has_key(field):
 
          # now merge data types seperately depending on whether they are hash, list,
          # or scalar.

          fielddata = results[field]

          if type(fielddata) == dict:
             # interweave hash results
             results[field].update(data_item.copy())
          elif type(fielddata) == list or type(fielddata) == tuple:
             # add to lists (cobbler doesn't have many lists)
             # FIXME: should probably uniqueify list after doing this
             results[field].extend(data_item)
             results[field] = uniquify(results[field])
          else:
             # just override scalars
             results[field] = data_item
       else:
          results[field] = data_item

    # now if we have any "!foo" results in the list, delete corresponding
    # key entry "foo", and also the entry "!foo", allowing for removal
    # of kernel options set in a distro later in a profile, etc.

    hash_removals(results,"kernel_options")
    hash_removals(results,"kernel_options_post")
    hash_removals(results,"ks_meta")
    hash_removals(results,"template_files")

def hash_removals(results,subkey):
    if not results.has_key(subkey):
        return
    scan = results[subkey].keys()
    for k in scan:
        if str(k).startswith("!") and k != "!":
           remove_me = k[1:]
           if results[subkey].has_key(remove_me):
               del results[subkey][remove_me]
           del results[subkey][k]

def hash_to_string(hash):
    """
    Convert a hash to a printable string.
    used primarily in the kernel options string
    and for some legacy stuff where koan expects strings
    (though this last part should be changed to hashes)
    """
    buffer = ""
    if type(hash) != dict:
       return hash
    for key in hash:
       value = hash[key]
       if value is None:
           buffer = buffer + str(key) + " "
       elif type(value) == list:
           # this value is an array, so we print out every
           # key=value
           for item in value:
              buffer = buffer + str(key) + "=" + str(item) + " "
       else:
          buffer = buffer + str(key) + "=" + str(value) + " "
    return buffer

def run_triggers(api,ref,globber,additional=[],logger=None):
    """
    Runs all the trigger scripts in a given directory.
    ref can be a cobbler object, if not None, the name will be passed
    to the script.  If ref is None, the script will be called with
    no argumenets.  Globber is a wildcard expression indicating which
    triggers to run.  Example:  "/var/lib/cobbler/triggers/blah/*"

    As of Cobbler 1.5.X, this also runs cobbler modules that match the globbing paths.
    """

    # Python triggers first, before shell

    modules = api.get_modules_in_category(globber)
    for m in modules:
       arglist = []
       if ref:
           arglist.append(ref.name)
       for x in additional:
           arglist.append(x)
       rc = m.run(api, arglist, logger)
       if rc != 0:
           raise CX("cobbler trigger failed: %s" % m.__name__)

    # now do the old shell triggers, which are usually going to be slower, but are easier to write  
    # and support any language

    triggers = glob.glob(globber)
    triggers.sort()
    for file in triggers:
        try:
            if file.startswith(".") or file.find(".rpm") != -1:
                # skip dotfiles or .rpmnew files that may have been installed
                # in the triggers directory
                continue
            arglist = [ file ]
            if ref:
                arglist.append(ref.name)
            for x in additional:
                arglist.append(x)
            rc = subprocess_call(logger, arglist, shell=False) # close_fds=True)
        except:
            if logger is not None:
               logger.warning("failed to execute trigger: %s" % file)
            continue

        if rc != 0:
            raise CX(_("cobbler trigger failed: %(file)s returns %(code)d") % { "file" : file, "code" : rc })

def fix_mod_python_select_submission(repos):
    """ 
    WARNING: this is a heinous hack to convert mod_python submitted form data
    to something usable.  Ultimately we need to fix the root cause of this
    which doesn't seem to happen on all versions of python/mp.
    """

    # should be nice regex, but this is readable :)
    repos = str(repos)
    repos = repos.replace("'repos'","")
    repos = repos.replace("'","")
    repos = repos.replace("[","")
    repos = repos.replace("]","")
    repos = repos.replace("Field(","")
    repos = repos.replace(")","")
    repos = repos.replace(",","")
    repos = repos.replace('"',"")
    repos = repos.lstrip().rstrip()
    return repos

def check_dist():
    """
    Determines what distro we're running under.  
    """
    if os.path.exists("/etc/debian_version"):
       return "debian"
    elif os.path.exists("/etc/SuSE-release"):
       return "suse"
    else:
       # valid for Fedora and all Red Hat / Fedora derivatives
       return "redhat"

def os_release():

   if check_dist() == "redhat":
      fh = open("/etc/redhat-release")
      data = fh.read().lower()
      if data.find("fedora") != -1:
         make = "fedora"
      elif data.find("centos") != -1:
         make = "centos"
      else:
         make = "redhat"
      release_index = data.find("release") 
      rest = data[release_index+7:-1]
      tokens = rest.split(" ")
      for t in tokens:
         try:
             return (make,float(t))
         except ValueError, ve:
             pass
      raise CX("failed to detect local OS version from /etc/redhat-release")

   elif check_dist() == "debian":
      fd = open("/etc/debian_version")
      parts = fd.read().split(".")
      version = parts[0]
      rest = parts[1]
      make = "debian"
      return (make, float(version))
   elif check_dist() == "suse":
      fd = open("/etc/SuSE-release")
      for line in fd.read().split("\n"):
         if line.find("VERSION") != -1:
            version = line.replace("VERSION = ","")
         if line.find("PATCHLEVEL") != -1:
            rest = line.replace("PATCHLEVEL = ","")
      make = "suse"
      return (make, float(version))
   else:
      return ("unknown",0)

def tftpboot_location():

    # if possible, read from TFTP config file to get the location
    if os.path.exists("/etc/xinetd.d/tftp"):
        fd = open("/etc/xinetd.d/tftp")
        lines = fd.read().split("\n")
        for line in lines:
           if line.find("server_args") != -1:
              tokens = line.split(None)
              mark = False
              for t in tokens:
                 if t == "-s":    
                    mark = True
                 elif mark:
                    return t

    # otherwise, guess based on the distro
    (make,version) = os_release()
    if make == "fedora" and version >= 9:
       return "/var/lib/tftpboot"
    return "/tftpboot"

def can_do_public_content(api):
    """
    Returns whether we can use public_content_t which greatly
    simplifies SELinux usage.
    """
    (dist, ver) = api.get_os_details()
    if dist == "redhat" and ver <= 4:
       return False
    return True

def is_safe_to_hardlink(src,dst,api):
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

def linkfile(src, dst, symlink_ok=False, api=None, logger=None):
    """
    Attempt to create a link dst that points to src.  Because file
    systems suck we attempt several different methods or bail to
    copyfile()
    """

    if api is None:
        # FIXME: this really should not be a keyword
        # arg
        raise "Internal error: API handle is required"

    is_remote = is_remote_file(src)

    if os.path.exists(dst):
        # if the destination exists, is it right in terms of accuracy
        # and context?
        if os.path.samefile(src, dst):
            if not is_safe_to_hardlink(src,dst,api):
                # may have to remove old hardlinks for SELinux reasons
                # as previous implementations were not complete
                if logger is not None:
                   logger.info("removing: %s" % dst)
                os.remove(dst)
            else:
                return True
        elif os.path.islink(dst):
            # existing path exists and is a symlink, update the symlink
            if logger is not None:
               logger.info("removing: %s" % dst)
            os.remove(dst)

    if is_safe_to_hardlink(src,dst,api):
        # we can try a hardlink if the destination isn't to NFS or Samba
        # this will help save space and sync time.
        try:
            if logger is not None:
                logger.info("trying hardlink %s -> %s" % (src,dst))
            rc = os.link(src, dst)
            return rc
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
                logger.info("trying symlink %s -> %s" % (src,dst))
            rc = os.symlink(src, dst)
            return rc
        except (IOError, OSError):
            pass

    # we couldn't hardlink and we couldn't symlink so we must copy

    return copyfile(src, dst, api=api, logger=logger)

def copyfile(src,dst,api=None,logger=None):
    try:
        if logger is not None:
           logger.info("copying: %s -> %s" % (src,dst))
        rc = shutil.copyfile(src,dst)
        return rc
    except:
        if not os.access(src,os.R_OK):
            raise CX(_("Cannot read: %s") % src)
        if not os.path.samefile(src,dst):
            # accomodate for the possibility that we already copied
            # the file as a symlink/hardlink
            raise
            # traceback.print_exc()
            # raise CX(_("Error copying %(src)s to %(dst)s") % { "src" : src, "dst" : dst})

def check_openfiles(src):
    """
    Used to check for open files on a mounted partition.
    """
    try:
        if not os.path.isdir(src):
            raise CX(_("Error in check_openfiles: the source (%s) must be a directory") % src)
        cmd = [ "/usr/sbin/lsof", "+D", src, "-Fn", "|", "wc", "-l" ]
        handle = sub_process.Popen(cmd, shell=True, stdout=sub_process.PIPE, close_fds=True)
        out = handle.stdout
        results = out.read()
        return int(results)
    except:
        if not os.access(src,os.R_OK):
            raise CX(_("Cannot read: %s") % src)
        if not os.path.samefile(src,dst):
            # accomodate for the possibility that we already copied
            # the file as a symlink/hardlink
            raise


def copyfile_pattern(pattern,dst,require_match=True,symlink_ok=False,api=None,logger=None):
    files = glob.glob(pattern)
    if require_match and not len(files) > 0:
        raise CX(_("Could not find files matching %s") % pattern)
    for file in files:
        base = os.path.basename(file)
        dst1 = os.path.join(dst,os.path.basename(file))
        linkfile(file,dst1,symlink_ok=symlink_ok,api=api,logger=logger)

def rmfile(path,logger=None):
    try:
        if logger is not None:
           logger.info("removing: %s" % path)
        os.unlink(path)
        return True
    except OSError, ioe:
        if not ioe.errno == errno.ENOENT: # doesn't exist
            if logger is not None:
                log_exc(logger)
            raise CX(_("Error deleting %s") % path)
        return True

def rmtree_contents(path,logger=None):
   what_to_delete = glob.glob("%s/*" % path)
   for x in what_to_delete:
       rmtree(x,logger=logger)

def rmtree(path,logger=None):
   try:
       if os.path.isfile(path):
           return rmfile(path,logger=logger)
       else:
           if logger is not None:
               logger.info("removing: %s" % path)
           return shutil.rmtree(path,ignore_errors=True)
   except OSError, ioe:
       if logger is not None:
           log_exc(logger)
       if not ioe.errno == errno.ENOENT: # doesn't exist
           raise CX(_("Error deleting %s") % path)
       return True

def mkdir(path,mode=0777,logger=None):
   try:
       if logger is not None:
          logger.info("mkdir: %s" % path)
       return os.makedirs(path,mode)
   except OSError, oe:
       if not oe.errno == 17: # already exists (no constant for 17?)
           if logger is not None:
               log_exc(logger)
           raise CX(_("Error creating") % path)

def set_redhat_management_key(self,key):
   self.redhat_management_key = key
   return True

def set_redhat_management_server(self,server):
   self.redhat_management_server = server
   return True

def set_arch(self,arch,repo=False):
   if arch is None or arch == "" or arch == "standard" or arch == "x86":
       arch = "i386"

   if repo:
       valids = [ "i386", "x86_64", "ia64", "ppc", "ppc64", "s390", "s390x", "noarch", "src" ]
   else:
       valids = [ "i386", "x86_64", "ia64", "ppc", "ppc64", "s390", "s390x" ]

   if arch in valids:
       self.arch = arch
       return True

   raise CX("arch choices include: %s" % ", ".join(valids))

def set_os_version(self,os_version):
   if os_version == "" or os_version is None:
      self.os_version = ""
      return True
   self.os_version = os_version.lower()
   if self.breed is None or self.breed == "":
      raise CX(_("cannot set --os-version without setting --breed first"))
   if not self.breed in codes.VALID_OS_BREEDS:
      raise CX(_("fix --breed first before applying this setting"))
   matched = codes.VALID_OS_VERSIONS[self.breed]
   if not os_version in matched:
      nicer = ", ".join(matched)
      raise CX(_("--os-version for breed %s must be one of %s, given was %s") % (self.breed, nicer, os_version))
   self.os_version = os_version
   return True

def set_breed(self,breed):
   valid_breeds = codes.VALID_OS_BREEDS
   if breed is not None and breed.lower() in valid_breeds:
       self.breed = breed.lower()
       return True
   nicer = ", ".join(valid_breeds)
   raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support") % (breed, nicer))

def set_repo_os_version(self,os_version):
   if os_version == "" or os_version is None:
      self.os_version = ""
      return True
   self.os_version = os_version.lower()
   if self.breed is None or self.breed == "":
      raise CX(_("cannot set --os-version without setting --breed first"))
   if not self.breed in codes.VALID_REPO_BREEDS:
      raise CX(_("fix --breed first before applying this setting"))
   self.os_version = os_version
   return True

def set_repo_breed(self,breed):
   valid_breeds = codes.VALID_REPO_BREEDS
   if breed is not None and breed.lower() in valid_breeds:
       self.breed = breed.lower()
       return True
   nicer = ", ".join(valid_breeds)
   raise CX(_("invalid value for --breed (%s), must be one of %s, different breeds have different levels of support") % (breed, nicer))

def set_repos(self,repos,bypass_check=False):
   # WARNING: hack
   # repos = fix_mod_python_select_submission(repos)

   # allow the magic inherit string to persist
   if repos == "<<inherit>>":
        self.repos = "<<inherit>>"
        return True

   # store as an array regardless of input type
   if repos is None:
        self.repos = []
   else:
        self.repos = input_string_or_list(repos)
   if bypass_check:
       return True

   for r in self.repos:
       if self.config.repos().find(name=r) is None:
          raise CX(_("repo %s is not defined") % r)

   return True

def set_virt_file_size(self,num):
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
        return True

    if num == "<<inherit>>":
        self.virt_file_size = "<<inherit>>"
        return True

    if type(num) == str and num.find(",") != -1:
        tokens = num.split(",")
        for t in tokens:
            # hack to run validation on each
            self.set_virt_file_size(t)
        # if no exceptions raised, good enough
        self.virt_file_size = num
        return True

    try:
        inum = int(num)
        if inum != float(num):
            return CX(_("invalid virt file size (%s)" % num))
        if inum >= 0:
            self.virt_file_size = inum
            return True
        raise CX(_("invalid virt file size (%s)" % num))
    except:
        raise CX(_("invalid virt file size (%s)" % num))
    return True

def set_virt_auto_boot(self,num):
    """
    For Virt only.
    Specifies whether the VM should automatically boot upon host reboot
    0 tells Koan not to auto_boot virtuals
    """

    if num == "<<inherit>>":
        self.virt_auto_boot = "<<inherit>>"
        return True

    # num is a non-negative integer (0 means default)
    try:
        inum = int(num)
        if (inum == 0) or (inum == 1):
            self.virt_auto_boot = inum
            return True
        return CX(_("invalid virt_auto_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % inum))
    except:
        return CX(_("invalid virt_auto_boot value (%s): value must be either '0' (disabled) or '1' (enabled)" % inum))
    return True

def set_virt_ram(self,num):
    """
    For Virt only.
    Specifies the size of the Virt RAM in MB.
    0 tells Koan to just choose a reasonable default.
    """

    if num == "<<inherit>>":
        self.virt_ram = "<<inherit>>"
        return True

    # num is a non-negative integer (0 means default)
    try:
        inum = int(num)
        if inum != float(num):
            return CX(_("invalid virt ram size (%s)" % num))
        if inum >= 0:
            self.virt_ram = inum
            return True
        return CX(_("invalid virt ram size (%s)" % num))
    except:
        return CX(_("invalid virt ram size (%s)" % num))
    return True

def set_virt_type(self,vtype):
    """
    Virtualization preference, can be overridden by koan.
    """

    if vtype == "<<inherit>>":
        self.virt_type == "<<inherit>>"
        return True

    if vtype.lower() not in [ "qemu", "xenpv", "xenfv", "vmware", "vmwarew", "auto" ]:
        raise CX(_("invalid virt type (%s)" % vtype))
    self.virt_type = vtype
    return True

def set_virt_bridge(self,vbridge):
    """
    The default bridge for all virtual interfaces under this profile.
    """
    if vbridge is None or vbridge == "":
       vbridge = self.settings.default_virt_bridge
    self.virt_bridge = vbridge
    return True

def set_virt_path(self,path,for_system=False):
    """
    Virtual storage location suggestion, can be overriden by koan.
    """
    if path is None:
       path = ""
    if for_system:
       if path == "":
          path = "<<inherit>>"
    self.virt_path = path
    return True

def set_virt_cpus(self,num):
    """
    For Virt only.  Set the number of virtual CPUs to give to the
    virtual machine.  This is fed to virtinst RAW, so cobbler
    will not yelp if you try to feed it 9999 CPUs.  No formatting
    like 9,999 please :)
    """
    if num == "" or num is None:
        self.virt_cpus = 1
        return True

    if num == "<<inherit>>":
        self.virt_cpus = "<<inherit>>"
        return True

    try:
        num = int(str(num))
    except:
        raise CX(_("invalid number of virtual CPUs (%s)" % num))

    self.virt_cpus = num
    return True

def get_kickstart_templates(api):
    files = {}
    for x in api.profiles():
        if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
            if os.path.exists(x.kickstart):
                files[x.kickstart] = 1
    for x in api.systems():
        if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
            if os.path.exists(x.kickstart):
                files[x.kickstart] = 1
    for x in glob.glob("/var/lib/cobbler/kickstarts/*"):
        if os.path.isfile(x):
            files[x] = 1
    for x in glob.glob("/etc/cobbler/*.ks"):
        if os.path.isfile(x):
            files[x] = 1

    results = files.keys()
    results.sort()
    return results

def safe_filter(var):
    if var is None:
       return
    if var.find("..") != -1 or var.find(";") != -1:
       raise CX("Invalid characters found in input")

def is_selinux_enabled():
    if not os.path.exists("/usr/sbin/selinuxenabled"):
       return False
    args = "/usr/sbin/selinuxenabled"
    selinuxenabled = sub_process.call(args,close_fds=True)
    if selinuxenabled == 0:
        return True
    else:
        return False

import os
import sys
import random

# We cache the contents of /etc/mtab ... the following variables are used 
# to keep our cache in sync
mtab_mtime = None
mtab_map = []

class MntEntObj(object):
    mnt_fsname = None #* name of mounted file system */
    mnt_dir = None    #* file system path prefix */
    mnt_type = None   #* mount type (see mntent.h) */
    mnt_opts = None   #* mount options (see mntent.h) */
    mnt_freq = 0      #* dump frequency in days */
    mnt_passno = 0    #* pass number on parallel fsck */

    def __init__(self,input=None):
        if input and isinstance(input, str):
            (self.mnt_fsname, self.mnt_dir, self.mnt_type, self.mnt_opts, \
             self.mnt_freq, self.mnt_passno) = input.split()
    def __dict__(self):
        return {"mnt_fsname": self.mnt_fsname, "mnt_dir": self.mnt_dir, \
                "mnt_type": self.mnt_type, "mnt_opts": self.mnt_opts, \
                "mnt_freq": self.mnt_freq, "mnt_passno": self.mnt_passno}
    def __str__(self):
        return "%s %s %s %s %s %s" % (self.mnt_fsname, self.mnt_dir, self.mnt_type, \
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
    global mtab_mtime

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
    for ent in get_mtab():
        mtab_dict[ent.mnt_dir] = ent.mnt_fsname

    # find a best match
    fdir = os.path.dirname(fname)
    match = mtab_dict.has_key(fdir)
    while not match:
        fdir = os.path.realpath(os.path.join(fdir, os.path.pardir))
        match = mtab_dict.has_key(fdir)

    # construct file path relative to device
    if fdir != os.path.sep:
        fname = fname[len(fdir):]

    return (mtab_dict[fdir], fname)

def is_remote_file(file):
    (dev, path) = get_file_device_path(file)
    if dev.find(":") != -1:
       return True
    else:
       return False 

def subprocess_call(logger, cmd, shell=True):
    logger.info("running: %s" % cmd)
    try:
       rc = sub_process.call(cmd, shell=shell, stdout=logger.handle(), stderr=logger.handle(), close_fds=True)
    except OSError:
       log_exc(logger)
       if not isinstance(cmd, basestring):
          cmd = str(" ".join(cmd))
       die(logger, "OS Error, command not found?  While running: %s" % cmd)
    logger.info("returned: %s" % rc)
    return rc

def subprocess_get(logger, cmd, shell=True):
    logger.info("running: %s" % cmd)
    sp = sub_process.Popen(cmd, shell=shell, stdout=sub_process.PIPE, stderr=sub_process.PIPE)
    data = sp.communicate()[0] 
    logger.info("received: %s" % data)
    return data

def popen2(args, **kwargs):
    """ 
    Leftovers from borrowing some bits from Snake, replace this 
    function with just the subprocess call.
    """
    p = sub_process.Popen(args, stdout=sub_process.PIPE, stdin=sub_process.PIPE, **kwargs)
    return (p.stdout, p.stdin)

def ram_consumption_of_guests(host, api):
    guest_names = host.virt_guests
    ttl_ram = 0
    if len(guest_names) == 0:
       # a system with no virt hosts already is our best
       # candidate
       return 0

    for g in guest_names:
       host_obj = api.find_system(g)
       if host_obj is None:
          # guest object was deleted but host was not updated
          continue
       host_data = blender(api,False,host_obj)
       ram = host_data.get("virt_ram", 512)
       ttl_ram = ttl_ram + host_data["virt_ram"]
    return ttl_ram



def choose_virt_host(systems, api):
    """
    From a list of systems, choose a system that can best host a virtual
    machine.  This initial engine is not as optimal as it could be, but
    works by determining the system with the least amount of VM RAM deployed
    as defined by the amount of virtual ram on each guest for each guest
    that the hosts hosts.  Hop on pop.  

    This does assume hosts are reasonably homogenous.  In the future
    this heuristic should be pluggable and be able to tap into other
    external data sources and maybe basic usage stats.
    """
     
    if len(systems) == 0:
       raise CX("empty candidate systems list")
    by_name = {}
    least_host = systems[0] 
    least_host_ct = -1
    for s in systems:
       ct = ram_consumption_of_guests(s, api)
       if (ct < least_host_ct) or (least_host_ct == -1):
          least_host = s
          least_host_ct = ct
    return least_host.name

def os_system(cmd):
    """
    os.system doesn't close file descriptors, so this is a wrapper
    to ensure we never use it.
    """
    rc = sub_process.call(cmd, shell=True, close_fds=True)
    return rc

def clear_from_fields(obj, fields, is_subobject=False):
    """
    Used by various item_*.py classes for automating datastructure boilerplate.
    """
    for elems in fields:
        # if elems startswith * it's an interface field and we do not operate on it.
        if elems[0].startswith("*") or elems[0].find("widget") != -1:
           continue
        if is_subobject:
           val = elems[2]
        else:
           val = elems[1]
        if isinstance(val,basestring):
           if val.startswith("SETTINGS:"):
               setkey = val.split(":")[-1]
               val = getattr(obj.settings, setkey)
        setattr(obj, elems[0], val)

    if obj.COLLECTION_TYPE == "system":
        obj.interfaces = {}

def from_datastruct_from_fields(obj, seed_data, fields):

    for elems in fields:
        # we don't have to load interface fields here
        if elems[0].startswith("*") or elems[0].find("widget") != -1:
            continue
        k = elems[0]
        if seed_data.has_key(k):
            setattr(obj, k, seed_data[k])

    if obj.uid == '':
        obj.uid = obj.config.generate_uid()

    # special handling for interfaces
    if obj.COLLECTION_TYPE == "system":
        obj.interfaces = copy.deepcopy(seed_data["interfaces"])

    return obj

def get_methods_from_fields(obj, fields):
    ds = {}
    for elem in fields:
        k = elem[0]
        # modify interfaces is handled differently, and need not work this way
        if k.startswith("*") or k.find("widget") != -1:
            continue
        setfn = getattr(obj, "set_%s" % k)
        ds[k] = setfn
    return ds

def to_datastruct_from_fields(obj, fields):
    ds = {}
    for elem in fields:
        k = elem[0]
        if k.startswith("*") or k.find("widget") != -1:
            continue
        data = getattr(obj, k)
        ds[k] = data
    # interfaces on systems require somewhat special handling
    # they are the only exception in Cobbler.
    if obj.COLLECTION_TYPE == "system":
        ds["interfaces"] = copy.deepcopy(obj.interfaces)
    return ds

def printable_from_fields(obj, fields):
    """
    Obj is a hash datastructure, fields is something like item_distro.FIELDS
    """
    buf  = ""
    keys = []
    for elem in fields:
       keys.append((elem[0], elem[3], elem[4]))
    keys.sort()
    buf = buf + "%-30s : %s\n" % ("Name", obj["name"])
    for (k, nicename, editable) in keys:
       # FIXME: supress fields users don't need to see?
       # FIXME: interfaces should be sorted
       # FIXME: print ctime, mtime nicely
       if k.startswith("*") or not editable or k.find("widget") != -1:
           continue

       if k != "name":
           # FIXME: move examples one field over, use description here.
           buf = buf + "%-30s : %s\n" % (nicename, obj[k])

    # somewhat brain-melting special handling to print the hashes
    # inside of the interfaces more neatly.
    if obj.has_key("interfaces"):
       for iname in obj["interfaces"].keys():
          # FIXME: inames possibly not sorted
          buf = buf + "%-30s : %s\n" % ("Interface ===== ",iname)
          for (k, nicename, editable) in keys:
             nkey = k.replace("*","")
             if k.startswith("*") and editable:
                 buf = buf + "%-30s : %s\n" % (nicename, obj["interfaces"][iname].get(nkey,""))

    return buf

def matches_args(args, list_of):
    """
    Used to simplify some code around which arguments to add when.
    """
    for x in args:
        if x in list_of:
            return True
    return False

def add_options_from_fields(object_type, parser, fields, object_action):
    for elem in fields:
        k = elem[0] 
        if k.find("widget") != -1:
            continue
        # scrub interface tags so all fields get added correctly.
        k = k.replace("*","")
        default = elem[1]
        nicename = elem[3]
        tooltip = elem[5]
        choices = elem[6]
        if field_info.ALTERNATE_OPTIONS.has_key(k):
            niceopt = field_info.ALTERNATE_OPTIONS[k]
        else:
            niceopt = "--%s" % k.replace("_","-")
        desc = nicename
        if tooltip != "":
            desc = nicename + " (%s)" % tooltip


        if type(choices) == type([]) and len(choices) != 0:
            desc = desc + " (valid options: %s)" % ",".join(choices)    
            parser.add_option(niceopt, dest=k, help=desc, choices=choices)
        else:
            parser.add_option(niceopt, dest=k, help=desc)


    # FIXME: not supported in 2.0?
    if not object_action in ["dumpvars","find","remove","report","list"]: 
        # FIXME: implement
        parser.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")
        parser.add_option("--in-place", action="store_true", default=False, dest="in_place", help="edit items in kopts or ksmeta without clearing the other items")
    if object_action in ["copy","rename"]:
        parser.add_option("--newname", help="new object name")
    # FIXME: not supported in 2.0 ?
    #if not object_action in ["dumpvars","find","remove","report","list"]: 
    #    parser.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
    # FIXME: not supported in 2.0 ?
    # if not matches_args(args,["dumpvars","report","list"]):
    #    parser.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
    if object_action in ["remove"]:
        parser.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")
    if object_type == "system":
        # system object
        parser.add_option("--interface", dest="interface", default="eth0", help="which interface to edit")
        parser.add_option("--delete-interface", dest="delete_interface", action="store_true")


def get_remote_methods_from_fields(obj,fields):
    """
    Return the name of set functions for all fields, keyed by the field name.
    """
    ds = {}
    for elem in fields:
       name = elem[0].replace("*","")
       if name.find("widget") == -1:
          ds[name] = getattr(obj,"set_%s" % name)
    if obj.COLLECTION_TYPE == "system":
       ds["modify_interface"] = getattr(obj,"modify_interface")
       ds["delete_interface"] = getattr(obj,"delete_interface")
    return ds

def get_power_types():
    """
    Return all possible power types
    """
    power_types = []
    power_template = re.compile(r'power_(.*).template')
    for x in glob.glob("/etc/cobbler/power/power_*.template"):
        power_types.append(power_template.search(x).group(1))
    return power_types

def get_power(powertype=None):
    """
    Return power command for type
    """
    if powertype:
        powerpath = "/etc/cobbler/power/power_%s.template" % powertype
        if os.path.isfile(powerpath):
            return powerpath
    return None

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

def strip_none(data, omit_none=False):
    """
    Remove "none" entries from datastructures.
    Used prior to communicating with XMLRPC.
    """
    if data is None:
        data = '~'

    elif type(data) == list:
        data2 = []
        for x in data:
            if omit_none and x is None:
                pass
            else:
                data2.append(strip_none(x))
        return data2

    elif type(data) == dict:
        data2 = {}
        for key in data.keys():
            keydata = data[key]
            if omit_none and data[key] is None:
                pass
            else:
                data2[str(key)] = strip_none(data[key])
        return data2

    return data

def cli_find_via_xmlrpc(remote, otype, options):
    """
    Given an options object and a remote handle, find options matching
    the criteria given.
    """
    criteria = strip_none2(options.__dict__)
    return remote.find_items(otype,criteria,"name",False)

# -------------------------------------------------------
    
def loh_to_hoh(datastruct, indexkey):
    """
    things like get_distros() returns a list of a hashes
    convert this to a hash of hashes keyed off of an arbitrary field

    EX:  [  { "a" : 2 }, { "a : 3 } ]  ->  { "2" : { "a" : 2 }, "3" : { "a" : "3" }

    """
    results = {}
    for item in datastruct:
        results[item[indexkey]] = item
    return results

# -------------------------------------------------------

def loh_sort_by_key(datastruct, indexkey):
    """
    Sorts a list of hashes by a given key in the hashes
    note: this is a destructive operation
    """
    datastruct.sort(lambda a, b: a[indexkey] < b[indexkey])
    return datastruct

def dhcpconf_location(api):
    version = api.os_version
    if version[0] in [ "redhat", "centos" ] and version[1] < 6:
        return "/etc/dhcpd.conf"
    elif version[0] in [ "fedora" ] and version[1] < 11: 
        return "/etc/dhcpd.conf"
    else:
        return "/etc/dhcp/dhcpd.conf"


if __name__ == "__main__":
    print os_release() # returns 2, not 3


