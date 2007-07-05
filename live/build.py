"""
Validates whether the system is reasonably well configured for
serving up content.  This is the code behind 'cobbler check'.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# usage: --server=bootserver.example.com --koan="--profile=FOO"

import optparse
import subprocess
import sys
import os

# this configuration is the kickstart for the live CD, not the install system
# tweak at your own risk

basef = open("./base.cfg")
base_config = basef.read()
basef.close()

# not expected to work with anything lower than FC-7
# use i386 for compatibility, still works with x86_64
# this is the LiveCD's OS, not the target install OS

USE_DISTRO_SHORT = "FC-7"
USE_DISTRO = "FC-7-i386"
USE_REPO   = "fc7i386extras"

# packages to put on the LiveCD

packages = [
  "kernel", "bash", "koan", "policycoreutils", "grub", "eject", "tree"
]

# some debug checks
   
#prereqs = {
#      "/usr/bin/livecd-creator" : "make and make install -> http://gitweb.freedesktop.org/?p=users/david/livecd-tools.git",
#      "/sbin/mksquashfs"        : "yum install squashfs-tools"
#}

#=======

def main(args):


   p = optparse.OptionParser()
   p.add_option("-k","--koan",action="store",help="koan arguments")
   p.add_option("-s","--server",action="store",help="cobbler server name")
   (options,args) = p.parse_args()

   if options.server is None:
      print >>sys.stderr, "error: --server is required"
      sys.exit(1)
   if options.koan is None:
      options.koan = "--replace-self --server=%s" % options.server
   if options.koan.find("--server") == -1 and options.koan.find("-s") == -1:
      options.koan = options.koan + " --server=%s" % options.server
   if options.koan.find("--replace-self") == -1:
      options.koan = options.koan + " --replace-self"

   # create the local repo so we can have the latest koan
   # even if it's not in Fedora yet
   subprocess.call("createrepo ../rpm-build",shell=True)
   subprocess.call("mkdir -p /var/www/html/newkoan", shell=True) 
   subprocess.call("cp -r ../rpm-build/* /var/www/html/newkoan/",shell=True) 

   # write config file
   cfg = open("/tmp/koanlive.cfg","w+")
   cfg.write(base_config.replace("INSERT_KOAN_ARGS", options.koan))
   cfg.close()

   # ======

   cmd = "livecd-creator"
   cmd = cmd + " --fslabel=koan-live-cd"
   cmd = cmd + " --config=/tmp/koanlive.cfg"
   #cmd = cmd = cmd + " --repo=newkoan,%s" % os.path.join(os.getcwd()[0:-1], "rpm-build")

   #cmd = cmd + " --repo=allofeverything,http://download.fedora.redhat.com/pub/fedora/linux/releases/7/Everything/i386/os/Fedora/"
   

   for x in packages:
      cmd = cmd + " --package=%s" % x
   
   print "running: %s" % cmd

   try:
       os.remove("koan-live-cd.iso")
   except:
       print "existing file not removed"
   subprocess.call(cmd, shell=True)

if __name__ == "__main__":
   main(sys.argv)

