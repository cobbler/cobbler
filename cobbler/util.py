# Misc heavy lifting functions for cobbler
#
# Michael DeHaan <mdehaan@redhat.com>

import config

import os
import re
import socket
import glob
import weakref

class BootUtil:

   def __init__(self,api,config):
       # BootAPI is the preferred holder of all references
       self.api = weakref.proxy(api)
       self.config = weakref.proxy(config)
       self.re_kernel = re.compile(r'vmlinuz-(\d+)\.(\d+)\.(\d+)-(.*)')
       self.re_initrd = re.compile(r'initrd-(\d+)\.(\d+)\.(\d+)-(.*).img')


   def find_system_identifier(self,strdata):
       """
       If the input is a MAC or an IP, return that.
       If it's not, resolve the hostname and return the IP.
       pxelinux doesn't work in hostnames
       """
       if self.is_mac(strdata):
           return strdata
       if self.is_ip(strdata):
           return strdata
       return self.resolve_ip(strdata)


   def is_ip(self,strdata):
       """
       Return whether the argument is an IP address.  ipv6 needs
       to be added...
       """
       # needs testcase
       if re.search(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}',strdata):
           return True
       return False


   def is_mac(self,strdata):
       """
       Return whether the argument is a mac address.
       """
       # needs testcase
       if re.search(r'[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F:0-9]{2}:[A-F:0-9]{2}',strdata):
           return True
       return False


   def resolve_ip(self,strdata):
       """
       Resolve the IP address and handle errors...
       """
       try:
          return socket.gethostbyname(strdata)
       except:
          return None


   def find_matching_files(self,directory,regex):
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


   def find_highest_files(self,directory,unversioned,regex):
       """
       Find the highest numbered file (kernel or initrd numbering scheme)
       in a given directory that matches a given pattern.  Used for
       auto-booting the latest kernel in a directory.
       """
       files = self.find_matching_files(directory, regex)
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


   def find_kernel(self,path):
       """
       Given a directory or a filename, find if the path can be made
       to resolve into a kernel, and return that full path if possible.
       """
       if os.path.isfile(path):
           filename = os.path.basename(path)
           if self.re_kernel.match(filename):
               return path
           if filename == "vmlinuz":
               return path
       elif os.path.isdir(path):
           return self.find_highest_files(path,"vmlinuz",self.re_kernel)
       return None


   def find_initrd(self,path):
       """
       Given a directory or a filename, see if the path can be made
       to resolve into an intird, return that full path if possible.
       """
       # FUTURE: add another function to see if kernel and initrd have matched numbers (and throw a warning?)
       if os.path.isfile(path):
           filename = os.path.basename(path)
           if self.re_initrd.match(filename):
               return path
           if filename == "initrd.img" or filename == "initrd":
               return path
       elif os.path.isdir(path):
           return self.find_highest_files(path,"initrd.img",self.re_initrd)
       return None


   def find_kickstart(self,url):
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
              if x.startswith("/") and not os.path.isfile(x):
                  return None
              return url
       return None

