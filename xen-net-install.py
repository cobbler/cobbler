#!/usr/bin/env python
#
# xen-net-install.py
# Michael DeHaan <mdehaan@redhat.com>
#
# note:
#   requires arp (pkg: "net-tools"), curl, and xenguest-install.py (pkg "xen")
#   (on top of the usual python stuff)

import sys
import os
import socket
import yaml       # not in fc5.  should be.  or a fixed py-syck, one...
import optparse
# FIXME: would be nice to use pycurl versus shelling out to curl

"""
xen-net-install is a network provisioning tool for xen-instances.
The expectation is that 'bootconf' has been run on a centralized
boot server.  It is this server that will specify Xen configurations
and serve up images to xen-net-install.  

Example:

   xen-net-install --profiles="webserver,dbserver" --server=192.168.1.1
"""

class CurlDownload:

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
        if self.verbose:
            print "> %s" % cmd
        rc = os.system(cmd)
        if rc!=0:
            raise "Error.  File doesn't exist?"
    
    def get_data(self,server,src):
        """
        Download TFTP file from server and return string
        """
        cmd = "curl tftp://%s/%s" % (server,src)
        if self.verbose:
            print "> %s" % cmd
        out = os.popen(cmd)
        data = out.read()
        if data is None or data == "":
            raise "Server unreachable or profile doesn't exist."
        out.close()
        try:
            return yaml.load(data).next()       
        except:
            raise "Server returned invalid data."

class XenNetInstall:
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

    def run(self):
        """
        Actually kicks off downloads and xen installs
        """
        if self.server is None:
            raise "no server specified ... can't ask DHCP"
        for profile in self.profiles:
            if self.verbose:
                print "- processing profile: %s" % profile
            profile_data = self.get_profile_yaml(profile)
            if self.verbose:
                print "- %s" % profile_data
            if not 'distro' in profile_data:
                raise "invalid response from boot server"
            distro = profile_data['distro']
            distro_data = self.get_distro_yaml(distro)
            if self.verbose:
                print "- %s" % distro_data
            self.get_distro_files(distro_data)
            self.install_xen_guest(profile_data, distro_data)
            
    def get_profile_yaml(self,profile_name):
        """
        Fetches profile yaml from a from a remote bootconf tree.
        """
        if self.verbose:
            print "- fetching configuration for profile: %s" % profile_name
        data = self.download.get_data(self.server, 
                                      '/'.join(['profiles', profile_name]))
        return data

    def get_distro_yaml(self,distro_name):
        """
        Fetches distribution yaml from a remote bootconf tree.
        """
        if self.verbose:
            print "- fetching configuration for distro: %s" % distro_name
        data = self.download.get_data(self.server, 
                                      '/'.join(['distros', distro_name]))      
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
        kernel_save = self.find_kernel_save_location(distro_data,kernel_short)
        initrd_save = self.find_initrd_save_location(distro_data,initrd_short)
        # FIXME: save in better locations.
        if self.verbose:
            print "- downloading initrd %s to %s" % (initrd_short, initrd_save)
        self.download.get_file(self.server, 
                              '/'.join(['images',distro,initrd_short]), 
                              initrd_save)
        if self.verbose:
            print "- downloading kernel %s to %s" % (kernel_short, kernel_save)
        self.download.get_file(self.server, 
                              '/'.join(['images',distro,kernel_short]),
                              kernel_save)

    def find_kernel_save_location(self,distro_data,kernel_short):
        """
        the distro_data contains hints about where to save the file
        but in case they won't work, return something that will
        """
        # FIXME: IMPLEMENT
        return kernel_short
 
    def find_initrd_save_location(self,distro_data,initrd_short):
        """
        the distro_data contains hints about where to save the file
        but in case they won't work, return something that will
        """
        # FIXME: IMPLEMENT
        return initrd_short
           
    def install_xen_guest(self,profile_data,distro_data):
        """
        Now that we have data on the Xen profile and the distribution,
        and have already downloaded the kernel and initrd, 
        go ahead and install the Xen guest.
        """
        # FIXME: IMPLEMENT
        # something like system("xen-guest-install ...")
        raise "NOT_IMPLEMENTED"
 

if __name__ == "__main__":
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
    # FIXME:  try/catch print message
    # FIXME:  custom exception class
    installer = XenNetInstall(options)
    installer.run()

