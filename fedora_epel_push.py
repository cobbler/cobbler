#!/usr/bin/python

"""
Michael DeHaan <mdehaan@fedoraproject.org>, 2008

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

---

This script automates pushes from git checkouts
into Fedora CVS.  It is expected you already have
Fedora CVS set up for a project and have the build
system tools installed.

After that, usage looks like:
python pusher.py --proj=/cg/func --cvs=~/func

Work in progress
"""

# if new releases come out or old ones go away, edit here
PROCESS_RELEASES = [ "devel", "F-11", "F-10", "F-8", "EL-5", "EL-4" ]

import optparse
import os
import sys
import glob
import subprocess

def run(cmd,failok=False):
   """
   Wrapper around subprocess
   """
   print "running: %s" % cmd
   rc = subprocess.call(cmd, shell=True)
   print "rc: %s" % rc
   if not failok and not rc == 0:
       croak("aborting")


def croak(msg):
   """
   Print something and die.
   """
   print msg
   sys.exit(1)


# process options, as described at the top of this file
p = optparse.OptionParser(usage="pusher [ARGS]")
p.add_option("--cvs", dest="cvs", help="EX: ~/cvs/func")
p.add_option("--proj", dest="proj", help="EX: /cg/func")
(options,args) = p.parse_args()
if options.cvs is None:
   croak("--cvs is required, PEBKAC")
if options.proj is None:
   croak("--proj is required, PEBKAC")

cvsdir  = os.path.expanduser(options.cvs)
projdir = os.path.expanduser(options.proj)

print "----------------------------------------------"
print "Running Michael's totally awesome code pusher script"
print "----------------------------------------------"
print "assuming you first ran something like..."
print "  ssh-agent bash"
print "  ssh-agent ~/.ssh/id_dsa"
print "if not, expect pain and it's not my fault"
print "----------------------------------------------"
print " "
print "ok, here we go..."
print " "

# find the RPM build directory
rpmbuild = os.path.join(projdir, "rpm-build")
if not os.path.exists(rpmbuild):
   croak("no directory: %s" % rpmbuild)
print "found rpm-build directory"

# find the tarballs
tarsearch = "%s/*.tar.gz" % rpmbuild
tars = glob.glob(tarsearch)
if len(tars) != 1:
   croak("expected to find just one tar.gz in %s, no luck") % rpmbuild
tarfile = tars[0]
print "found tarball: %s" % tarfile

# find a version file, if any
versionfile = None
versearch = os.path.join(projdir,"version")
if os.path.exists(versearch):
   print "found a version file: %s" % versearch
   versionfile = versearch
print "found version file: %s" % versionfile

# find a specfile
specsearch = "%s/*.spec" % projdir
specs = glob.glob(specsearch)
if len(specs) != 1:
   croak("need one and only one specfile in %s" % projdir)
specfile = specs[0]
print "found specfile: %s" % specfile

# verify cvsdir exists
if not os.path.exists(cvsdir):
   croak("can't find cvs directory: %s" % cvsdir)

# store current directory
topdir = os.getcwd()

# do cvs update
os.chdir(cvsdir)
run("cvs update -d")
os.chdir(topdir)

# copy specfile and version file into CVS
# plus upload tarball
# and then commit
for x in PROCESS_RELEASES:
    releasedir = os.path.join(cvsdir, x)
    rc = run("cp %s %s" % (specfile, releasedir))
    if versionfile:
        rc = run("cp %s %s" % (versionfile, releasedir))
    print "cd into %s" % releasedir
    os.chdir(releasedir)
    rc = run("make upload FILES=%s" % tarfile)
os.chdir(cvsdir)
run("cvs commit")

# go back through each CVS directory and build stuff
for x in PROCESS_RELEASES:
    releasedir = os.path.join(cvsdir, x)
    print "cd into %s" % releasedir
    os.chdir(releasedir)
    rc = run("make tag")
    rc = run("BUILD_FLAGS=\"--nowait\" make build",failok=True)

print "---------------------------------------------"
print "all done, assuming you didn't see anything weird"
print "don't forget to visit https://admin.fedoraproject.org/updates"
print " "   

