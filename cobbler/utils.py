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
import random
import sub_process
import shutil
import string
import traceback
import errno
from cexceptions import *

#placeholder for translation
def _(foo):
   return foo


MODULE_CACHE = {}

# import api # factor out

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

def get_config_filename(sys,interface):
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

def get_random_mac(api_handle):
    """
    Generate a random MAC address.
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-16-3E, allocated to
    Xensource, Inc.  Last 3 fields are random.
    return: MAC address string
    """
    mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
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

def input_string_or_list(options,delim=","):
    """
    Accepts a delimited list of stuff or a list, but always returns a list.
    """
    if options is None or options == "delete":
       return []
    elif type(options) == list:
       return options
    elif type(options) == str:
       tokens = options.split(delim)
       if delim == ",":
           tokens = [t.lstrip().rstrip() for t in tokens]
       return tokens
    else:
       raise CX(_("invalid input type"))

def input_string_or_hash(options,delim=","):
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
        raise CX(_("invalid input type"))

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
 
    blend_key = "%s/%s/%s" % (root_obj.TYPE_NAME, root_obj.name, remove_hashes)

    settings = api_handle.settings()
    tree = grab_tree(api_handle, root_obj)
    tree.reverse()  # start with top of tree, override going down
    results = {}
    for node in tree:
        __consolidate(node,results)

    # add in syslog to results (magic)    
    if settings.syslog_port != 0:
        if not results.has_key("kernel_options"):
            results["kernel_options"] = {}
        syslog = "%s:%s" % (results["server"], settings.syslog_port)
        results["kernel_options"]["syslog"] = syslog

    # determine if we have room to add kssendmac to the kernel options line
    kernel_txt = hash_to_string(results["kernel_options"])
    if len(kernel_txt) < 244:
        results["kernel_options"]["kssendmac"] = None

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
    if http_port != 80:
       results["http_server"] = "%s:%s" % (results["server"] , http_port)
    else:
       results["http_server"] = results["server"]

    # sanitize output for koan and kernel option lines, etc
    if remove_hashes:
        results = flatten(results)
    return results

def flatten(data):
    # convert certain nested hashes to strings.
    # this is only really done for the ones koan needs as strings
    # this should not be done for everything
    if data.has_key("kernel_options"):
        data["kernel_options"] = hash_to_string(data["kernel_options"])
    if data.has_key("yumopts"):
        data["yumopts"]        = hash_to_string(data["yumopts"])
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

def run_triggers(ref,globber,additional=[]):
    """
    Runs all the trigger scripts in a given directory.
    ref can be a cobbler object, if not None, the name will be passed
    to the script.  If ref is None, the script will be called with
    no argumenets.  Globber is a wildcard expression indicating which
    triggers to run.  Example:  "/var/lib/cobbler/triggers/blah/*"
    """

    triggers = glob.glob(globber)
    triggers.sort()
    for file in triggers:
        try:
            if file.find(".rpm") != -1:
                # skip .rpmnew files that may have been installed
                # in the triggers directory
                continue
            arglist = [ file ]
            if ref:
                arglist.append(ref.name)
            for x in additional:
                arglist.append(x)
            rc = sub_process.call(arglist, shell=False)
        except:
            print _("Warning: failed to execute trigger: %s" % file)
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
    else:
       # valid for Fedora and all Red Hat / Fedora derivatives
       return "redhat"

def os_release():

   if check_dist() == "redhat":

      if not os.path.exists("/bin/rpm"):
         return ("unknown", 0)
      args = ["/bin/rpm", "-q", "--whatprovides", "redhat-release"]
      cmd = sub_process.Popen(args,shell=False,stdout=sub_process.PIPE)
      data = cmd.communicate()[0]
      data = data.rstrip().lower()
      make = "other"
      if data.find("redhat") != -1:
          make = "redhat"
      elif data.find("centos") != -1:
          make = "centos"
      elif data.find("fedora") != -1:
          make = "fedora"
      version = data.split("release-")[-1]
      rest = 0
      if version.find("-"):
         parts = version.split("-")
         version = parts[0]
         rest = parts[1]
      return (make, float(version), rest)
   elif check_dist() == "debian":
      fd = open("/etc/debian_version")
      parts = fd.read().split(".")
      version = parts[0]
      rest = parts[1]
      make = "debian"
      return (make, float(version), rest)
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
    (make,version,rest) = os_release()
    if make == "fedora" and version >= 9:
       return "/var/lib/tftpboot"
    return "/tftpboot"

