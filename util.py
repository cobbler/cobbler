# Misc heavy lifting functions for bootconf
# 
# Michael DeHaan <mdehaan@redhat.com>

import config

import os
import re
import socket
import glob

# FIXME: use python logging?

def debug(msg):
   print "debug: %s" % msg

def info(msg):
   print "%s" % msg

def error(msg):
   print "error: %s" % msg

def warning(msg):
   print "warning: %s" % msg

class BootUtil:


   # TO DO:  functions for manipulation of all things important.
   #         yes, that's a lot...

   def __init__(self,api,config):
       self.api = api
       self.config = config
       self.re_kernel = re.compile(r'vmlinuz-(\d+)\.(\d+)\.(\d+)-(.*)')
       self.re_initrd = re.compile(r'initrd-(\d+)\.(\d+)\.(\d+)-(.*).img')

   """
   If the input is a MAC or an IP, return that.
   If it's not, resolve the hostname and return the IP.
   pxelinux doesn't work in hostnames
   """
   def find_system_identifier(self,strdata):
       if self.is_mac(strdata):
           return strdata
       if self.is_ip(strdata):
           return strdata
       return self.resolve_ip(strdata)

   """
   Return whether the argument is an IP address.  ipv6 needs
   to be added...
   """
   def is_ip(self,strdata):
       # needs testcase
       if re.search(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}',strdata):
           return True
       return False

   """
   Return whether the argument is a mac address.
   """
   def is_mac(self,strdata):
       # needs testcase
       if re.search(r'[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F:0-9]{2}:[A-F:0-9]{2}',strdata):
           return True
       return False

   """
   Resolve the IP address and handle errors...
   """
   def resolve_ip(self,strdata):
       try:
          return socket.gethostbyname(strdata)
       except:
          return None 

   """
   Find all files in a given directory that match a given regex.
   Can't use glob directly as glob doesn't take regexen.
   """
   def find_matching_files(self,directory,regex):
       files = glob.glob(os.path.join(directory,"*"))
       results = [] 
       for f in files:
           if regex.match(os.path.basename(f)):
              results.append(f)
       return results
   
   """
   Find the highest numbered file (kernel or initrd numbering scheme)
   in a given directory that matches a given pattern.  Used for 
   auto-booting the latest kernel in a directory.
   """
   def find_highest_files(self,directory,regex):
       files = self.find_matching_files(directory, regex)
       get_numbers = re.compile(r'(\d+).(\d+).(\d+)')
       def sort(a,b):
           av  = get_numbers.search(os.path.basename(a)).groups()
           bv  = get_numbers.search(os.path.basename(b)).groups()
           if av[0]<bv[0]: return -1
           elif av[0]>bv[0]: return 1 
           elif av[1]<bv[1]: return -1
           elif av[1]>bv[1]: return 1
           elif av[2]<bv[2]: return -1
           elif av[2]>bv[2]: return 1
           return 0 
       files = sorted(files, sort)
       return files[-1]
             
   def find_kernel(self,path):
       if os.path.isfile(path):
           filename = os.path.basename(path)
           if self.re_kernel.match(filename):
               return path
       elif os.path.isdir(path):
           return self.find_highest_files(path,self.re_kernel)
       return None

   def find_initrd(self,path):
       # FUTURE: add another function to see if kernel and initrd have matched numbers (warning?)
       if os.path.isfile(path):
           filename = os.path.basename(path)
           if self.re_initrd.match(filename):
               return path
       elif os.path.isdir(path):
           return self.find_highest_files(path,self.re_initrd)  
       return None
 
   def find_kickstart(self,path):
       # Kickstarts must be explicit.
       # FUTURE:  Look in configured kickstart path and don't require full paths to kickstart
       # FUTURE:  Open kickstart file and validate that it's real
       if os.path.isfile(path):
           return path
       joined = os.path.join(self.config.kickstart_root, path)
       if os.path.isfile(joined):
           return joined
       return None

   """
   Returns None if there are no errors, otherwise returns a list 
   of things to correct prior to running bootconf 'for real'.
   FIXME: this needs to be more tolerant of non-default paths
   FIXME: this should check self.api.configuration variables
   """
   def check_install(self):
       status = []
       if os.getuid() != 0:
          print "Cannot run this as non-root user"
          return None
       if not os.path.exists(self.config.dhcpd_bin):
          status.append("can't find dhcpd, try 'yum install dhcpd'")
       if not os.path.exists(self.config.pxelinux):
          status.append("can't find %s, try 'yum install pxelinux'" % self.pxelinux)
       if not os.path.exists(self.config.tftpboot):
          status.append("can't find %s, need to create it" % self.config.tftpboot)
       if not os.path.exists(self.config.tftpd_bin):
          status.append("can't find tftpd, need to 'yum install tftp-server'") 
       if os.path.exists(self.config.tftpd_conf):
          f = open(self.config.tftpd_conf)
          re_1 = re.compile(r'default:.*off')
          re_2 = re.compile(r'disable.*=.*yes')
          found_bootdir = False
          for line in f.readlines():
             if re_1.search(line):
                 status.append("set default to 'on' in %s" % self.config.tftpd_conf)
             if re_2.search(line):
                 status.append("set disable to 'no' in %s" % self.config.tftpd_conf)
             if line.find("-s %s" % self.config.tftpboot) != -1:
                 found_bootdir = True
          if not found_bootdir:
              status.append("server_args should be \"-s %s\"' in %s" % (self.config.tftpboot,self.config.tftpd_conf))   
       else:
          status.append("%s does not exist" % self.tftpd_conf)
       if os.path.exists(self.config.dhcpd_conf):
           match_next = False
           match_file = False
           f = open(self.config.dhcpd_conf)
           for line in f.readlines():
               if line.find("next-server") != -1: 
                   match_next = True
               if line.find("filename") != -1:
                   match_file = True     
           if not match_next:
              status.append("%s needs a 'next-server ip-address;' somewhere." % self.config.dhcpd_conf)
           if not match_file:
              status.append("%s needs a 'filename \"%s/pxelinux.0\";' somewhere." % (self.config.dhcpd_conf, self.config.tftpboot))
       else:
           status.append("can't find %s" % self.config.dhcpd_conf)
       if not os.path.exists(self.config.kernel_root):
          status.append("Nothing exists at %s, edit bootconf.conf to change kernel_root or create directory" % self.config.kernel_root)
       if not os.path.exists(self.config.kickstart_root):
          status.append("Nothing exists at %s, edit bootconf.conf to change kickstart_root or create directory, also verify that kickstart_url serves up the contents of this directory!" % self.config.kickstart_root)
       return status     

   def sync(self,dryrun=False):
       # FIXME: IMPLEMENT
       return False


