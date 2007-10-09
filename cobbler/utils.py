"""
Misc heavy lifting functions for cobbler

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import sys
import os
import re
import socket
import glob
import sub_process
import shutil
import string
import traceback
import logging
from cexceptions import *
from rhpl.translate import _, N_, textdomain, utf8

import api # factor out

_re_kernel = re.compile(r'vmlinuz(.*)')
_re_initrd = re.compile(r'initrd(.*).img')


def log_exc(logger):
   """
   Log an exception.
   """
   (t, v, tb) = sys.exc_info()
   logger.info("Exception occured: %s" % t )
   logger.info("Exception value: %s" % v)
   logger.info("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))


def trace_me():
   x = traceback.extract_stack()
   bar = string.join(traceback.format_list(x))
   return bar

def get_host_ip(ip):
    """
    Return the IP encoding needed for the TFTP boot tree.
    """
    handle = sub_process.Popen("/usr/bin/gethostip %s" % ip, shell=True, stdout=sub_process.PIPE)
    out = handle.stdout
    results = out.read()
    return results.split(" ")[-1][0:8]

def get_config_filename(sys,interface=0):
    """
    The configuration file for each system pxe uses is either
    a form of the MAC address of the hex version of the IP.  If none
    of that is available, just use the given name, though the name
    given will be unsuitable for PXE configuration (For this, check
    system.is_pxe_supported()).  This same file is used to store
    system config information in the Apache tree, so it's still relevant.
    """

    interface = str(interface)
    if not sys.interfaces.has_key(interface):
        raise CX(_("internal error:  probing an interface that does not exist"))

    if sys.name == "default":
        return "default"
    mac = sys.get_mac_address(interface)
    ip  = sys.get_ip_address(interface)
    if mac != None:
        return "01-" + "-".join(mac.split(":")).lower()
    elif ip != None:
        return get_host_ip(ip)
    else:
        return sys.name


def is_ip(strdata):
    """
    Return whether the argument is an IP address.  ipv6 needs
    to be added...
    """
    # needs testcase
    if strdata is None:
        return False
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',strdata):
        return True
    return False


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

def remove_yum_olddata(path):
    """
    Delete .olddata files that might be present from a failed run
    of createrepo.  
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
            print _("- removing: %s") % olddata
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

def input_string_or_hash(options,delim=","):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """
    if options is None:
        return (True, {})
    elif type(options) == list:
        raise CX(_("No idea what to do with list: %s") % options)
    elif type(options) == str:
        new_dict = {}
        tokens = options.split(delim)
        for t in tokens:
            tokens2 = t.split("=")
            if len(tokens2) == 1 and tokens2[0] != '':
                new_dict[tokens2[0]] = None
            elif len(tokens2) == 2 and tokens2[0] != '':
                new_dict[tokens2[0]] = tokens2[1]
            else:
                return (False, {})
        new_dict.pop('', None)
        return (True, new_dict)
    elif type(options) == dict:
        options.pop('',None)
        return (True, options)
    else:
        raise CX(_("Foreign options type"))

def grab_tree(obj):
    """
    Climb the tree and get every node.
    """
    settings = api.BootAPI().settings()
    results = [ obj ]
    parent = obj.get_parent()
    while parent is not None:
       results.append(parent)
       parent = parent.get_parent()
    results.append(settings)  
    return results

def blender(remove_hashes, root_obj):
    """
    Combine all of the data in an object tree from the perspective
    of that point on the tree, and produce a merged hash containing
    consolidated data.
    """
    settings = api.BootAPI().settings()
    tree = grab_tree(root_obj)
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node,results)

    # add in syslog to results (magic)    
    if settings.syslog_port != 0:
        if not results.has_key("kernel_options"):
            results["kernel_options"] = {}
        syslog = "%s:%s" % (settings.server, settings.syslog_port)
        results["kernel_options"]["syslog"] = syslog

    # determine if we have room to add kssendmac to the kernel options line
    kernel_txt = hash_to_string(results["kernel_options"])
    if len(kernel_txt) < 244:
        results["kernel_options"]["kssendmac"] = None

    # make interfaces accessible without Cheetah-voodoo in the templates
    # EXAMPLE:  $ip == $ip0, $ip1, $ip2 and so on.
 
    if root_obj.COLLECTION_TYPE == "system":
        counter = 0
        for (name,interface) in root_obj.interfaces.iteritems():
            for key in interface.keys():
                results["%s%d" % (key,counter)] = interface[key]
                # just to keep templates backwards compatibile
                if counter == 0:
                    results[key] = interface[key]
            counter = counter + 1

    # sanitize output for koan and kernel option lines, etc
    if remove_hashes:
        results = flatten(results)

    return results

def flatten(data):
    # convert certain nested hashes to strings.
    # FIXME: this function should be made more generic
    if data.has_key("kernel_options"):
        data["kernel_options"] = hash_to_string(data["kernel_options"])
    if data.has_key("ks_meta"):
        data["ks_meta"] = hash_to_string(data["ks_meta"])
    if data.has_key("repos") and type(data["repos"]) == list:
        data["repos"]   = " ".join(data["repos"])
    if data.has_key("rpm_list") and type(data["rpm_list"]) == list:
        data["rpm_list"] = " ".join(data["rpm_list"])

    # note -- we do not need to flatten "interfaces" as koan does not expect
    # it to be a string, nor do we use it on a kernel options line, etc...
 
    return data

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
 
          # FIXME: remove, we're doing this higher up
          #    for subobjects (child objects), a value of <<inherit>>
          #    means defer up the stack, and by definition usage of the API
          #    must ensure the value is valid somewhere up the stack.  So, remove
          #    any magic values of <<inherit>> prior to blending.
          #if data_item == '<<inherit>>':
          #   # don't load into results hash, the parent will have the
          #   # data we need.
          #   continue

          # now merge data types seperately depending on whether they are hash, list,
          # or scalar.
          if type(data_item) == dict:
             # interweave hash results
             results[field].update(data_item.copy())
          elif type(data_item) == list or type(data_item) == tuple:
             # add to lists (cobbler doesn't have many lists)
             # FIXME: should probably uniqueify list after doing this
             results[field].extend(data_item)
          else:
             # just override scalars
             results[field] = data_item
       else:
          results[field] = data_item

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
       else:
          buffer = buffer + str(key) + "=" + str(value) + " "
    return buffer

