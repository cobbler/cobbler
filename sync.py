# Code to vivify a configuration into a real TFTP/DHCP configuration.
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
import yaml
from msg import *

"""
Handles conversion of internal state to the tftpboot tree layout
"""

class BootSync:

    def __init__(self,api):
        self.api = api
        self.verbose = True


    def sync(self,dry_run=False,verbose=True):
        """
        Syncs the current configuration file with the config tree.  
        Using the Check().run_ functions previously is recommended
        """
        self.dry_run = dry_run
        try:
            self.copy_pxelinux()
            self.clean_trees()
            self.copy_distros()
            self.validate_kickstarts()
            self.configure_httpd()
            self.build_trees()
        except:
            traceback.print_exc()
            return False
        return True


    def copy_pxelinux(self):
        """
        Copy syslinux to the configured tftpboot directory
        """
        self.copy(self.api.config.pxelinux, os.path.join(self.api.config.tftpboot, "pxelinux.0"))

    def configure_httpd(self):
        """
        Create a config file to Apache that will allow access to the 
        cobbler infrastructure available over TFTP over HTTP also.
        """
        if not os.path.exists("/etc/httpd/conf.d"):
           self.sync_log(m("no_httpd"))
           return
        f = self.open_file("/etc/httpd/conf.d/cobbler.conf","w+")
        config = """
        #
        # This configuration file allows 'cobbler' boot info
        # to be accessed over HTTP in addition to PXE.
        AliasMatch ^/cobbler(/.*)?$ "/tftpboot$1"
        <Directory "/tftpboot">
            Options Indexes
            AllowOverride None
            Order allow,deny
            Allow from all
        </Directory>
        """
        config.replace("/tftpboot",self.api.config.tftpboot)
        self.tee(f, config)
        self.close_file(f)

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and xen tree info.
        """
        for x in ["pxelinux.cfg","images","systems","distros","profiles","kickstarts"]:
            dir = os.path.join(self.api.config.tftpboot,x)
            self.rmtree(dir, True) 
            self.mkdir(dir)

    def copy_distros(self):
        """
        A distro is a kernel and an initrd.  Copy all of them and error
        out if any files are missing.  The conf file was correct if built
        via the CLI or API, though it's possible files have been moved
        since or perhaps they reference NFS directories that are no longer
        mounted.
        """
        # copy is a 4-letter word but tftpboot runs chroot, thus it's required.
        distros = os.path.join(self.api.config.tftpboot, "images")
        for d in self.api.get_distros().contents():
            distro_dir = os.path.join(distros,d.name)
            self.mkdir(distro_dir)
            kernel = self.api.utils.find_kernel(d.kernel) # full path
            initrd = self.api.utils.find_initrd(d.initrd) # full path
            if kernel is None or not os.path.isfile(kernel):
               self.api.last_error = "Kernel for distro (%s) cannot be found and needs to be fixed: %s" % (d.name, d.kernel)
               raise "error"
            if initrd is None or not os.path.isfile(initrd):
               self.api.last_error = "Initrd for distro (%s) cannot be found and needs to be fixed: %s" % (d.name, d.initrd)
               raise "error"
            b_kernel = os.path.basename(kernel)
            b_initrd = os.path.basename(initrd)
            self.copyfile(kernel, os.path.join(distro_dir, b_kernel))
            self.copyfile(initrd, os.path.join(distro_dir, b_initrd))


    def validate_kickstarts(self):
        """
        Similar to what we do for distros, ensure all the kickstarts
        in conf file are valid.   kickstarts are referenced by URL
        (http or ftp), can stay as is.  kickstarts referenced by absolute
        path will be mirrored over http.
        """
        # ensure all referenced kickstarts exist
        # these are served by either NFS, Apache, or some ftpd, so we don't need to copy them
        # it's up to the user to make sure they are nicely served by their URLs

        for g in self.api.get_profiles().contents():
           self.sync_log("mirroring any local kickstarts: %s" % g.name)
           kickstart_path = self.api.utils.find_kickstart(g.kickstart)
           if kickstart_path is None:
              self.api.last_error = m("err_kickstart") % (g.name, g.kickstart)
              raise "error"
           if os.path.exists(kickstart_path):
              # the input is an *actual* file, hence we have to copy it
              copy_path = os.path.join(self.api.config.tftpboot, "kickstarts", g.name)
              self.mkdir(copy_path)
              dest = os.path.join(copy_path, "ks.cfg")
              try:
                  self.copyfile(g.kickstart, dest)
              except:
                  self.api.last_error = m("err_kickstart2") % (g.kickstart,dest)
                  raise "error"
           elif kickstart_path.startswith("/"):
              self.api_last_error = m("err_kickstart") % (kickstart_path,g.name)

    def build_trees(self):
        """
        Now that kernels and initrds are copied and kickstarts are all valid,
        build the pxelinux.cfg tree, which contains a directory for each 
        configured IP or MAC address.  Also build a parallel 'xeninfo' tree
        for xen-net-install info.
        """
        print "building trees..."
        # create pxelinux.cfg under tftpboot
        # and file for each MAC or IP (hex encoded 01-XX-XX-XX-XX-XX-XX)
        systems = self.api.get_systems()
        profiles = self.api.get_profiles()
        distros = self.api.get_distros()

        for d in distros:
            self.sync_log("processing distro: %s" % d.name)
            # TODO: add check to ensure all distros have profiles (=warning)
            filename = os.path.join(self.api.config.tftpboot,"distros",d.name)
            d.kernel_options = self.blend_kernel_options((
               self.api.config.kernel_options,
               d.kernel_options
            ))
            self.write_distro_file(filename,d)

        for p in profiles:
            self.sync_log("processing profile: %s" % p.name)
            # TODO: add check to ensure all profiles have distros (=error)
            # TODO: add check to ensure all profiles have systems (=warning)
            filename = os.path.join(self.api.config.tftpboot,"profiles",p.name)
            distro = self.api.get_distros().find(p.distro)
            if distro is not None:
                p.kernel_options = self.blend_kernel_options((
                   self.api.config.kernel_options,
                   distro.kernel_options,
                   p.kernel_options
                ))
            self.write_profile_file(filename,p)

        for system in systems:
            self.sync_log("processing system: %s" % system.name)
            profile = profiles.find(system.profile)
            if profile is None:
                self.api.last_error = m("orphan_profile2")
                raise "error"
            distro = distros.find(profile.distro)
            if distro is None: 
                self.api.last_error = m("orphan_system2")
                raise "error"
            f1 = self.get_pxelinux_filename(system.name)
            f2 = os.path.join(self.api.config.tftpboot, "pxelinux.cfg", f1)
            f3 = os.path.join(self.api.config.tftpboot, "systems", f1)
            self.write_pxelinux_file(f2,system,profile,distro)
            self.write_system_file(f3,system)


    def get_pxelinux_filename(self,name_input):
        """
        The configuration file for each system pxelinux uses is either
        a form of the MAC address of the hex version of the IP.  Not sure
        about ipv6 (or if that works).  The system name in the config file
        is either a system name, an IP, or the MAC, so figure it out, resolve
        the host if needed, and return the pxelinux directory name.
        """
        name = self.api.utils.find_system_identifier(name_input)
        if self.api.utils.is_ip(name):
            return IPy.IP(name).strHex()[2:]
        elif self.api.utils.is_mac(name):
            return "01-" + "-".join(name.split(":")).lower()
        else:
            self.api.last_error = m("err_resolv") % name
            raise "error"
      

    def write_pxelinux_file(self,filename,system,profile,distro):
        """
        Write a configuration file for the pxelinux boot loader.
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py
        """
        kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        kickstart_path = profile.kickstart
        self.sync_log("writing: %s" % filename)
        self.sync_log("---------------------------------")
        file = self.open_file(filename,"w+")
        self.tee(file,"default linux\n")
        self.tee(file,"prompt 0\n")
        self.tee(file,"timeout 1\n")
        self.tee(file,"label linux\n")
        self.tee(file,"   kernel %s\n" % kernel_path)
        kopts = self.blend_kernel_options((
           self.api.config.kernel_options, 
           profile.kernel_options, 
           distro.kernel_options, 
           system.kernel_options
        ))
        nextline = "   append %s initrd=%s" % (kopts,initrd_path)
        if kickstart_path is not None and kickstart_path != "":
            # if kickstart path is local, we've already copied it into
            # the HTTP mirror, so make it something anaconda can get at
            if kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cobbler/kickstarts/%s/ks.cfg" % (self.api.config.server, profile.name)
            nextline = nextline + " ks=%s" % kickstart_path
        self.tee(file, nextline)
        self.close_file(file)
        self.sync_log("--------------------------------")


    def write_distro_file(self,filename,distro):
        """ 
        Create distro information for xen-net-install
        """
        file = self.open_file(filename,"w+")
        self.tee(file,yaml.dump(distro.to_datastruct()))
        self.close_file(file)


    def write_profile_file(self,filename,profile):
        """
        Create profile information for xen-net-install
        """
        file = self.open_file(filename,"w+")
        # if kickstart path is local, we've already copied it into
        # the HTTP mirror, so make it something anaconda can get at
        if profile.kickstart.startswith("/"):
            profile.kickstart = "http://%s/cobbler/kickstarts/%s/ks.cfg" % (self.api.config.server, profile.name)
        self.tee(file,yaml.dump(profile.to_datastruct()))
        self.close_file(file)
 

    def write_system_file(self,filename,system):
        """
        Create system information for xen-net-install
        """ 
        file = self.open_file(filename,"w+")
        self.tee(file,yaml.dump(system.to_datastruct()))
        self.close_file(file)

    def tee(self,file,text):
        """
        For dry_run support:  send data to screen and potentially to disk
        """
        self.sync_log(text)
        if not self.dry_run:
            file.write(text)
  
    def open_file(self,filename,mode):
        """
        For dry_run support:  open a file if not in dry_run mode.
        """
        if self.dry_run:
            return None
        return open(filename,mode)
 
    def close_file(self,file):
        """
	For dry_run support:  close a file if not in dry_run mode.
	"""
        if not self.dry_run:
            file.close()

    def copyfile(self,src,dst):
       """
       For dry_run support:  potentially copy a file.
       """
       self.sync_log("copy %s to %s" % (src,dst))
       if self.dry_run:
           return True
       return shutil.copyfile(src,dst)

    def copy(self,src,dst):
       """
       For dry_run support: potentially copy a file.
       """
       self.sync_log("copy %s to %s" % (src,dst))
       if self.dry_run:
           return True
       return shutil.copy(src,dst)

    def rmtree(self,path,ignore):
       """
       For dry_run support:  potentially delete a tree.
       """
       self.sync_log("removing dir %s" % (path))
       if self.dry_run:
           return True
       return shutil.rmtree(path,ignore)

    def mkdir(self,path,mode=0777):
       """
       For dry_run support:  potentially make a directory.
       """
       self.sync_log("creating dir %s" % (path))
       if self.dry_run:
           return True
       return os.mkdir(path,mode)

    def sync_log(self,message):
       """
       Used to differentiate dry_run output from the real thing
       automagically
       """
       if self.verbose:
           if self.dry_run:
               print "dry_run | %s" % message
           else:
               print message
            
    def blend_kernel_options(self, list_of_opts):
        """
        Given a list of kernel options, take the values used by the
        first argument in the list unless overridden by those in the
        second (or further on), according to --key=value formats.  

        This is used such that we can have default kernel options 
        in /etc and then distro, profile, and system options with various 
        levels of configurability.
        """
        internal = {}
        results = []
        # for all list of kernel options
        for items in list_of_opts:
           # get each option
           tokens=items.split(" ")
           # deal with key/value pairs and single options alike
           for token in tokens:
              key_value = token.split("=")
              if len(key_value) == 1:
                  internal[key_value[0]] = ""
              else:
                  internal[key_value[0]] = key_value[1]
        # now go back through the final list and render the single
        # items AND key/value items
        for key in internal.keys():
           data = internal[key]
           if key == "ks" or key == "initrd" or key == "append":
               # the user REALLY doesn't want to do this...
               continue 
           if data == "":
               results.append(key)
           else:       
               results.append("%s=%s" % (key,internal[key]))
        # end result is a new fragment of a kernel options string
        return " ".join(results)
 

