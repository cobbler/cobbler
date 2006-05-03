#!/usr/bin/env python
#
# koan = kickstart over a network
#
# a tool for network provisioning of Xen and network re-provisioning
# of existing Linux systems.  used with 'cobbler'.
#
# Michael DeHaan <mdehaan@redhat.com>

import sys
import os
import yaml       # (rpm -i python-yaml*.rpm in /hg/cobbler for now)
import traceback
import time
import tempfile
import urlgrabber
import optparse
import exceptions
import subprocess
import re
import shutil

# we're importing a slightly modified version of xenguest-install.
# once it's more of a library that supports a bit more explicit
# settings we can use the real thing.
import xencreate
  
"""
koan --xen --profiles=webserver,dbserver --server=hostname
koan --replace-self --server=hostname --profiles=foo
LATER? koan --replace-self --kickstart=foo (??)
"""


class InfoException(exceptions.Exception):
    def __init__(self,args=None):
        self.args = args

class Koan:
 
    def __init__(self,args):
        """
        Constructor.  Arguments are those from optparse...
        """
        self.server            = args.server
        self.profiles          = args.profiles
        self.verbose           = args.verbose
        self.is_xen            = args.is_xen
        self.is_auto_kickstart = args.is_auto_kickstart
        self.dryrun            = False
        if self.server is None:
            raise InfoException, "no server specified"
        if not self.is_xen and not self.is_auto_kickstart:
            raise InfoException, "must use either --xen or --replace-self"
        if not self.server:
            raise InfoException, "no server specified"
        if self.verbose is None:
            self.verbose = True
        if not self.profiles:
            raise InfoException, "must specify --profiles"
        self.profiles = self.profiles.split(',')
        if self.is_xen:
            self.do_xen()
        else:
            self.do_auto_kickstart()

    def debug(self,msg):
        """
        Debug print if verbose is set.
        """
        if self.verbose:
            print "- %s" % msg
        return msg    

    def mkdir(self,path):
        """
        A more verbose and tolerant mkdir
        """
        self.debug("mkdir: %s" % path)
        try:
            os.mkdir(path)
        except OSError, (errno, msg): 
            if errno != errno.EEXIST:
                raise OSError(errno,msg)

    def rmtree(self,path):
        """
        A more verbose and tolerant rmtree
        """
        self.debug("removing: %s" % path)
        try:
            shutil.rmtree(path)
        except:
            pass

    def copyfile(self,src,dest):
        """
        A more verbose copyfile
        """
        self.debug("copying %s to %s" % (src,dest))
        return shutil.copyfile(src,dest)

    def subprocess_call(self,cmd,fake_it=False,ignore_rc=False):
        """
        Wrapper around subprocess.call(...)
        """
        msg = " ".join(cmd)
        self.debug(cmd)
        if fake_it: 
            self.debug("(SIMULATED)")
            return 0
        rc = subprocess.call(cmd)
        if rc != 0 and not ignore_rc:
            raise InfoException, "command failed (%s)" % rc
        return rc

    def do_net_install(self,download_root,each_profile):
        """
        Actually kicks off downloads and auto-ks or xen installs
        """
        for profile in self.profiles:
            self.debug("processing profile: %s" % profile)
            profile_data = self.get_profile_yaml(profile)
            self.debug(profile_data)
            if not 'distro' in profile_data:
                raise InfoException, "invalid response from boot server"
            distro = profile_data['distro']
            distro_data = self.get_distro_yaml(distro)
            self.debug(distro_data)
            self.get_distro_files(distro_data, download_root)
            each_profile(self, distro_data, profile_data)
    
    def do_xen(self):
        """
        Handle xen provisioning.
        """
        def each_profile(self, distro_data, profile_data):
            cmd = self.do_xen_net_install(profile_data, distro_data)
        return self.do_net_install("/tmp",each_profile)

    def do_auto_kickstart(self):
        """
        Handle morphing an existing system through downloading new
        kernel, new initrd, and installing a kickstart in the initrd,
        then manipulating grub.
        """
        self.rmtree("/var/spool/koan")
        self.mkdir("/var/spool/koan")
    
        def each_profile(self, distro_data, profile_data):
            if not os.path.exists("/sbin/grubby"):
                raise InfoException, "grubby is not installed"
            k_args = distro_data['kernel_options']
            k_args = k_args + " ks=file:ks.cfg"
            self.build_initrd(distro_data['initrd_local'], profile_data['kickstart'])
            cmd = [ "/sbin/grubby",
                    "--add-kernel", distro_data['kernel_local'],
                    "--initrd", distro_data['initrd_local'],
                    "--make-default",
                    "--title", "kickstart",
                    "--args", k_args,
                    "--copy-default" ]
            self.subprocess_call(cmd, fake_it=self.dryrun)
            self.debug("reboot to apply changes")
        return self.do_net_install("/boot",each_profile)

    def get_kickstart_data(self,kickstart):
        """
        Get contents of data in network kickstart file.
        """
        if kickstart.startswith("nfs"):
            # FIXME: NFS bits not tested
            ndir  = os.path.dirname(kickstart[4:])
            nfile = os.path.basename(kickstart[4:])
            nfsdir = tempfile.mkdtemp(prefix="koan_nfs",dir="/var/spool/koan")
            nfsfile = os.path.join(nfsdir,nfile)
            cmd = ["mount","-o","ro", ndir, nfsdir]
            self.subprocess_call(cmd)
            return nfile.open(nfsfile).read()
        elif kickstart.startswith("http") or kickstart.startswith("ftp"):
            self.debug("urlgrab: %s" % kickstart)
            inf = urlgrabber.urlread(kickstart)
            return inf
        else:
            raise InfoException, "invalid kickstart URL"

    def get_insert_script(self,initrd,initrd_data):
        """
        Create bash script for inserting kickstart into initrd.
        Code heavily borrowed from internal auto-ks scripts.
        """
        if initrd_data.find("filesystem data") != -1:
            # FIXME: not tested with ext2 images yet
            return """
               cp %s /var/spool/koan/initrd_copy.gz
                gunzip /var/spool/koan/initrd_copy.gz
                mount -o loop -t ext2 /var/spool/koan/initrd_open /var/spool/koan/initrd_copy
                cp /var/spool/koan/ks.cfg /var/spool/koan/initrd_contents/
                ln /var/spool/koan/initrd_open/ks.cfg /var/spool/koan/initrd_open/tmp/ks.cfg
                umount /var/spool/koan/initrd_open
                gzip -c initrd_copy > /var/spool/koan/initrd_final
            """ % (initrd)
        else:
            # image is CPIO
            return """
                cp %s /var/spool/koan/initrd_copy.gz
                gunzip /var/spool/koan/initrd_copy.gz
                cat /var/spool/koan/initrd_copy | (
                    cd /var/spool/koan/initrd_contents &&
                    cpio -id &&
                    cp /var/spool/koan/ks.cfg . &&
                    ln ks.cfg tmp/ks.cfg &&
                    find . |
                    cpio -c -o | gzip -9) > /var/spool/koan/initrd_final
            """ % (initrd)


    def build_initrd(self,initrd,kickstart): 
        """
        Crack open an initrd and install the kickstart file.
        """
 
        # read contents of initrd (check for filesystem)
        fd = open(initrd,"r")
        initrd_data = fd.read()
        fd.close()

        # create directory where initrd will be exploded
        self.mkdir("/var/spool/koan/initrd_contents")

        # save kickstart to file
        fd = open("/var/spool/koan/ks.cfg","w+")
        fd.write(self.get_kickstart_data(kickstart))
        fd.close()
     
        # handle insertion of kickstart based on type of initrd
        fd = open("/var/spool/koan/insert.sh","w+")
        fd.write(self.get_insert_script(initrd,initrd_data))
        fd.close()
        self.subprocess_call([ "/bin/bash", "/var/spool/koan/insert.sh" ])
        self.copyfile("/var/spool/koan/initrd_final", initrd)

    def get_profile_yaml(self,profile_name):
        """
        Fetches profile yaml from a from a remote bootconf tree.
        """
        self.debug("fetching configuration for profile: %s" % profile_name)
        try:
            url = "http://%s/cobbler/profiles/%s" % (self.server,profile_name)
            self.debug("url=%s" % url)
            data = urlgrabber.urlread(url)
            return yaml.load(data).next()
        except:
            traceback.print_exc() # debug
            raise InfoException, "couldn't download profile information: %s" % profile_name

    def get_distro_yaml(self,distro_name):
        """
        Fetches distribution yaml from a remote bootconf tree.
        """
        self.debug("fetching configuration for distro: %s" % distro_name)
        try:
            url = "http://%s/cobbler/distros/%s" % (self.server,distro_name)
            self.debug("url=%s" % url)
            data = urlgrabber.urlread(url)
            return yaml.load(data).next()
        except:
            raise InfoException, "couldn't download distro information: %s" % distro_name 

    def get_distro_files(self,distro_data, download_root):
        """
        Using distro data (fetched from bootconf tree), determine
        what kernel and initrd to download, and save them locally.
        """
        os.chdir(download_root)
        distro = distro_data['name']
        kernel = distro_data['kernel']
        initrd = distro_data['initrd']
        kernel_short = os.path.basename(kernel)
        initrd_short = os.path.basename(initrd)
        kernel_save = "%s/%s" % (download_root, kernel_short)
        initrd_save = "%s/%s" % (download_root, initrd_short)
        try:
            self.debug("downloading initrd %s to %s" % (initrd_short, initrd_save))
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, initrd_short)
            self.debug("url=%s" % url)
            urlgrabber.urlgrab(url)
            self.debug("downloading kernel %s to %s" % (kernel_short, kernel_save))
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, kernel_short) 
            self.debug("url=%s" % url)
            urlgrabber.urlgrab(url)
        except:
            raise InfoException, "error downloading files"
        distro_data['kernel_local'] = kernel_save
        self.debug("kernel saved = %s" % kernel_save)       
        distro_data['initrd_local'] = initrd_save
        self.debug("initrd saved = %s" % initrd_save)

    def do_xen_net_install(self,profile_data,distro_data):
        """
        Invoke xenguest-install (or tweaked copy thereof)
        """
        pd = profile_data
        dd = distro_data
        
        kextra = ""
        if pd['kickstart'] != "" or pd['kernel_options'] != "":
            if pd['kickstart'] != "":
                kextra = kextra + "ks=" + pd['kickstart']
            if pd['kickstart'] !="" and pd['kernel_options'] !="":
                kextra = kextra + " "
            if pd['kernel_options'] != "":
                kextra = kextra + pd['kernel_options']

        # parser issues?  lang needs a trailing = and somehow doesn't have it.
        kextra = kextra.replace("lang","lang=")
        kextra = kextra.replace("==","=")

        # any calc_ functions filter arguments from cobbler (server side)
        # and try to make them sane with respect to the local system.
        # For instance, a name might conflict, or a size might not
        # be specified and would need to be set to a reasonable default.
        # 
        # any xencreate.get_ functions are from xenguest install, and filter
        # those further.  They are a bit of legacy data left over
        # from xenguest-install's CLI nature but it's better than recloning
        # them.  Mainly the original xenguest-install functions have 
        # been tweaked to remove any danger of interactiveness or need
        # to use optparse, which we obviously don't want here.
        
        xencreate.start_paravirt_install(
            name=self.calc_xen_name(pd), 
            ram=self.calc_xen_ram(pd), 
            disk= xencreate.get_disk(self.calc_xen_filename(pd),
                self.calc_xen_filesize(pd)), 
            mac=xencreate.get_mac(self.calc_xen_mac(pd)),
            uuid=xencreate.get_uuid(self.calc_xen_uuid(pd)),
            kernel=dd['kernel_local'],
            initrd=dd['initrd_local'],
            extra=kextra
        )

    def calc_xen_name(self,data):
        """
        Turn the suggested name into a non-conflicting name.
        For now we're being lazy about this and are just taking on
        the epoch.  Probably not ideal.  FIXME.
        """
        name = data['xen_name']
        if name is None or name == "":
            name = "xenguest"
        name = name + str(int(time.time()))
        data['xen_name'] = name
        return name

    def calc_xen_uuid(self,data):
        # FIXME: eventually we'll want to allow some koan CLI
        # option for passing in the UUID.  Until then, it's random.
        return None 

    def calc_xen_filename(self,data): 
        """
        Determine where to store the Xen file.  Just base this off
        the name and put everything close to the other Xen files?
        """
        if not os.path.exists("/var/lib/xenimages"):
             try: 
                 os.mkdir("/var/lib/xenimages")
             except: 
                 pass
        return os.path.join("/var/lib/xenimages","%s.disk" % data['xen_name'])

    def calc_xen_filesize(self,data):
        """
        Assign a xen filesize if none is given in the profile.
        """
        size = data['xen_file_size']
        err = False
        try:
            int(size)
        except:
            err = True
        if int(size)<1:
            err = True
        if err:
            self.debug("invalid file size specified, defaulting to 1 GB")
            return 1
        return int(size)

    def calc_xen_ram(self,data):
        """
        Assign a xen ram size if none is given in the profile.
        """
        size = data['xen_ram'] 
        err = False
        try:
            int(size)
        except:
            err = True
        if int(size) < 256:
            err = True
        if err:
            self.debug("invalid RAM size specified, defaulting to 256 MB")
            return 256
        return int(size)
 

    def calc_xen_mac(self,data):
        """
        For now, we have no preference.
        """
        return None


if __name__ == "__main__":
    """
    Command line stuff...
    """
    if os.getuid() != 0:
        print "koan requires root access"
        sys.exit(3)
    p = optparse.OptionParser()
    p.add_option("-x", "--xen",
                 dest="is_xen",
                 action="store_true",
                 help="requests new Xen guest creation")
    p.add_option("-r", "--replace-self",
                 dest="is_auto_kickstart",
                 action="store_true",
                 help="requests re-provisioning of this host")
    p.add_option("-p", "--profiles", 
                 dest="profiles", 
                 help="list of profiles to install")
    p.add_option("-s", "--server", 
                 dest="server", 
                 help="specify the cobbler server")
    p.add_option("-q", "--quiet",
                 dest="verbose",
                 action="store_false",
                 help="run (more) quietly")
    (options, args) = p.parse_args()
    # FIXME:  catch custom exceptions only...
    try:
        Koan(options)
    except InfoException, ie:
        traceback.print_exc()
        # print str(ie)  # str.message() ... FIXME
        sys.exit(1)
    except:
        traceback.print_exc()
        sys.exit(2)
    sys.exit(0)


