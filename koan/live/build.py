"""
Validates whether the system is reasonably well configured for
serving up content.  This is the code behind 'cobbler check'.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# usage: --server=bootserver.example.com --koan="--profile=FOO"
# requires latest git://git.fedoraproject.org/git/hosted/livecd

import optparse
import subprocess
import sys
import os

# this configuration is the kickstart for the live CD, not the install system
# tweak at your own risk

basef = open("./base.cfg")
base_config = basef.read()
basef.close()

# packages to put on the LiveCD

#packages = [
#  "kernel", "bash", "koan", "policycoreutils", "grub", "eject", "tree"
#]

#=======

def main(args):


   p = optparse.OptionParser()
   p.add_option("-k","--koan",action="store",help="additional koan arguments, if any")
   p.add_option("-s","--server",action="store",help="cobbler server address")
   (options,args) = p.parse_args()

   if options.server is None:
      sys.stderr.write("error: --server is required\n")
      sys.exit(1)
   if options.koan is None:
      options.koan = "--replace-self --server=%s" % options.server
   if options.koan.find("--server") == -1 and options.koan.find("-s") == -1:
      options.koan = options.koan + " --server=%s" % options.server
   if options.koan.find("--replace-self") == -1:
      options.koan = options.koan + " --replace-self"

   if not os.path.exists("/usr/bin/livecd-creator"):
      print("livecd-tools needs to be installed")
      sys.exit(1)

   if not os.path.exists("/usr/bin/createrepo"):
      print("createrepo needs to be installed")
      sys.exit(1)

   if not os.path.exists("/sbin/mksquashfs"):
      print("squashfs-tools needs to be installed")
      sys.exit(1)


   # create the local repo so we can have the latest koan
   # even if it's not in Fedora yet
   subprocess.call("createrepo ../../rpm-build",shell=True)

   subprocess.call("mkdir -p /tmp/newkoan", shell=True) 
   subprocess.call("cp -r ../../rpm-build/* /tmp/newkoan/",shell=True) 

   # write config file
   cfg = open("/tmp/koanlive.cfg","w+")
   cfg.write(base_config.replace("INSERT_KOAN_ARGS", "/usr/bin/koan %s" % options.koan))
   cfg.close()

   # ======

   cmd = "livecd-creator"
   cmd = cmd + " --fslabel=koan-live-cd"
   cmd = cmd + " --config=/tmp/koanlive.cfg"
   

   #for x in packages:
   #   cmd = cmd + " --package=%s" % x
   
   print("running: %s" % cmd)

   try:
       os.remove("koan-live-cd.iso")
   except:
       print("existing file not removed")
   subprocess.call(cmd, shell=True)

if __name__ == "__main__":
   main(sys.argv)

