"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

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
import time
import sub_process
import sys
import glob
import traceback
import errno

import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system
import item_image

from utils import _


class PXEGen:
    """
    Handles building out PXE stuff
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.images      = config.images()
        self.templar     = templar.Templar(config)
        self.bootloc     = utils.tftpboot_location()

    def copy_bootloaders(self):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in
        /etc/cobbler/settings.
        """
        dst = self.bootloc

        # copy syslinux from one of two locations
        try:
            utils.copyfile_pattern('/usr/lib/syslinux/pxelinux.0',   dst)
        except:
            utils.copyfile_pattern('/usr/share/syslinux/pxelinux.0', dst)
   
        # copy memtest only if we find it
        utils.copyfile_pattern('/boot/memtest*', dst, require_match=False)
  
        # copy elilo which we include for IA64 targets
        utils.copyfile_pattern('/var/lib/cobbler/elilo-3.6-ia64.efi', dst)
 
        # copy menu.c32 as the older one has some bugs on certain RHEL
        utils.copyfile_pattern('/var/lib/cobbler/menu.c32', dst)

        # copy memdisk as we need it to boot ISOs
        try:
            utils.copyfile_pattern('/usr/lib/syslinux/memdisk',   dst)
        except:
            utils.copyfile_pattern('/usr/share/syslinux/memdisk', dst)


    def copy_distros(self):
        """
        A distro is a kernel and an initrd.  Copy all of them and error
        out if any files are missing.  The conf file was correct if built
        via the CLI or API, though it's possible files have been moved
        since or perhaps they reference NFS directories that are no longer
        mounted.

        NOTE:  this has to be done for both tftp and http methods
        """
        # copy is a 4-letter word but tftpboot runs chroot, thus it's required.
        for d in self.distros:
            self.copy_single_distro_files(d)

    def copy_images(self):
        """
        Like copy_distros except for images.
        """
        for i in self.images:
            self.copy_single_image_files(i)

    def copy_single_distro_files(self, d):
        for dirtree in [self.bootloc, self.settings.webdir]: 
            distros = os.path.join(dirtree, "images")
            distro_dir = os.path.join(distros,d.name)
            utils.mkdir(distro_dir)
            kernel = utils.find_kernel(d.kernel) # full path
            initrd = utils.find_initrd(d.initrd) # full path
            if kernel is None or not os.path.isfile(kernel):
                raise CX(_("kernel not found: %(file)s, distro: %(distro)s") % { "file" : d.kernel, "distro" : d.name })
            if initrd is None or not os.path.isfile(initrd):
                raise CX(_("initrd not found: %(file)s, distro: %(distro)s") % { "file" : d.initrd, "distro" : d.name })
            b_kernel = os.path.basename(kernel)
            b_initrd = os.path.basename(initrd)
            allow_symlink=False
            if dirtree == self.settings.webdir:
                allow_symlink=True
            utils.linkfile(kernel, os.path.join(distro_dir, b_kernel), symlink_ok=allow_symlink)
            utils.linkfile(initrd, os.path.join(distro_dir, b_initrd), symlink_ok=allow_symlink)

    def copy_single_image_files(self, img):
        images_dir = os.path.join(self.bootloc, "images2")
        filename = img.file 
        if not os.path.exists(filename):
            # likely for virtual usage, cannot use
            return
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        basename = os.path.basename(img.file)
        newfile = os.path.join(images_dir, img.name)
        utils.linkfile(filename, newfile)
        return True

    def write_all_system_files(self,system):

        profile = system.get_conceptual_parent()
        if profile is None:
            raise CX(_("system %(system)s references a missing profile %(profile)s") % { "system" : system.name, "profile" : system.profile})
        distro = profile.get_conceptual_parent()
        image_based = False
        image = None
        if distro is None:
            if profile.COLLECTION_TYPE == "profile":
               raise CX(_("profile %(profile)s references a missing distro %(distro)s") % { "profile" : system.profile, "distro" : profile.distro})
            else:
               image_based = True
               image = profile

        # this used to just generate a single PXE config file, but now must
        # generate one record for each described NIC ...
 
        for (name,interface) in system.interfaces.iteritems():

            ip = interface["ip_address"]

            f1 = utils.get_config_filename(system,interface=name)

            if image_based:
                working_arch = image.arch
            else:
                working_arch = distro.arch

            if working_arch is None or working_arch == "":
                working_arch = "x86"

            # for tftp only ...
            if working_arch in [ "i386", "x86", "x86_64", "standard"]:
                # pxelinux wants a file named $name under pxelinux.cfg
                f2 = os.path.join(self.bootloc, "pxelinux.cfg", f1)
            elif working_arch == "ia64":
                # elilo expects files to be named "$name.conf" in the root
                # and can not do files based on the MAC address
                if ip is not None and ip != "":
                    print _("Warning: Itanium system object (%s) needs an IP address to PXE") % system.name

                filename = "%s.conf" % utils.get_config_filename(system,interface=name)
                f2 = os.path.join(self.bootloc, filename)
            elif working_arch == "s390x":
                filename = "%s" % utils.get_config_filename(system,interface=name)
                f2 = os.path.join(self.bootloc, "s390x", filename)
            else:
                continue 

            if system.netboot_enabled and system.is_management_supported():
                if not image_based:
                    self.write_pxe_file(f2,system,profile,distro,distro.arch)
                else:
                    self.write_pxe_file(f2,system,None,None,None,image=profile)
            else:
                # ensure the file doesn't exist
                utils.rmfile(f2)

    def make_pxe_menu(self):
        self.make_s390_pseudo_pxe_menu()
        self.make_actual_pxe_menu() 

    def make_s390_pseudo_pxe_menu(self):
        s390path = os.path.join(self.bootloc, "s390x")
        if not os.path.exists(s390path):
            utils.mkdir(s390path)
        profile_list = [profile for profile in self.profiles]
        image_list = [image for image in self.images]
        def sort_name(a,b):
           return cmp(a.name,b.name)
        profile_list.sort(sort_name)
        image_list.sort(sort_name)
        listfile = open(os.path.join(s390path, "profile_list"),"w+")
        for profile in profile_list:
            distro = profile.get_conceptual_parent()
            if distro.arch == "s390x":
                listfile.write("%s\n" % profile.name)
            f2 = os.path.join(self.bootloc, "s390x", profile.name)
            self.write_pxe_file(f2,None,profile,distro,distro.arch)
        listfile2 = open(os.path.join(s390path, "image_list"),"w+")
        for image in image_list:
            if os.path.exists(image.file):
                listfile2.write("%s\n" % image.name)
            f2 = os.path.join(self.bootloc, "s390x", image.name)
            self.write_pxe_file(f2,None,None,None,None,image=image)
        listfile.close()
        listfile2.close()

    def make_actual_pxe_menu(self):
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")
        if default is not None:
            return
        
        fname = os.path.join(self.bootloc, "pxelinux.cfg", "default")

        # read the default template file
        template_src = open("/etc/cobbler/pxedefault.template")
        template_data = template_src.read()

        # sort the profiles
        profile_list = [profile for profile in self.profiles]
        def sort_name(a,b):
           return cmp(a.name,b.name)
        profile_list.sort(sort_name)

        # sort the images
        image_list = [image for image in self.images]
        image_list.sort(sort_name)

        # build out the menu entries
        pxe_menu_items = ""
        for profile in profile_list:
            distro = profile.get_conceptual_parent()
            # xen distros can be ruled out as they won't boot
            if distro.name.find("-xen") != -1:
                # can't PXE Xen 
                continue
            contents = self.write_pxe_file(None,None,profile,distro,distro.arch,include_header=False)
            if contents is not None:
                pxe_menu_items = pxe_menu_items + contents + "\n"

        # image names towards the bottom
        for image in image_list:
            if os.path.exists(image.file):
                contents = self.write_pxe_file(None,None,None,None,None,image=image)
                if contents is not None:
                    pxe_menu_items = pxe_menu_items + contents + "\n"

        # if we have any memtest files in images, make entries for them
        # after we list the profiles
        memtests = glob.glob(self.bootloc + "/images/memtest*")
        if len(memtests) > 0:
            pxe_menu_items = pxe_menu_items + "\n\n"
            for memtest in glob.glob(self.bootloc + '/images/memtest*'):
                base = os.path.basename(memtest)
                contents = self.write_memtest_pxe("/images/%s" % base)
                pxe_menu_items = pxe_menu_items + contents + "\n"
              
        # save the template.
        metadata = { "pxe_menu_items" : pxe_menu_items }
        outfile = os.path.join(self.bootloc, "pxelinux.cfg", "default")
        self.templar.render(template_data, metadata, outfile, None)
        template_src.close()

    def write_memtest_pxe(self,filename):
        """
        Write a configuration file for memtest
        """

        # FIXME: this should be handled via "cobbler image add" now that it is available,
        # though it would be nice if there was a less-manual way to add those as images.

        # just some random variables
        template = None
        metadata = {}
        buffer = ""

        template = "/etc/cobbler/pxeprofile.template"

        # store variables for templating
        metadata["menu_label"] = "MENU LABEL %s" % os.path.basename(filename)
        metadata["profile_name"] = os.path.basename(filename)
        metadata["kernel_path"] = "/images/%s" % os.path.basename(filename)
        metadata["initrd_path"] = ""
        metadata["append_line"] = ""

        # get the template
        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        # return results
        buffer = self.templar.render(template_data, metadata, None)
        return buffer


    def write_pxe_file(self,filename,system,profile,distro,arch,image=None,include_header=True):
        """
        Write a configuration file for the boot loader(s).
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py

        NOTE: relevant to tftp and pseudo-PXE (s390) only

        ia64 is mostly the same as syslinux stuff, s390 is a bit
        short-circuited and simpler.  All of it goes through the
        templating engine, see the templates in /etc/cobbler for
        more details
        """

        # ---
        # system might have netboot_enabled set to False (see item_system.py), if so, 
        # don't do anything else and flag the error condition.
        if system is not None and not system.netboot_enabled:
            return None
        if image and not os.path.exists(image.file):
            return None  # nfs:// URLs or something, can't use for TFTP

        # ---
        # just some random variables
        template = None
        metadata = {}
        buffer = ""

        # ---
        kickstart_path = None
        kernel_path = None
        initrd_path = None

        if image is None: 
            # profile or system+profile based, not image based, or system+image based

            kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
            initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        
            # Find the kickstart if we inherit from another profile
            kickstart_path = utils.blender(self.api, True, profile)["kickstart"]
        else:
            if image.image_type == "direct":
                kernel_path = os.path.join("/images2",image.name)
            elif image.image_type == "memdisk":
                kernel_path = "/memdisk"
                initrd_path = os.path.join("/images2",image.name)
            else:
                # CD-ROM ISO or virt-clone image? We can't PXE boot it.
                kernel_path = None
                initrd_path = None

        # ---
        # choose a template
        if arch in [ "standard", "x86", "i386", "i386", "x86_64" ] or (arch is None and system is None):
            template = "/etc/cobbler/pxeprofile.template"
        elif arch == "s390x":
            template = "/etc/cobbler/pxesystem_s390x.template"
        elif arch == "ia64":
            template = "/etc/cobbler/pxesystem_ia64.template"
        else:
            template = "/etc/cobbler/pxesystem.template"


        # now build the kernel command line
        if system is not None:
            blended = utils.blender(self.api, True, system)
        elif profile is not None:
            blended = utils.blender(self.api, True, profile)
        else:
            blended = utils.blender(self.api, True, image)
        kopts = blended.get("kernel_options","")

        # generate the append line
        hkopts = utils.hash_to_string(kopts)
        if not arch or arch != "ia64":
            append_line = "append initrd=%s %s" % (initrd_path, hkopts)
        else:
            append_line = "append %s" % hkopts

        if len(append_line) >= 255 + len("append "):
            print _("warning: kernel option length exceeds 255")

        # kickstart path rewriting (get URLs for local files)
        if kickstart_path is not None and kickstart_path != "":

            if system is not None and kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cblr/svc/op/ks/system/%s" % (blended["http_server"], system.name)
            elif kickstart_path.startswith("/") or kickstart_path.find("/cobbler/kickstarts/") != -1:
                kickstart_path = "http://%s/cblr/svc/op/ks/profile/%s" % (blended["http_server"], profile.name)

            if distro.breed is None or distro.breed == "redhat":
                append_line = "%s ks=%s" % (append_line, kickstart_path)
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, kickstart_path)
            elif distro.breed == "debian":
                append_line = "%s auto=true url=%s" % (append_line, kickstart_path)
                append_line = append_line.replace("ksdevice","interface")

        if arch == "s390x":
            # remove the prefix "append"
            append_line = append_line[7:]

        # store variables for templating
        metadata["menu_label"] = ""
        if profile and not arch == "ia64" and system is None:
            metadata["menu_label"] = "MENU LABEL %s" % profile.name
            metadata["profile_name"] = profile.name
        elif image:
            metadata["menu_label"] = "MENU LABEL %s" % image.name
            metadata["profile_name"] = image.name

        if kernel_path is not None:
            metadata["kernel_path"] = kernel_path
        if initrd_path is not None:
            metadata["initrd_path"] = initrd_path

        metadata["append_line"] = append_line

        # get the template
        if kernel_path is not None and initrd_path is not None:
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()
        else:
            # this is something we can't PXE boot
            template_data = "\n"        

        # save file and/or return results, depending on how called.
        buffer = self.templar.render(template_data, metadata, None)
        if filename is not None:
            fd = open(filename, "w")
            fd.write(buffer)
            fd.close()
        return buffer




