#!/usr/bin/env python
#
# xen-net-install.py
# Michael DeHaan <mdehaan@redhat.com>
#
# note:
#   requires arp (pkg: "net-tools"), curl, and xenguest-install.py (pkg "xen")
#   (on top of the usual python stuff)
#
# see 'man xen-net-install' for details.

import sys
import os
import socket
import yaml       # not in fc5.  should be.  or a fixed py-syck, one...
import traceback
import time
import optparse

"""
xen-net-install is a network provisioning tool for xen-instances.
The expectation is that 'bootconf' has been run on a centralized
boot server.  It is this server that will specify Xen configurations
and serve up images to xen-net-install.  

Example:

   xen-net-install --profiles=webserver,dbserver --server=192.168.1.1
"""

class Base:
    """
    For convience, mostly...
    """
    def debug(self,msg):
        if self.verbose:
            print "- %s" % msg

class CurlDownload(Base):

    """
    pycurl exists but requires a newer libcurl than what was in FC5
    at the time of writing this, so we're just shelling out to curl.
    """

    def __init__(self,verbose):
        self.verbose = verbose

    def get_file(self,server,src,dest):
        """
        Download TFTP file on server named src to local file dest
        """
        cmd = "curl tftp://%s/%s -o %s" % (server,src,dest)
        self.debug("> %s" % cmd)
        rc = os.system(cmd)
        if rc!=0:
            raise "Error.  File doesn't exist?"
    
    def get_data(self,server,src):
        """
        Download TFTP file from server and return string
        """
        cmd = "curl tftp://%s/%s" % (server,src)
        self.debug("> %s" % cmd)
        out = os.popen(cmd)
        data = out.read()
        if data is None or data == "":
            raise "Server unreachable or profile doesn't exist."
        out.close()
        try:
            return yaml.load(data).next()       
        except:
            raise "Server returned invalid data."