def linkfile(src, dst):
    """
    Attempt to create a link dst that points to src.  Because file
    systems suck we attempt several different methods or bail to
    copyfile()
    """

    try:
        return os.link(src, dst)
    except (IOError, OSError):
        pass

    try:
        return os.symlink(src, dst)
    except (IOError, OSError):
        pass

        return copyfile(src, dst)

def copyfile(src,dst):
    try:
        return shutil.copyfile(src,dst)
    except:
        try:
            if not os.path.samefile(src,dst):
                # accomodate for the possibility that we already copied
                # the file as a symlink/hardlink
                raise CX(_("Error copying %(src)s to %(dst)s") % { "src" : src, "dst" : dst})
        except:
            raise CX(_("Problems reading %(src)s") % { "src" : src})

def rmfile(path):
    try:
        os.unlink(path)
        return True
    except OSError, ioe:
        if not ioe.errno == errno.ENOENT: # doesn't exist
            traceback.print_exc()
            raise CX(_("Error deleting %s") % path)
        return True

def rmtree_contents(path):
   what_to_delete = glob.glob("%s/*" % path)
   for x in what_to_delete:
       rmtree(x)

def rmtree(path):
   try:
       if os.path.isfile(path):
           return rmfile(path)
       else:
           return shutil.rmtree(path,ignore_errors=True)
   except OSError, ioe:
       traceback.print_exc()
       if not ioe.errno == errno.ENOENT: # doesn't exist
           raise CX(_("Error deleting %s") % path)
       return True

def mkdir(path,mode=0777):
   try:
       return os.makedirs(path,mode)
   except OSError, oe:
       if not oe.errno == 17: # already exists (no constant for 17?)
           traceback.print_exc()
           print oe.errno
           raise CX(_("Error creating") % path)

def set_repos(self,repos):
   # WARNING: hack
   repos = fix_mod_python_select_submission(repos)

   # allow the magic inherit string to persist
   if repos == "<<inherit>>":
        # FIXME: this is not inheritable in the WebUI presently ?
        self.repos = "<<inherit>>"
        return

   # store as an array regardless of input type
   if repos is None:
        repolist = []
   elif type(repos) != list:
        # allow backwards compatibility support of string input
        repolist = repos.split(None)
   else:
        repolist = repos

        
   # make sure there are no empty strings
   try:
       repolist.remove('')
   except:
       pass

   self.repos = []

   # if any repos don't exist, fail the operation
   ok = True
   for r in repolist:
        if self.config.repos().find(name=r) is not None:
            self.repos.append(r)
        else:
            print _("warning: repository not found: %s" % r)

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
            return CX(_("invalid virt file size"))
        if inum >= 0:
            self.virt_file_size = inum
            return True
        raise CX(_("invalid virt file size"))
    except:
        raise CX(_("invalid virt file size"))
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
             return CX(_("invalid virt ram size"))
         if inum >= 0:
             self.virt_ram = inum
             return True
         return CX(_("invalid virt ram size"))
     except:
         return CX(_("invalid virt ram size"))
     return True

def set_virt_type(self,vtype):
     """
     Virtualization preference, can be overridden by koan.
     """

     if vtype == "<<inherit>>":
         self.virt_type == "<<inherit>>"
         return True

     if vtype.lower() not in [ "qemu", "xenpv", "xenfv", "vmware", "auto" ]:
         raise CX(_("invalid virt type"))
     self.virt_type = vtype
     return True

def set_virt_bridge(self,vbridge):
     """
     The default bridge for all virtual interfaces under this profile.
     """
     self.virt_bridge = vbridge
     return True

def set_virt_path(self,path):
     """
     Virtual storage location suggestion, can be overriden by koan.
     """
     self.virt_path = path
     return True

def set_virt_cpus(self,num):
     """
     For Virt only.  Set the number of virtual CPUs to give to the
     virtual machine.  This is fed to virtinst RAW, so cobbler
     will not yelp if you try to feed it 9999 CPUs.  No formatting
     like 9,999 please :)
     """
     if num == "<<inherit>>":
         self.virt_cpus = "<<inherit>>"
         return True

     try:
         num = int(str(num))
     except:
         raise CX(_("invalid number of virtual CPUs"))

     self.virt_cpus = num
     return True

def get_kickstart_templates(api):
    files = {}
    for x in api.profiles():
        if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
            files[x.kickstart] = 1
    for x in api.systems():
        if x.kickstart is not None and x.kickstart != "" and x.kickstart != "<<inherit>>":
            files[x.kickstart] = 1
    for x in glob.glob("/var/lib/cobbler/kickstarts/*"):
        files[x] = 1
    for x in glob.glob("/etc/cobbler/*.ks"):
        files[x] = 1

    return files.keys()



if __name__ == "__main__":
    # print redhat_release()
    print tftpboot_location()

