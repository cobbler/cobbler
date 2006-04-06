# Misc heavy lifting functions for bootconf
# 
# Michael DeHaan <mdehaan@redhat.com>

import config

import os
import re
import socket
import glob

class BootUtil:

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
   def find_highest_files(self,directory,unversioned,regex):
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
       if len(files) > 0:
           return sorted(files, sort)[-1]
       else:
           # couldn't find a highest numbered file, but maybe there
           # is just a 'vmlinuz' or an 'initrd.img' in this directory?
           last_chance = os.path.join(directory,unversioned)
           if os.path.exists(last_chance):
               return last_chance
           return None
 
   """
   Given a directory or a filename, find if the path can be made
   to resolve into a kernel, and return that full path if possible.
   """ 
   def find_kernel(self,path):
       if os.path.isfile(path):
           filename = os.path.basename(path)
           if self.re_kernel.match(filename):
               return path
           if filename == "vmlinuz":
               return path
       elif os.path.isdir(path):
           return self.find_highest_files(path,"vmlinuz",self.re_kernel)
       return None

   """
   Given a directory or a filename, see if the path can be made 
   to resolve into an intird, return that full path if possible.
   """
   def find_initrd(self,path):
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
 
   """
   Check if a kickstart url looks like an http, ftp, or nfs url.
   """
   def find_kickstart(self,url):
       x = url.lower()
       for y in ["http://","nfs://","ftp://"]:
          if x.startswith(y):
              return url
       return None