class XenNetInstall(Base):
    """
    The guts of xen-net-install... the command line uses 
    this but it's reasonably usable as a library as well.
    """
 
    def __init__(self,args):
        """
        Constructor.  Arguments are those from optparse...
        """
        self.server = args.server
        self.profiles = args.profiles
        self.verbose = args.verbose
        self.last_error = ""
        if not self.server:
            raise "no server specified"
        if self.verbose is None:
            self.verbose = True
        if not self.profiles:
            self.profiles = []
            if not self.autodiscover:
                raise "must specify profiles or autodiscover"
        self.profiles = self.profiles.split(',')
        self.download = CurlDownload(self.verbose)
        self.xenguest_install = "./xenguest-install_mpd.py"

    def run(self):
        """
        Actually kicks off downloads and xen installs
        """
        if self.server is None:
            raise "no server specified ... can't ask DHCP"
        for profile in self.profiles:
            self.debug("processing profile: %s" % profile)
            profile_data = self.get_profile_yaml(profile)
            self.debug(profile_data)
            if not 'distro' in profile_data:
                raise "invalid response from boot server"
            distro = profile_data['distro']
            distro_data = self.get_distro_yaml(distro)
            self.debug(distro_data)
            self.get_distro_files(distro_data)
            cmd = self.build_xen_args(profile_data, distro_data)
            self.invoke_xen_install(cmd)            

    def get_profile_yaml(self,profile_name):
        """
        Fetches profile yaml from a from a remote bootconf tree.
        """
        self.debug("fetching configuration for profile: %s" % profile_name)
        data = self.download.get_data(self.server, '/'.join(['profiles', profile_name]))
        return data

    def get_distro_yaml(self,distro_name):
        """
        Fetches distribution yaml from a remote bootconf tree.
        """
        self.debug("- fetching configuration for distro: %s" % distro_name)
        data = self.download.get_data(self.server, '/'.join(['distros', distro_name]))      
        return data

    def get_distro_files(self,distro_data):
        """
        Using distro data (fetched from bootconf tree), determine
        what kernel and initrd to download, and save them locally.
        """
        distro = distro_data['name']
        kernel = distro_data['kernel']
        initrd = distro_data['initrd']
        kernel_short = os.path.basename(kernel)
        initrd_short = os.path.basename(initrd)
        kernel_save = "/tmp/%s" % kernel_short
        initrd_save = "/tmp/%s" % initrd_short
        self.debug("downloading initrd %s to %s" % (initrd_short, initrd_save))
        self.download.get_file(self.server, '/'.join(['images',distro,initrd_short]), initrd_save)
        self.debug("downloading kernel %s to %s" % (kernel_short, kernel_save))
        self.download.get_file(self.server, '/'.join(['images',distro,kernel_short]), kernel_save)
        distro_data['kernel_local'] = kernel_save
        distro_data['initrd_local'] = initrd_save

    def build_xen_args(self,profile_data,distro_data):
        """
        Now that we have data on the Xen profile and the distribution,
        and have already downloaded the kernel and initrd, 
        go ahead and install the Xen guest.  Eventually this should
        use xenguest-install as more of a library...
        """
        pd = profile_data
        dd = distro_data
        args = [
            self.xenguest_install,
            "--name=%s"     % self.calc_xen_name(pd),
            "--file=%s"     % self.calc_xen_filename(pd),
            "--file-size=%s" % self.calc_xen_filesize(pd),
            "--ram=%s"      % self.calc_xen_ram(pd),
            "--location=file://%s,%s" % (dd['initrd_local'],dd['kernel_local'])
        ] 
        # optional opts
        if pd['xen_paravirt']:
            args.append("--paravirt")
        if pd['kickstart'] != "" or pd['kernel_options'] != "":
            extra = " -x "
            if pd['kickstart'] != "":
                extra = extra + "ks=" + pd['kickstart']
            if pd['kickstart'] !="" and pd['kernel_options'] !="":
                extra = extra + ","
            if pd['kernel_options'] != "":
                extra = extra + pd['kernel_options']
            args.append(extra)
        # FIXME: support MAC ranges in addition to specifics
        if pd['xen_mac'] != "":
            args.append("--mac=%s" % pd['xen_mac'])
        return " ".join(args)
    
    def invoke_xen_install(self,cmd):     
        """
        Runs xenguest-install now that we have the args determined.
        """
        self.debug("running %s" % cmd)
        rc = os.system(cmd)
        if not rc == 0:
            raise "%s failed (rc=%d)..." % (self.xenguest_install, rc)
        return True

    def calc_xen_name(self,data):
        """
        Turn the suggested name into a non-conflicting name.
        For now we're *really* lazy about this and are just taking on
        the epoch. FIXME.
        """
        name = data['xen_name']
        if name is None or name == "":
            name = "xenguest"
        name = data['xen_name'] + str(int(time.time()))
        data['xen_name'] = name
        return name

    def calc_xen_filename(self,data): 
        """
        Determine where to store the Xen file.  Just base this off
        the name and put everything close to the other Xen files.
        """
        if not os.path.exists("/var/lib/xenimages"):
             try: 
                 os.mkdir("/var/lib/xenimages")
             except: 
                 pass
        return os.path.join("/var/lib/xenimages",data['xen_name'])

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
 

if __name__ == "__main__":
    """
    Command line stuff...
    """
    if os.getuid() != 0:
        print "xen installation requires root access"
        sys.exit(2)
    p = optparse.OptionParser()
    p.add_option("-p", "--profiles", 
                 dest="profiles", 
                 help="list of profiles to install")
    p.add_option("-s", "--server", 
                 dest="server", 
                 help="specify what server to contact, rather than "
                      "searching through DHCP to find it")
    p.add_option("-q", "--quiet",
                 dest="verbose",
                 action="store_false",
                 help="run (more) quietly")
    (options, args) = p.parse_args()
    # FIXME:  catch custom exceptions only...
    installer = XenNetInstall(options)
    try:
        installer.run()
        sys.exit(0)
    except:
        traceback.print_exc() # change to print msg in prod
        sys.exit(1)

