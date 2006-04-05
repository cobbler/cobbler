# Code to vivify a bootconf configuration into a real TFTP/DHCP configuration.
#
# Michael DeHaan <mdehaan@redhat.com>

import api
import config

import os
import sys
import traceback
import re
import shutil

import IPy
from msg import *

class BootSync:

    def __init__(self,api):
        self.api = api
        self.verbose = True

    """
    Syncs the current bootconf configuration.  
    Automatically runs the 'check' function first to eliminate likely failures.
    FUTURE: make dryrun work.
    """
    def sync(self,dry_run=False,verbose=True):
        self.dry_run = dry_run
        results = self.api.check()
        if results != []:
            self.api.last_error = m("run_check")
            return False
        try:
            self.copy_pxelinux()
            self.clean_pxelinux_tree()
            self.copy_distros()
            self.validate_kickstarts()
            self.build_pxelinux_tree()
        except:
            traceback.print_exc()
            return False
        return True

    """
    Copy syslinux to the configured tftpboot directory
    """
    def copy_pxelinux(self):
        self.copy(self.api.config.pxelinux, os.path.join(self.api.config.tftpboot, "pxelinux.0"))


    """
    Delete any previously built pxelinux.cfg tree for individual systems.
    This is better than trying to just add additional entries
    as both MAC and IP settings could have been added and the MACs will
    take precedence.  So we can't really trust human edits won't
    conflict.
    """
    def clean_pxelinux_tree(self):
        self.rmtree(os.path.join(self.api.config.tftpboot, "pxelinux.cfg"), True) 

    """
    A distro is a kernel and an initrd.  Copy all of them and error
    out if any files are missing.  The conf file was correct if built
    via the CLI or API, though it's possible files have been moved
    since or perhaps they reference NFS directories that are no longer
    mounted.
    """
    def copy_distros(self):
        # copy is a 4-letter word but tftpboot runs chroot, thus it's required.
        images = os.path.join(self.api.config.tftpboot, "images")
        self.rmtree(os.path.join(self.api.config.tftpboot, "images"), True)
        self.mkdir(images)
        for d in self.api.get_distros().contents():
            kernel = self.api.utils.find_kernel(d.kernel) # full path
            initrd = self.api.utils.find_initrd(d.initrd) # full path
            if kernel is None:
               self.api.last_error = "Kernel for distro (%s) cannot be found and needs to be fixed: %s" % (d.name, d.kernel)
               raise "error"
            if kernel is None:
               self.api.last_error = "Initrd for distro (%s) cannot be found and needs to be fixed: %s" % (d.initrd, d.kernel)
               raise "error"
            b_kernel = os.path.basename(kernel)
            b_initrd = os.path.basename(initrd)
            self.copyfile(kernel, os.path.join(images, b_kernel))
            self.copyfile(initrd, os.path.join(images, b_initrd))

    """
    Similar to what we do for distros, ensure all the kickstarts
    in conf file are valid.  Since kickstarts are referenced by URL
    (http or ftp), we do not have to copy them.  They are already
    expected to be in the right place.  We can't check to see that the
    URLs are right (or we don't, we could...) but we do check to see
    that the files are at least still there.
    """
    def validate_kickstarts(self):
        # ensure all referenced kickstarts exist
        # these are served by either NFS, Apache, or some ftpd, so we don't need to copy them
        # it's up to the user to make sure they are nicely served by their URLs
        for g in self.api.get_groups().contents():
           kickstart_path = self.api.utils.find_kickstart(g.kickstart)
           if kickstart_path is None or not os.path.isfile(kickstart_path):
              self.api.last_error = "Kickstart for group (%s) cannot be found and needs to be fixed: %s" % (g.name, g.kickstart)
              raise "error"
            
    """
    Now that kernels and initrds are copied and kickstarts are all valid,
    build the pxelinux.cfg tree, which contains a directory for each 
    configured IP or MAC address.
    """
    def build_pxelinux_tree(self):
        # create pxelinux.cfg under tftpboot
        # and file for each MAC or IP (hex encoded 01-XX-XX-XX-XX-XX-XX)
        systems = self.api.get_systems()
        groups  = self.api.get_groups()
        distros = self.api.get_distros()
        self.mkdir(os.path.join(self.api.config.tftpboot,"pxelinux.cfg"))
        for system in self.api.get_systems().contents():
            group = groups.find(system.group)
            if group is None:
                self.api.last_error = "System %s is orphaned (no group), was the configuration edited manually?" % system.name
                raise "error"
            distro = distros.find(group.distro)
            if distro is None: 
                self.api.last_error = "Group %s is orphaned (no distro), was the configuration edited manually?" % group.name 
                raise "error"
            filename = self.get_pxelinux_filename(system.name)
            filename = os.path.join(self.api.config.tftpboot, "pxelinux.cfg", filename)
            self.write_pxelinux_file(filename,system,group,distro)

    """
    The configuration file for each system pxelinux uses is either
    a form of the MAC address of the hex version of the IP.  Not sure
    about ipv6 (or if that works).  The system name in the config file
    is either a system name, an IP, or the MAC, so figure it out, resolve
    the host if needed, and return the pxelinux directory name.
    """
    def get_pxelinux_filename(self,name_input):
        name = self.api.utils.find_system_identifier(name_input)
        if self.api.utils.is_ip(name):
            return IPy.IP(name).strHex()[2:]
        elif self.api.utils.is_mac(name):
            return "01-" + "-".join(name.split(":")).lower()
        else:
            self.api.last_error = "system name (%s) couldn't resolve and is not an IP or a MAC address." % name
            raise "error"
      
    """
    Write a configuration file for the pxelinux boot loader.
    More system-specific configuration may come in later, if so
    that would appear inside the system object in api.py
    """
    def write_pxelinux_file(self,filename,system,group,distro):
        kernel_path = os.path.join("/images",os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",os.path.basename(distro.initrd))
        kickstart_path = self.api.config.kickstart_url + "/" + os.path.basename(group.kickstart)
        self.sync_log("writing: %s" % filename)
        self.sync_log("---------------------------------")
        if self.dry_run:
            file = None
        else:
            file = open(filename,"w+")
        self.tee(file,"default linux\n")
        self.tee(file,"prompt 0\n")
        self.tee(file,"timeout 1\n")
        self.tee(file,"label linux\n")
        self.tee(file,"   kernel %s\n" % kernel_path)
        # FIXME: leave off kickstart if no kickstart...
        # FIXME: allow specifying of other (system specific?) 
        #        parameters in bootconf.conf ???
        self.tee(file,"   append devfs=nomount ramdisk_size=16438 lang= vga=788 ksdevice=eth0 initrd=%s ks=%s console=ttyS0,38400n8\n" % (initrd_path, kickstart_path))
        if not self.dry_run: 
            file.close()
        self.sync_log("--------------------------------")

    """
    For dry_run support, and logging...
    """
    def tee(self,file,text):
        self.sync_log(text)
        if not self.dry_run:
            file.write(text)
  
    def copyfile(self,src,dst):
       self.sync_log("copy %s to %s" % (src,dst))
       if self.dry_run:
           return True
       return shutil.copyfile(src,dst)

    def copy(self,src,dst):
        self.sync_log("copy %s to %s" % (src,dst))
        if self.dry_run:
            return True
        return shutil.copy(src,dst)

    def rmtree(self,path,ignore):
       self.sync_log("removing dir %s" % (path))
       if self.dry_run:
           return True
       return shutil.rmtree(path,ignore)

    def mkdir(self,path,mode=0777):
       self.sync_log("creating dir %s" % (path))
       if self.dry_run:
           return True
       return os.mkdir(path,mode)

    """
    Used to differentiate dry_run output from the real thing
    automagically
    """
    def sync_log(self,message):
        if self.verbose:
            if self.dry_run:
                print "dry_run | %s" % message
            else:
                print message
            
 
    # FUTURE: would be nice to check if dhcpd and tftpd are running...
    # and whether kickstart url works (nfs, http, ftp)
    # at least those that work with open-uri

