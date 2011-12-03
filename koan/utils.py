"""
koan = kickstart over a network
general usage functions

Copyright 2006-2008 Red Hat, Inc and Others.
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

import random
import os
import traceback
import tempfile
import exceptions
ANCIENT_PYTHON = 0
try:
    try:
        import subprocess as sub_process
    except:
       import sub_process
    import urllib2
except:
    ANCIENT_PYTHON = 1
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
import urlgrabber

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

def setupLogging(appname):
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
    streamHandler.setLevel(logging.DEBUG)
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

    elif url[0:3] == "nfs":
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
            traceback.print_exc()
            raise InfoException, "Couldn't mount and read URL: %s" % url
          
    elif url[0:4] == "http":
        try:
            fd = urllib2.urlopen(url)
            data = fd.read()
            fd.close()
            return data
        except:
            if ANCIENT_PYTHON:
                # this logic is to support python 1.5 and EL 2
                import urllib
                fd = urllib.urlopen(url)
                data = fd.read()
                fd.close()
                return data
            traceback.print_exc()
            raise InfoException, "Couldn't download: %s" % url
    elif url[0:4] == "file":
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

def subprocess_call(cmd,ignore_rc=0):
    """
    Wrapper around subprocess.call(...)
    """
    print "- %s" % cmd
    if not ANCIENT_PYTHON:
        rc = sub_process.call(cmd)
    else:
        cmd = string.join(cmd, " ")
        print "cmdstr=(%s)" % cmd
        rc = os.system(cmd)
    if rc != 0 and not ignore_rc:
        raise InfoException, "command failed (%s)" % rc
    return rc

def input_string_or_hash(options,delim=None,allow_multiples=True):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options is None:
        return {}
    elif type(options) == list:
        raise InfoException("No idea what to do with list: %s" % options)
    elif type(options) == type(""):
        new_dict = {}
        tokens = string.split(options, delim)
        for t in tokens:
            tokens2 = string.split(t,"=")
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

        # dict.pop is not avail in 2.2
        if new_dict.has_key(""):
           del new_dict[""]
        return new_dict
    elif type(options) == type({}):
        options.pop('',None)
        return options
    else:
        raise InfoException("invalid input type: %s" % type(options))

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

def nfsmount(input_path):
    # input:  [user@]server:/foo/bar/x.img as string
    # output:  (dirname where mounted, last part of filename) as 2-element tuple
    # FIXME: move this function to util.py so other modules can use it
    # we have to mount it first
    filename = input_path.split("/")[-1]
    dirpath = string.join(input_path.split("/")[:-1],"/")
    tempdir = tempfile.mkdtemp(suffix='.mnt', prefix='koan_', dir='/tmp')
    mount_cmd = [
         "/bin/mount", "-t", "nfs", "-o", "ro", dirpath, tempdir
    ]
    print "- running: %s" % mount_cmd
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
       import lsb_release
       return lsb_release.get_distro_information()['ID'].lower()
    elif os.path.exists("/etc/SuSE-release"):
       return "suse"
    else:
       # valid for Fedora and all Red Hat / Fedora derivatives
       return "redhat"

def os_release():

   """
   This code is borrowed from Cobbler and really shouldn't be repeated.
   """

   if ANCIENT_PYTHON:
      return ("unknown", 0)

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
      import lsb_release
      release = lsb_release.get_distro_information()['RELEASE']
      return ("debian", release)
   elif check_dist() == "ubuntu":
      version = sub_process.check_output(("lsb_release","--release","--short")).rstrip()
      make = "ubuntu"
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

def uniqify(lst, purge=None):
   temp = {}
   for x in lst:
      temp[x] = 1
   if purge is not None:
      temp2 = {}
      for x in temp.keys():
         if x != purge:
            temp2[x] = 1
      temp = temp2
   return temp.keys()

def get_network_info():
   try:
      import ethtool
   except:
      try:
         import rhpl.ethtool
         ethtool = rhpl.ethtool
      except:
           raise InfoException("the rhpl or ethtool module is required to use this feature (is your OS>=EL3?)")

   interfaces = {}
   # get names
   inames  = ethtool.get_devices()

   for iname in inames:
      mac = ethtool.get_hwaddr(iname)

      if mac == "00:00:00:00:00:00":
         mac = "?"

      try:
         ip  = ethtool.get_ipaddr(iname)
         if ip == "127.0.0.1":
            ip = "?"
      except:
         ip  = "?"

      bridge = 0
      module = ""

      try:
         nm  = ethtool.get_netmask(iname)
      except:
         nm  = "?"

      interfaces[iname] = {
         "ip_address"  : ip,
         "mac_address" : mac,
         "netmask"     : nm,
         "bridge"      : bridge,
         "module"      : module
      }

   # print interfaces
   return interfaces

def connect_to_server(server=None,port=None):

    if server is None:
        server = os.environ.get("COBBLER_SERVER","")
    if server == "":
        raise InfoException("--server must be specified")

    if port is None: 
        port = 80
        
    connect_ok = 0

    try_urls = [
        "http://%s:%s/cobbler_api" % (server,port),
        "https://%s:%s/cobbler_api" % (server,port),
    ]
    for url in try_urls:
        print "- looking for Cobbler at %s" % url
        server = __try_connect(url)
        if server is not None:
           return server
    raise InfoException ("Could not find Cobbler.")

def create_xendomains_symlink(name):
    """
    Create an /etc/xen/auto/<name> symlink for use with "xendomains"-style
    VM boot upon dom0 reboot.
    """
    src = "/etc/xen/%s" % name
    dst = "/etc/xen/auto/%s" % name

    # check that xen config file exists and create symlink
    if os.path.exists(src) and os.access(os.path.dirname(dst), os.W_OK):
        os.symlink(src, dst)
    else:
        raise InfoException("Could not create /etc/xen/auto/%s symlink.  Please check write permissions and ownership" % name)

def libvirt_enable_autostart(domain_name):
   import libvirt
   try:
      conn = libvirt.open("qemu:///system")
      conn.listDefinedDomains()
      domain = conn.lookupByName(domain_name)
      domain.setAutostart(1)
   except:
      raise InfoException("libvirt could not find domain %s" % domain_name)

   if not domain.autostart:
      raise InfoException("Could not enable autostart on domain %s." % domain_name)

def make_floppy(kickstart):

    (fd, floppy_path) = tempfile.mkstemp(suffix='.floppy', prefix='tmp', dir="/tmp")
    print "- creating floppy image at %s" % floppy_path

    # create the floppy image file
    cmd = "dd if=/dev/zero of=%s bs=1440 count=1024" % floppy_path
    print "- %s" % cmd
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("dd failed")

    # vfatify
    cmd = "mkdosfs %s" % floppy_path
    print "- %s" % cmd
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("mkdosfs failed")

    # mount the floppy
    mount_path = tempfile.mkdtemp(suffix=".mnt", prefix='tmp', dir="/tmp")
    cmd = "mount -o loop -t vfat %s %s" % (floppy_path, mount_path)
    print "- %s" % cmd
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("mount failed")

    # download the kickstart file onto the mounted floppy
    print "- downloading %s" % kickstart
    save_file = os.path.join(mount_path, "unattended.txt")
    urlgrabber.urlgrab(kickstart,filename=save_file)

    # umount    
    cmd = "umount %s" % mount_path
    print "- %s" % cmd
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("umount failed")

    # return the path to the completed disk image to pass to virtinst
    return floppy_path

def sync_file(ofile, nfile, uid, gid, mode):
    sub_process.call(['/usr/bin/diff', ofile, nfile])
    shutil.copy(nfile, ofile)
    os.chmod(ofile,mode)
    os.chown(ofile,uid,gid)

#class ServerProxy(xmlrpclib.ServerProxy):
#
#    def __init__(self, url=None):
#        try:
#            xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)
#        except:
#            # for RHEL3's xmlrpclib -- cobblerd should strip Nones anyway
#            xmlrpclib.ServerProxy.__init__(self, url)

def __try_connect(url):
    try:
        xmlrpc_server = xmlrpclib.Server(url)
        xmlrpc_server.ping()
        return xmlrpc_server
    except:
        traceback.print_exc()
        return None




