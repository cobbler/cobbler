"""
Builds non-live bootable CD's that have PXE-equivalent behavior
for all cobbler profiles currently in memory.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import shutil
import sub_process
import sys
import traceback
import shutil
import sub_process

import utils
from cexceptions import *
from utils import _

# FIXME: lots of overlap with pxegen.py, should consolidate
# FIXME: disable timeouts and remove local boot for this?
HEADER = """

DEFAULT menu
PROMPT 0
MENU TITLE Cobbler | http://cobbler.et.redhat.com
TIMEOUT 200
TOTALTIMEOUT 6000
ONTIMEOUT local

LABEL local
        MENU LABEL (local)
        MENU DEFAULT
        LOCALBOOT -1

"""

class BuildIso:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=False):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.distmap     = {}
        self.distctr     = 0

    def make_shorter(self,distname):
        if self.distmap.has_key(distname):
            return self.distmap[distname]
        else:
            self.distctr = self.distctr + 1
            self.distmap[distname] = str(self.distctr)
            return str(self.distctr)

    def run(self,iso=None,tempdir=None,profiles=None,systems=None):

        # verify we can find isolinux.bin

        if iso is None:
            iso = "kickstart.iso"

        isolinuxbin = "/usr/lib/syslinux/isolinux.bin"
        if not os.path.exists(isolinuxbin):
            raise CX(_("Required file not found: %s") % isolinuxbin)

        # if iso is none, create it in . as "cobbler.iso"
        if tempdir is None:
            tempdir = os.path.join(os.getcwd(), "buildiso")
        print _("- using/creating tempdir: %s") % tempdir 
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        # if base of tempdir does not exist, fail
        # create all profiles unless filtered by "profiles"
        imagesdir = os.path.join(tempdir, "images")
        isolinuxdir = os.path.join(tempdir, "isolinux")       

        print _("- building tree for isolinux")
        if not os.path.exists(imagesdir):
            os.makedirs(imagesdir)
        if not os.path.exists(isolinuxdir):
            os.makedirs(isolinuxdir)

        print _("- copying miscellaneous files")
        utils.copyfile(isolinuxbin, os.path.join(isolinuxdir, "isolinux.bin"))
        menu = "/var/lib/cobbler/menu.c32"
        files = [ isolinuxbin, menu ]
        for f in files:
            if not os.path.exists(f):
                raise CX(_("Required file not found: %s") % f)
        utils.copyfile(f, os.path.join(isolinuxdir, os.path.basename(f)))
 
        print _("- copying kernels and initrds - for profiles")
        # copy all images in included profiles to images dir
        for x in self.api.profiles():
           use_this = True
           if profiles is not None:
              which_profiles = profiles.split(",")
              if not use_this in which_profiles:
                 use_this = False
           dist = x.get_conceptual_parent()
           if dist.name.find("-xen") != -1:
               continue
           distname = self.make_shorter(dist.name)
           # tempdir/isolinux/$distro/vmlinuz, initrd.img
           # FIXME: this will likely crash on non-Linux breeds
           shutil.copyfile(dist.kernel, os.path.join(isolinuxdir, "%s.krn" % distname))
           shutil.copyfile(dist.initrd, os.path.join(isolinuxdir, "%s.img" % distname))

        print _("- copying kernels and initrds - for systems")
        # copy all images in included profiles to images dir
        for x in self.api.systems():
           use_this = False
           if systems is not None:
              which_systems = systems.split(",")
              if use_this in which_systems:
                 use_this = True
           y = x.get_conceptual_parent()
           dist = y.get_conceptual_parent()
           if dist.name.find("-xen") != -1:
               continue
           distname = self.make_shorter(dist.name)
           # tempdir/isolinux/$distro/vmlinuz, initrd.img
           # FIXME: this will likely crash on non-Linux breeds
           shutil.copyfile(dist.kernel, os.path.join(isolinuxdir, "%s.krn" % distname))
           shutil.copyfile(dist.initrd, os.path.join(isolinuxdir, "%s.img" % distname))

        print _("- generating a isolinux.cfg")
        isolinuxcfg = os.path.join(isolinuxdir, "isolinux.cfg")
        cfg = open(isolinuxcfg, "w+")
        cfg.write(HEADER) # fixme, use template
        
        print _("- generating profile list")
        for x in self.api.profiles():
            use_this = True
            if profiles is not None:
                which_profiles = profiles.split(",")
                if not x.name in which_profiles:
                    use_this = False
            if use_this:
                dist = x.get_conceptual_parent()
                if dist.name.find("-xen") != -1:
                    continue
                data = utils.blender(self.api, True, x)
                distname = self.make_shorter(dist.name)

                cfg.write("\n")
                cfg.write("LABEL %s\n" % x.name)
                cfg.write("  MENU LABEL %s\n" % x.name)
                cfg.write("  kernel %s.krn\n" % distname)

                if data["kickstart"].startswith("/"):
                    data["kickstart"] = "http://%s/cblr/svc/op/ks/profile/%s" % (
                        data["server"],
                        x.name
                    )

                append_line = "  append initrd=%s.img" % distname
                if data["breed"] == "suse":
                        append_line = append_line + " autoyast=%s " % data["kickstart"]
                if data["breed"] == "redhat":
                        append_line = append_line + " ks=%s " % data["kickstart"]
                append_line = append_line + " %s\n" % data["kernel_options"]
                cfg.write(append_line)

        print _("- generating system list")
        for x in self.api.systems():
            use_this = False
            if systems is not None:
                which_systems = systems.split(",")
                if x.name in which_systems:
                    use_this = True
            if use_this:
                y = x.get_conceptual_parent()
                dist = y.get_conceptual_parent()
                if dist.name.find("-xen") != -1:
                    continue
                data = utils.blender(self.api, True, x)
                distname = self.make_shorter(dist.name)

                cfg.write("\n")
                cfg.write("LABEL %s\n" % x.name)
                cfg.write("  MENU LABEL %s\n" % x.name)
                cfg.write("  kernel %s.krn\n" % distname)

                if data["kickstart"].startswith("/"):
                    data["kickstart"] = "http://%s/cblr/svc/op/ks/system/%s" % (
                        data["server"],
                        x.name
                    )

                append_line = "  append initrd=%s.img" % distname
                append_line = append_line + " ks=%s " % data["kickstart"]
                append_line = append_line + " %s\n" % data["kernel_options"]
                cfg.write(append_line)

        print _("- done writing config")        
        cfg.write("\n")
        cfg.write("MENU END\n")
        cfg.close()
 
        cmd = "mkisofs -o %s -r -b isolinux/isolinux.bin -c isolinux/boot.cat" % iso
        cmd = cmd + "  -no-emul-boot -boot-load-size 4 "
        cmd = cmd + "  -boot-info-table -V Cobbler\ Install -R -J -T %s" % tempdir

        print _("- running: %s") % cmd
        rc = sub_process.call(cmd, shell=True)
        if rc:
            raise CX(_("mkisofs failed"))
        
        print _("ISO build complete")
        print _("You may wish to delete: %s") % tempdir
        print _("The output file is: %s") % iso 
        
  
