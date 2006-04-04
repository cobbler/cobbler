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

    """
    Syncs the current bootconf configuration.  
    Automatically runs the 'check_install'
    FUTURE: make dryrun work.
    """
    def sync(self,dry_run=False):
        if dry_run:
            print "WARNING: dryrun hasn't been implemented yet.  Try not using dryrun at your own risk."
            sys.exit(1)
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

    def copy_pxelinux(self):
        shutil.copy(self.api.config.pxelinux, os.path.join(self.api.config.tftpboot, "pxelinux.0"))

    def clean_pxelinux_tree(self):
        shutil.rmtree(os.path.join(self.api.config.tftpboot, "pxelinux.cfg"), True) 

    def copy_distros(self):
        # copy is a 4-letter word but tftpboot runs chroot, thus it's required.
        images = os.path.join(self.api.config.tftpboot, "images")
        shutil.rmtree(os.path.join(self.api.config.tftpboot, "images"), True)
        os.mkdir(images)
        for d in self.api.get_distros().contents():
            kernel = self.api.utils.find_kernel(d.kernel) # full path
            initrd = self.api.utils.find_initrd(d.initrd) # full path
            print "DEBUG: kernel = %s" % kernel
            print "DEBUG: initrd = %s" % initrd
            if kernel is None:
               self.api.last_error = "Kernel for distro (%s) cannot be found and needs to be fixed: %s" % (d.name, d.kernel)
               raise "error"
            if kernel is None:
               self.api.last_error = "Initrd for distro (%s) cannot be found and needs to be fixed: %s" % (d.initrd, d.kernel)
               raise "error"
            b_kernel = os.path.basename(kernel)
            b_initrd = os.path.basename(initrd)
            shutil.copyfile(kernel, os.path.join(images, b_kernel))
            shutil.copyfile(initrd, os.path.join(images, b_initrd))

    def validate_kickstarts(self):
        # ensure all referenced kickstarts exist
        # these are served by either NFS, Apache, or some ftpd, so we don't need to copy them
        # it's up to the user to make sure they are nicely served by their URLs
        for g in self.api.get_groups().contents():
           kickstart_path = self.api.utils.find_kickstart(g.kickstart)
           if kickstart_path is None or not os.path.isfile(kickstart_path):
              self.api.last_error = "Kickstart for group (%s) cannot be found and needs to be fixed: %s" % (g.name, g.kickstart)
              raise "error"
            
    def build_pxelinux_tree(self):
        # create pxelinux.cfg under tftpboot
        # and file for each MAC or IP (hex encoded 01-XX-XX-XX-XX-XX-XX)
        systems = self.api.get_systems()
        groups  = self.api.get_groups()
        distros = self.api.get_distros()
        os.mkdir(os.path.join(self.api.config.tftpboot,"pxelinux.cfg"))
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

    def get_pxelinux_filename(self,name_input):
        name = self.api.utils.find_system_identifier(name_input)
        if self.api.utils.is_ip(name):
            return IPy.IP(name).strHex()[2:]
        elif self.api.utils.is_mac(name):
            return "01-" + "-".join(name.split(":")).lower()
        else:
            self.api.last_error = "system name (%s) couldn't resolve and is not an IP or a MAC address." % name
            raise "error"
      
    def write_pxelinux_file(self,filename,system,group,distro):
        kernel_path = os.path.join("/images",os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",os.path.basename(distro.initrd))
        kickstart_path = self.api.config.kickstart_url + "/" + os.path.basename(group.kickstart)
        file = open(filename,"w+")
        file.write("default linux\n")
        file.write("prompt 0\n")
        file.write("timeout 1\n")
        file.write("label linux\n")
        file.write("   kernel %s\n" % kernel_path)
        # FIXME: leave off kickstart if no kickstart...
        # FIXME: allow specifying of other (system specific?) 
        #        parameters in bootconf.conf ???
        file.write("   append devfs=nomount ramdisk_size=16438 lang= vga=788 ksdevice=eth0 initrd=%s ks=%s console=ttyS0,38400n8\n" % (initrd_path, kickstart_path))
        file.close()

    # FUTURE: would be nice to check if dhcpd and tftpd are running...
    # and whether kickstart url works (nfs, http, ftp)
    # at least those that work with open-uri
    # possibly file permissions...

