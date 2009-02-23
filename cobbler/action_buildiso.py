"""
Builds non-live bootable CD's that have PXE-equivalent behavior
for all cobbler profiles currently in memory.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import os
import os.path
import shutil
import sub_process
import sys
import traceback
import shutil
import sub_process
import re

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
        KERNEL chain.c32
        APPEND hd0 0

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
        self.distros     = config.distros()
        self.distmap     = {}
        self.distctr     = 0
        self.source      = ""

    def make_shorter(self,distname):
        if self.distmap.has_key(distname):
            return self.distmap[distname]
        else:
            self.distctr = self.distctr + 1
            self.distmap[distname] = str(self.distctr)
            return str(self.distctr)

  
    def generate_netboot_iso(self,imagesdir,isolinuxdir,profiles=None,systems=None):
        print _("- copying kernels and initrds - for profiles")
        # copy all images in included profiles to images dir
        for profile in self.api.profiles():
           use_this = True
           if profiles is not None:
              which_profiles = profiles.split(",")
              if not profile.name in which_profiles:
                 use_this = False

           if use_this:
              dist = profile.get_conceptual_parent()
              if dist.name.lower().find("-xen") != -1:
                  print "skipping Xen distro: %s" % dist.name
                  continue
              distname = self.make_shorter(dist.name)
              # tempdir/isolinux/$distro/vmlinuz, initrd.img
              # FIXME: this will likely crash on non-Linux breeds
              f1 = os.path.join(isolinuxdir, "%s.krn" % distname)
              f2 = os.path.join(isolinuxdir, "%s.img" % distname)
              if not os.path.exists(dist.kernel):
                 raise CX("path does not exist: %s" % dist.kernel)
              if not os.path.exists(dist.initrd):
                 raise CX("path does not exist: %s" % dist.initrd)
              shutil.copyfile(dist.kernel, f1)
              shutil.copyfile(dist.initrd, f2)

        if systems is not None:
           print _("- copying kernels and initrds - for systems")
           # copy all images in included profiles to images dir
           for system in self.api.systems():
              if system.name in systems:
                 profile = system.get_conceptual_parent()
                 dist = profile.get_conceptual_parent()
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

        print _("- generating profile list...")
       #sort the profiles
        profile_list = [profile for profile in self.profiles]
        def sort_name(a,b):
            return cmp(a.name,b.name)
        profile_list.sort(sort_name)

        for profile in profile_list:
            use_this = True
            if profiles is not None:
                which_profiles = profiles.split(",")
                if not profile.name in which_profiles:
                    use_this = False

            if use_this:
                dist = profile.get_conceptual_parent()
                if dist.name.find("-xen") != -1:
                    continue
                data = utils.blender(self.api, True, profile)
                distname = self.make_shorter(dist.name)

                cfg.write("\n")
                cfg.write("LABEL %s\n" % profile.name)
                cfg.write("  MENU LABEL %s\n" % profile.name)
                cfg.write("  kernel %s.krn\n" % distname)

                if data["kickstart"].startswith("/"):
                    data["kickstart"] = "http://%s/cblr/svc/op/ks/profile/%s" % (
                        data["server"],
                        profile.name
                    )

                append_line = "  append initrd=%s.img" % distname
                append_line = append_line + " ks=%s " % data["kickstart"]
                append_line = append_line + " %s\n" % data["kernel_options"]

                length=len(append_line)
                if length>254:
                   print _("WARNING - append line length is greater than 254 chars: (%s chars)") % length

                cfg.write(append_line)

        if systems is not None:
           print _("- generating system list...")

           cfg.write("\nMENU SEPARATOR\n")

          #sort the systems
           system_list = [system for system in self.systems]
           def sort_name(a,b):
               return cmp(a.name,b.name)
           system_list.sort(sort_name)

           for system in system_list:
               use_this = False
               if systems is not None:
                   which_systems = systems.split(",")
                   if system.name in which_systems:
                       use_this = True

               if use_this:
                   profile = system.get_conceptual_parent()
                   dist = profile.get_conceptual_parent()
                   if dist.name.find("-xen") != -1:
                       continue
                   data = utils.blender(self.api, True, system)
                   distname = self.make_shorter(dist.name)

                   cfg.write("\n")
                   cfg.write("LABEL %s\n" % system.name)
                   cfg.write("  MENU LABEL %s\n" % system.name)
                   cfg.write("  kernel %s.krn\n" % distname)

                   if data["kickstart"].startswith("/"):
                       data["kickstart"] = "http://%s/cblr/svc/op/ks/system/%s" % (
                           data["server"],
                           system.name
                       )

                   append_line = "  append initrd=%s.img" % distname
                   append_line = append_line + " ks=%s" % data["kickstart"]
                   append_line = append_line + " %s" % data["kernel_options"]

                   # add network info to avoid DHCP only if it is available

                   if data.has_key("bonding_master_eth0") and data["bonding_master_eth0"] != "":
                      primary_interface = data["bonding_master_eth0"]
                   else:
                      primary_interface = "eth0"

                   if data.has_key("ip_address_" + primary_interface) and data["ip_address_" + primary_interface] != "":
                       append_line = append_line + " ip=%s" % data["ip_address_" + primary_interface]

                   if data.has_key("subnet_" + primary_interface) and data["subnet_" + primary_interface] != "":
                       append_line = append_line + " netmask=%s" % data["subnet_" + primary_interface]

                   if data.has_key("gateway") and data["gateway"] != "":
                       append_line = append_line + " gateway=%s" % data["gateway"]

                   if data.has_key("name_servers") and data["name_servers"]:
                       append_line = append_line + " dns=%s\n" % ",".join(data["name_servers"])

                   length=len(append_line)
                   if length > 254:
                      print _("WARNING - append line length is greater than 254 chars: (%s chars)") % length

                   cfg.write(append_line)

        print _("- done writing config")
        cfg.write("\n")
        cfg.write("MENU END\n")
        cfg.close()


    def generate_standalone_iso(self,imagesdir,isolinuxdir,distname,filesource):

        # Get the distro object for the requested distro
        # and then get all of its descendants (profiles/sub-profiles/systems)
        distro = self.api.find_distro(distname)
        if distro is None:
            raise CX("distro %s was not found, aborting" % distname)
        descendants = distro.get_descendants()

        print _("- copying kernels and initrds - for standalone distro")
        # tempdir/isolinux/$distro/vmlinuz, initrd.img
        # FIXME: this will likely crash on non-Linux breeds
        f1 = os.path.join(isolinuxdir, "vmlinuz")
        f2 = os.path.join(isolinuxdir, "initrd.img")
        if not os.path.exists(distro.kernel):
            raise CX("path does not exist: %s" % distro.kernel)
        if not os.path.exists(distro.initrd):
            raise CX("path does not exist: %s" % distro.initrd)
        shutil.copyfile(distro.kernel, f1)
        shutil.copyfile(distro.initrd, f2)

        cmd = "rsync -rlptgu --exclude=boot.cat --exclude=TRANS.TBL --exclude=isolinux/ %s/ %s/../" % (filesource, isolinuxdir)
        print _("- copying distro %s files (%s)" % (distname,cmd))
        rc = sub_process.call(cmd, shell=True, close_fds=True)
        if rc:
            raise CX(_("rsync of files failed"))

        print _("- generating a isolinux.cfg")
        isolinuxcfg = os.path.join(isolinuxdir, "isolinux.cfg")
        cfg = open(isolinuxcfg, "w+")
        cfg.write(HEADER) # fixme, use template

        for descendant in descendants:
            data = utils.blender(self.api, True, descendant)

            cfg.write("\n")
            cfg.write("LABEL %s\n" % descendant.name)
            cfg.write("  MENU LABEL %s\n" % descendant.name)
            cfg.write("  kernel vmlinuz\n")

            data["kickstart"] = "cdrom:/isolinux/ks-%s.cfg" % descendant.name

            append_line = "  append initrd=initrd.img"
            append_line = append_line + " ks=%s " % data["kickstart"]
            append_line = append_line + " %s\n" % data["kernel_options"]

            cfg.write(append_line)

            if descendant.COLLECTION_TYPE == 'profile':
                kickstart_data = self.api.kickgen.generate_kickstart_for_profile(descendant.name)
            elif descendant.COLLECTION_TYPE == 'system':
                kickstart_data = self.api.kickgen.generate_kickstart_for_system(descendant.name)

            cdregex = re.compile("url .*\n", re.IGNORECASE)
            kickstart_data = cdregex.sub("cdrom\n", kickstart_data)

            ks_name = os.path.join(isolinuxdir, "ks-%s.cfg" % descendant.name)
            ks_file = open(ks_name, "w+")
            ks_file.write(kickstart_data)
            ks_file.close()

        print _("- done writing config")
        cfg.write("\n")
        cfg.write("MENU END\n")
        cfg.close()

        return


    def run(self,iso=None,tempdir=None,profiles=None,systems=None,distro=None,standalone=None,source=None):

        # the distro option is for stand-alone builds only
        if not standalone and distro is not None:
            raise CX(_("The --distro option should only be used when creating a standalone ISO"))
        # if building standalone, we only want --distro,
        # profiles/systems are disallowed
        if standalone:
            if profiles is not None or systems is not None:
                raise CX(_("When building a standalone ISO, use --distro only instead of --profiles/--systems"))
            elif distro is None:
                raise CX(_("When building a standalone ISO, you must specify a --distro"))
            elif source is None:
                raise CX(_("When building a standalone ISO, you must specify a --source"))
            elif not os.path.exists(source):
                raise CX(_("The source specified (%s) does not exist" % source))

        # if iso is none, create it in . as "kickstart.iso"
        if iso is None:
            iso = "kickstart.iso"

        if tempdir is None:
            tempdir = os.path.join(os.getcwd(), "buildiso")
        else:
            if not os.path.isdir(tempdir):
                raise CX(_("The --tempdir specified is not a directory"))

            (tempdir_head,tempdir_tail) = os.path.split(os.path.normpath(tempdir))
            if tempdir_tail != "buildiso":
                tempdir = os.path.join(tempdir, "buildiso")

        print _("- using/creating tempdir: %s") % tempdir
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        else:
            shutil.rmtree(tempdir)
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
        isolinuxbin = "/usr/lib/syslinux/isolinux.bin"
        menu = "/var/lib/cobbler/menu.c32"
        chain = "/usr/lib/syslinux/chain.c32"
        files = [ isolinuxbin, menu, chain ]
        for f in files:
            if not os.path.exists(f):
               raise CX(_("Required file not found: %s") % f)
            else:
               utils.copyfile(f, os.path.join(isolinuxdir, os.path.basename(f)), self.api)

        if standalone:
            self.generate_standalone_iso(imagesdir,isolinuxdir,distro,source)
        else:
            self.generate_netboot_iso(imagesdir,isolinuxdir,profiles,systems)

        cmd = "mkisofs -quiet -o %s -r -b isolinux/isolinux.bin -c isolinux/boot.cat" % iso
        cmd = cmd + " -no-emul-boot -boot-load-size 4"
        cmd = cmd + " -boot-info-table -V Cobbler\ Install -R -J -T %s" % tempdir

        print _("- running: %s") % cmd
        rc = sub_process.call(cmd, shell=True, close_fds=True)
        if rc:
            raise CX(_("mkisofs failed"))

        print _("ISO build complete")
        print _("You may wish to delete: %s") % tempdir
        print _("The output file is: %s") % iso


