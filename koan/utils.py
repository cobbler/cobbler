"""
koan = kickstart over a network
general usage functions

Copyright 2006-2008 Red Hat, Inc.
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

import random
import os
import traceback
import tempfile
import urllib2
import opt_parse  # importing this for backwards compat with 2.2
import exceptions
import sub_process
import time
import shutil
import errno
import re
import sys
import xmlrpclib
import string
import re
import glob
import socket
import shutil
import tempfile

VIRT_STATE_NAME_MAP = {
   0 : "running",
   1 : "running",
   2 : "running",
   3 : "paused",
   4 : "shutdown",
   5 : "shutdown",
   6 : "crashed"
}

class InfoException(exceptions.Exception):
    """
    Custom exception for tracking of fatal errors.
    """
    def __init__(self,value,**args):
        self.value = value % args
        self.from_koan = 1
    def __str__(self):
        return repr(self.value)

def setupLogging(appname, debug=False):
    """
    set up logging ... code borrowed/adapted from virt-manager
    """
    import logging
    import logging.handlers

    dateFormat = "%a, %d %b %Y %H:%M:%S"
    fileFormat = "[%(asctime)s " + appname + " %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamFormat = "%(asctime)s %(levelname)-8s %(message)s"
    filename = "/var/log/koan/koan.log"

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    fileHandler = logging.handlers.RotatingFileHandler(filename, "a",
                                                       1024*1024, 5)

    fileHandler.setFormatter(logging.Formatter(fileFormat,
                                               dateFormat))
    rootLogger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(logging.Formatter(streamFormat,
                                                 dateFormat))
    if debug:
        streamHandler.setLevel(logging.DEBUG)
    else:
        streamHandler.setLevel(logging.ERROR)
    rootLogger.addHandler(streamHandler)


def urlread(url):
    """
    to support more distributions, implement (roughly) some 
    parts of urlread and urlgrab from urlgrabber, in ways that
    are less cool and less efficient.
    """
    print "- reading URL: %s" % url
    if url is None or url == "":
        raise InfoException, "invalid URL: %s" % url

    elif url.startswith("nfs"):
        try:
            ndir  = os.path.dirname(url[6:])
            nfile = os.path.basename(url[6:])
            nfsdir = tempfile.mkdtemp(prefix="koan_nfs",dir="/tmp")
            nfsfile = os.path.join(nfsdir,nfile)
            cmd = ["mount","-t","nfs","-o","ro", ndir, nfsdir]
            subprocess_call(cmd)
            fd = open(nfsfile)
            data = fd.read()
            fd.close()
            cmd = ["umount",nfsdir]
            subprocess_call(cmd)
            return data
        except:
            raise InfoException, "Couldn't mount and read URL: %s" % url
          
    elif url.startswith("http") or url.startswith("ftp"):
        try:
            fd = urllib2.urlopen(url)
            data = fd.read()
            fd.close()
            return data
        except:
            raise InfoException, "Couldn't download: %s" % url
    elif url.startswith("file"):
        try:
            fd = open(url[5:])
            data = fd.read()
            fd.close()
            return data
        except:
            raise InfoException, "Couldn't read file from URL: %s" % url
              
    else:
        raise InfoException, "Unhandled URL protocol: %s" % url

def urlgrab(url,saveto):
    """
    like urlread, but saves contents to disk.
    see comments for urlread as to why it's this way.
    """
    data = urlread(url)
    fd = open(saveto, "w+")
    fd.write(data)
    fd.close()

def subprocess_call(cmd,ignore_rc=False):
    """
    Wrapper around subprocess.call(...)
    """
    print "- %s" % cmd
    rc = sub_process.call(cmd)
    if rc != 0 and not ignore_rc:
        raise InfoException, "command failed (%s)" % rc
    return rc


def input_string_or_hash(options,delim=None):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options is None:
        return {}
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
                return {}
        # dict.pop is not avail in 2.2
        if new_dict.has_key(""):
           del new_dict[""]
        return new_dict
    elif type(options) == dict:
        options.pop('',None)
        return options
    else:
        raise CX(_("invalid input type"))

def nfsmount(input_path):
    # input:  nfs://user@server:/foo/bar/x.img as string
    # output:  (dirname where mounted, last part of filename) as 2-element tuple
    input_path = input_path[6:]
    # FIXME: move this function to util.py so other modules can use it
    # we have to mount it first
    segments = input_path.split("/") # discard nfs:// prefix
    filename = segments[-1]
    dirpath = "/".join(segments[:-1])
    tempdir = tempfile.mkdtemp(suffix='.mnt', prefix='koan_', dir='/tmp')
    mount_cmd = [
         "/bin/mount", "-t", "nfs", "-o", "ro", dirpath, tempdir
    ]
    print "- running: %s" % " ".join(mount_cmd)
    rc = sub_process.call(mount_cmd)
    if not rc == 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise koan.InfoException("nfs mount failed: %s" % dirpath)
    # NOTE: option for a blocking install might be nice, so we could do this
    # automatically, if supported by python-virtinst
    print "after install completes, you may unmount and delete %s" % tempdir
    return (tempdir, filename)


def find_vm(conn, vmid):
    """
    Extra bonus feature: vmid = -1 returns a list of everything
    This function from Func:  fedorahosted.org/func
    """

    vms = []

    # this block of code borrowed from virt-manager:
    # get working domain's name
    ids = conn.listDomainsID();
    for id in ids:
        vm = conn.lookupByID(id)
        vms.append(vm)
        
    # get defined domain
    names = conn.listDefinedDomains()
    for name in names:
        vm = conn.lookupByName(name)
        vms.append(vm)

    if vmid == -1:
        return vms

    for vm in vms:
        if vm.name() == vmid:
            return vm
     
    raise InfoException("koan could not find the VM to watch: %s" % vmid)

def get_vm_state(conn, vmid):
    """
    Returns the state of a libvirt VM, by name.
    From Func:  fedorahosted.org/func
    """
    state = find_vm(conn, vmid).info()[0]
    return VIRT_STATE_NAME_MAP.get(state,"unknown")

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

   """
   This code is borrowed from Cobbler and really shouldn't be repeated.
   """

   if check_dist() == "redhat":

      if not os.path.exists("/bin/rpm"):
         return ("unknown", 0)
      args = ["/bin/rpm", "-q", "--whatprovides", "redhat-release"]
      cmd = sub_process.Popen(args,shell=False,stdout=sub_process.PIPE,close_fds=True)
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
      try:
         version = float(version)
      except:
         version = float(version[0])
      return (make, float(version), rest)
   elif check_dist() == "debian":
      fd = open("/etc/debian_version")
      parts = fd.read().split(".")
      version = parts[0]
      rest = parts[1]
      make = "debian"
      return (make, float(version), rest)
   elif check_dist() == "suse":
      fd = open("/etc/SuSE-release")
      for line in fd.read().split("\n"):
         if line.find("VERSION") != -1:
            version = line.replace("VERSION = ","")
         if line.find("PATCHLEVEL") != -1:
            rest = line.replace("PATCHLEVEL = ","")
      make = "suse"
      return (make, float(version), rest)
   else:
      return ("unknown",0)

def uniqify(lst):
   temp = {}
   for x in lst:
      temp[x] = 1
   return temp.keys()

def get_network_info():
   try:
      import rhpl.ethtool as ethtool
   except:
      raise CX("the rhpl module is required to use this feature (is your OS>=EL3?)")

   interfaces = {}
   # get names
   inames  = ethtool.get_active_devices() 
   for iname in inames:
      mac = ethtool.get_hwaddr(iname)
      ip  = ethtool.get_ipaddr(iname)
      nm  = ethtool.get_netmask(iname)
      try:
         module = ethtool.get_module(iname)
         if module == "bridge":
            continue
      except:
         continue
      interfaces[iname] = {
         "ip_address"  : ip,
         "mac_address" : mac,
         "netmask"     : nm
      }

   return interfaces

def connect_to_server(server=None,port=None):

    if server is None:
        server = os.environ.get("COBBLER_SERVER","")
    if server == "":
        raise InfoException("--server must be specified")

    if port is None: 
        port = 25151 
        
    connect_ok = False

    try_urls = [
        "http://%s/cobbler_api" % (server),
        "https://%s/cobbler_api" % (server),
    ]
    for url in try_urls:
        print "- looking for Cobbler at %s" % url
        server = __try_connect(url)
        if server is not None:
           return server
    raise InfoException ("Could not find Cobbler.")


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        try:
            xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)
        except:
            # for RHEL3's xmlrpclib -- cobblerd should strip Nones anyway
            xmlrpclib.ServerProxy.__init__(self, url)

def __try_connect(url):
    try:
        xmlrpc_server = ServerProxy(url)
        xmlrpc_server.ping()
        return xmlrpc_server
    except:
        traceback.print_exc()
        return None




