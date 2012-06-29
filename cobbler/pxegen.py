"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import shlex
import time
import sys
import glob
import traceback
import errno
import string
import socket

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

    def __init__(self, config, logger):
        """
        Constructor
        """
        self.config      = config
        self.logger      = logger
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.images      = config.images()
        self.templar     = templar.Templar(config)
        self.bootloc     = utils.tftpboot_location()
        # FIXME: not used anymore, can remove?
        self.verbose     = False

    def copy_bootloaders(self):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in
        /etc/cobbler/settings.
        """
        dst = self.bootloc
        grub_dst = os.path.join(dst, "grub")
        image_dst = os.path.join(dst, "images")

        # copy syslinux from one of two locations
        try:
            try:
                utils.copyfile_pattern('/var/lib/cobbler/loaders/pxelinux.0',
                        dst, api=self.api, cache=False, logger=self.logger)
                utils.copyfile_pattern('/var/lib/cobbler/loaders/menu.c32',
                        dst, api=self.api, cache=False, logger=self.logger)
            except:
                utils.copyfile_pattern('/usr/share/syslinux/pxelinux.0',
                        dst, api=self.api, cache=False, logger=self.logger)
                utils.copyfile_pattern('/usr/share/syslinux/menu.c32',
                        dst, api=self.api, cache=False, logger=self.logger)

        except:
            utils.copyfile_pattern('/usr/lib/syslinux/pxelinux.0',
                    dst, api=self.api, cache=False, logger=self.logger)
            utils.copyfile_pattern('/usr/lib/syslinux/menu.c32',
                    dst, api=self.api, cache=False, logger=self.logger)

        # copy memtest only if we find it
        utils.copyfile_pattern('/boot/memtest*', image_dst,
                require_match=False, api=self.api, cache=False, logger=self.logger)

        # copy elilo which we include for IA64 targets
        utils.copyfile_pattern('/var/lib/cobbler/loaders/elilo.efi', dst,
                require_match=False, api=self.api, cache=False, logger=self.logger)

        # copy yaboot which we include for PowerPC targets
        utils.copyfile_pattern('/var/lib/cobbler/loaders/yaboot', dst,
                require_match=False, api=self.api, cache=False, logger=self.logger)

        try:
            utils.copyfile_pattern('/usr/lib/syslinux/memdisk',
                    dst, api=self.api, cache=False, logger=self.logger)
        except:
            utils.copyfile_pattern('/usr/share/syslinux/memdisk', dst,
                    require_match=False, api=self.api, cache=False, logger=self.logger)

        # Copy grub EFI bootloaders if possible:
        utils.copyfile_pattern('/var/lib/cobbler/loaders/grub*.efi', grub_dst,
                require_match=False, api=self.api, cache=False, logger=self.logger)


    def copy_images(self):
        """
        Like copy_distros except for images.
        """
        errors = list()
        for i in self.images:
            try:
                self.copy_single_image_files(i)
            except CX, e:
                errors.append(e)
                self.logger.error(e.value)

        # FIXME: using logging module so this ends up in cobbler.log?

    def copy_single_distro_files(self, d, dirtree, symlink_ok):
        distros = os.path.join(dirtree, "images")
        distro_dir = os.path.join(distros,d.name)
        utils.mkdir(distro_dir)
        kernel = utils.find_kernel(d.kernel) # full path
        initrd = utils.find_initrd(d.initrd) # full path

        if kernel is None:
            raise CX("kernel not found: %(file)s, distro: %(distro)s" % 
                    { "file" : d.kernel, "distro" : d.name })

        if initrd is None:
            raise CX("initrd not found: %(file)s, distro: %(distro)s" % 
                    { "file" : d.initrd, "distro" : d.name })

        # Kernels referenced by remote URL are passed through to koan directly,
        # no need for copying the kernel locally:
        if not utils.file_is_remote(kernel):
            b_kernel = os.path.basename(kernel)
            dst1 = os.path.join(distro_dir, b_kernel)
            utils.linkfile(kernel, dst1, symlink_ok=symlink_ok, 
                    api=self.api, logger=self.logger)

        if not utils.file_is_remote(initrd):
            b_initrd = os.path.basename(initrd)
            dst2 = os.path.join(distro_dir, b_initrd)
            utils.linkfile(initrd, dst2, symlink_ok=symlink_ok, 
                    api=self.api, logger=self.logger)

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
        utils.linkfile(filename, newfile, api=self.api, logger=self.logger)
        return True

    def write_all_system_files(self, system):

        profile = system.get_conceptual_parent()
        if profile is None:
            raise CX("system %(system)s references a missing profile %(profile)s" % { "system" : system.name, "profile" : system.profile})

        distro = profile.get_conceptual_parent()
        image_based = False
        image = None
        if distro is None:
            if profile.COLLECTION_TYPE == "profile":
               raise CX("profile %(profile)s references a missing distro %(distro)s" % { "profile" : system.profile, "distro" : profile.distro})
            else:
               image_based = True
               image = profile

        # hack: s390 generates files per system not per interface
        if not image_based and distro.arch.startswith("s390"):
            # Always write a system specific _conf and _parm file
            f2 = os.path.join(self.bootloc, "s390x", "s_%s" % system.name)
            cf = "%s_conf" % f2
            pf = "%s_parm" % f2
            template_cf = open("/etc/cobbler/pxe/s390x_conf.template")
            template_pf = open("/etc/cobbler/pxe/s390x_parm.template")
            blended = utils.blender(self.api, True, system)
            self.templar.render(template_cf, blended, cf)
            # FIXME: profiles also need this data!
            # FIXME: the _conf and _parm files are limited to 80 characters in length
            try: 
                ipaddress = socket.gethostbyname_ex(blended["http_server"])[2][0]
            except socket.gaierror:
                ipaddress = blended["http_server"]
            kickstart_path = "http://%s/cblr/svc/op/ks/system/%s" % (ipaddress, system.name)
            # gather default kernel_options and default kernel_options_s390x
            kopts = blended.get("kernel_options","")
            hkopts = shlex.split(utils.hash_to_string(kopts))
            blended["kickstart_expanded"] = "ks=%s" % kickstart_path
            blended["kernel_options"] = hkopts
            self.templar.render(template_pf, blended, pf)

            # Write system specific zPXE file
            if system.is_management_supported():
                self.write_pxe_file(f2, system, profile, distro, distro.arch)
            else:
                # ensure the file doesn't exist
                utils.rmfile(f2)
            return

        # generate one record for each described NIC ..
 
        for (name,interface) in system.interfaces.iteritems():

            ip = interface["ip_address"]

            f1 = utils.get_config_filename(system, interface=name)
            if f1 is None:
                self.logger.warning("invalid interface recorded for system (%s,%s)" % (system.name,name))
                continue;

            if image_based:
                working_arch = image.arch
            else:
                working_arch = distro.arch

            if working_arch is None:
                raise "internal error, invalid arch supplied"

            # for tftp only ...
            grub_path = None
            if working_arch in [ "i386", "x86", "x86_64", "arm", "standard"]:
                # pxelinux wants a file named $name under pxelinux.cfg
                f2 = os.path.join(self.bootloc, "pxelinux.cfg", f1)

                # Only generating grub menus for these arch's:
                grub_path = os.path.join(self.bootloc, "grub", f1.upper())

            elif working_arch == "ia64":
                # elilo expects files to be named "$name.conf" in the root
                # and can not do files based on the MAC address
                if ip is not None and ip != "":
                    self.logger.warning("Warning: Itanium system object (%s) needs an IP address to PXE" % system.name)

                filename = "%s.conf" % utils.get_config_filename(system,interface=name)
                f2 = os.path.join(self.bootloc, filename)

            elif working_arch.startswith("ppc"):
                # Determine filename for system-specific yaboot.conf
                filename = "%s" % utils.get_config_filename(system, interface=name).lower()
                f2 = os.path.join(self.bootloc, "etc", filename)

                # Link to the yaboot binary
                f3 = os.path.join(self.bootloc, "ppc", filename)
                if os.path.lexists(f3):
                    utils.rmfile(f3)
                os.symlink("../yaboot", f3)
            else:
                continue 

            if system.is_management_supported():
                if not image_based:
                    self.write_pxe_file(f2, system, profile, distro, working_arch)
                    if grub_path:
                        self.write_pxe_file(grub_path, system, profile, distro, 
                                working_arch, format="grub")
                else:
                    self.write_pxe_file(f2, system, None, None, working_arch, image=profile)
            else:
                # ensure the file doesn't exist
                utils.rmfile(f2)
                if grub_path:
                    utils.rmfile(grub_path)

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
            if distro is None:
                raise CX("profile is missing distribution: %s, %s" % (profile.name, profile.distro))
            if distro.arch.startswith("s390"):
                listfile.write("%s\n" % profile.name)
                f2 = os.path.join(self.bootloc, "s390x", "p_%s" % profile.name)
                self.write_pxe_file(f2,None,profile,distro,distro.arch)
                cf = "%s_conf" % f2
                pf = "%s_parm" % f2
                template_cf = open("/etc/cobbler/pxe/s390x_conf.template")
                template_pf = open("/etc/cobbler/pxe/s390x_parm.template")
                blended = utils.blender(self.api, True, profile)
                self.templar.render(template_cf, blended, cf)
                # FIXME: profiles also need this data!
                # FIXME: the _conf and _parm files are limited to 80 characters in length
                try: 
                    ipaddress = socket.gethostbyname_ex(blended["http_server"])[2][0]
                except socket.gaierror:
                    ipaddress = blended["http_server"]
                kickstart_path = "http://%s/cblr/svc/op/ks/profile/%s" % (ipaddress, profile.name)
                # gather default kernel_options and default kernel_options_s390x
                kopts = blended.get("kernel_options","")
                hkopts = shlex.split(utils.hash_to_string(kopts))
                blended["kickstart_expanded"] = "ks=%s" % kickstart_path
                blended["kernel_options"] = hkopts
                self.templar.render(template_pf, blended, pf)

        listfile.close()

    def make_actual_pxe_menu(self):
        """
        Generates both pxe and grub boot menus.
        """
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")

        if default is None:
            timeout_action = "local"
        else:
            timeout_action = default.profile

        # sort the profiles
        profile_list = [profile for profile in self.profiles]
        def sort_name(a,b):
           return cmp(a.name,b.name)
        profile_list.sort(sort_name)

        # sort the images
        image_list = [image for image in self.images]
        image_list.sort(sort_name)

        # Build out menu items and append each to this master list, used for
        # the default menus:
        pxe_menu_items = ""
        grub_menu_items = ""

        # For now, profiles are the only items we want grub EFI boot menu entries for:
        for profile in profile_list:
            if not profile.enable_menu:
               # This profile has been excluded from the menu
               continue
            distro = profile.get_conceptual_parent()
            # xen distros can be ruled out as they won't boot
            if distro.name.find("-xen") != -1 or distro.arch not in ["i386", "x86_64"]:
                # can't PXE Xen
                continue
            contents = self.write_pxe_file(filename=None, system=None,
                    profile=profile, distro=distro,
                    arch=distro.arch, include_header=False)
            if contents is not None:
                pxe_menu_items = pxe_menu_items + contents + "\n"

            grub_contents = self.write_pxe_file(filename=None, system=None,
                    profile=profile, distro=distro,
                    arch=distro.arch, include_header=False, format="grub")
            if grub_contents is not None:
                grub_menu_items = grub_menu_items + grub_contents + "\n"


        # image names towards the bottom
        for image in image_list:
            if os.path.exists(image.file):
                contents = self.write_pxe_file(filename=None, system=None,
                        profile=None, distro=None, arch=image.arch, image=image)
                if contents is not None:
                    pxe_menu_items = pxe_menu_items + contents + "\n"

        # if we have any memtest files in images, make entries for them
        # after we list the profiles
        memtests = glob.glob(self.bootloc + "/images/memtest*")
        if len(memtests) > 0:
            pxe_menu_items = pxe_menu_items + "\n\n"
            for memtest in glob.glob(self.bootloc + '/images/memtest*'):
                base = os.path.basename(memtest)
                contents = self.write_memtest_pxe("/%s" % base)
                pxe_menu_items = pxe_menu_items + contents + "\n"
              
        # Write the PXE menu:
        metadata = { "pxe_menu_items" : pxe_menu_items, "pxe_timeout_profile" : timeout_action}
        outfile = os.path.join(self.bootloc, "pxelinux.cfg", "default")
        template_src = open(os.path.join(self.settings.pxe_template_dir,"pxedefault.template"))
        template_data = template_src.read()
        self.templar.render(template_data, metadata, outfile, None)
        template_src.close()

        # Write the grub menu:
        metadata = { "grub_menu_items" : grub_menu_items }
        outfile = os.path.join(self.bootloc, "grub", "efidefault")
        template_src = open(os.path.join(self.settings.pxe_template_dir, "efidefault.template"))
        template_data = template_src.read()
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

        template = os.path.join(self.settings.pxe_template_dir,"pxeprofile.template")

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


    def write_pxe_file(self, filename, system, profile, distro, arch,
            image=None, include_header=True, metadata=None, format="pxe"):
        """
        Write a configuration file for the boot loader(s).
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py

        NOTE: relevant to tftp and pseudo-PXE (s390) only

        ia64 is mostly the same as syslinux stuff, s390 is a bit
        short-circuited and simpler.  All of it goes through the
        templating engine, see the templates in /etc/cobbler for
        more details

        Can be used for different formats, "pxe" (default) and "grub".
        """

        if arch is None:
            raise "missing arch"

        if image and not os.path.exists(image.file):
            return None  # nfs:// URLs or something, can't use for TFTP

        if metadata is None:
            metadata = {}
        # ---
        # just some random variables
        template = None
        buffer = ""

        # ---
        kickstart_path = None
        kernel_path = None
        initrd_path = None
        img_path = None

        if image is None: 
            # not image based, it's something normalish

            img_path = os.path.join("/images",distro.name)
            kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
            initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        
            # Find the kickstart if we inherit from another profile
            if system:
                blended = utils.blender(self.api, True, system)
            else:
                blended = utils.blender(self.api, True, profile)
            kickstart_path = blended.get("kickstart","")
            
        else:
            # this is an image we are making available, not kernel+initrd
            if image.image_type == "direct":
                kernel_path = os.path.join("/images2",image.name)
            elif image.image_type == "memdisk":
                kernel_path = "/memdisk"
                initrd_path = os.path.join("/images2",image.name)
            else:
                # CD-ROM ISO or virt-clone image? We can't PXE boot it.
                kernel_path = None
                initrd_path = None

        if img_path is not None and not metadata.has_key("img_path"):
            metadata["img_path"] = img_path
        if kernel_path is not None and not metadata.has_key("kernel_path"):
            metadata["kernel_path"] = kernel_path
        if initrd_path is not None and not metadata.has_key("initrd_path"):
            metadata["initrd_path"] = initrd_path

        # ---
        # choose a template
        if system:
            if format == "grub":
                template = os.path.join(self.settings.pxe_template_dir, "grubsystem.template")
            else: # pxe
                if system.netboot_enabled:
                    template = os.path.join(self.settings.pxe_template_dir,"pxesystem.template")

                    if arch.startswith("s390"):
                        template = os.path.join(self.settings.pxe_template_dir,"pxesystem_s390x.template")
                    elif arch == "ia64":
                        template = os.path.join(self.settings.pxe_template_dir,"pxesystem_ia64.template")
                    elif arch.startswith("ppc"):
                        template = os.path.join(self.settings.pxe_template_dir,"pxesystem_ppc.template")
                    elif arch.startswith("arm"):
                        template = os.path.join(self.settings.pxe_template_dir,"pxesystem_arm.template")
                    elif distro.os_version.startswith("esxi"):
                        # ESXi uses a very different pxe method, using more files than
                        # a standard kickstart and different options - so giving it a dedicated
                        # PXE template makes more sense than shoe-horning it into the existing
                        # templates
                        template = os.path.join(self.settings.pxe_template_dir,"pxesystem_esxi.template")
                else:
                    # local booting on ppc requires removing the system-specific dhcpd.conf filename
                    if arch is not None and arch.startswith("ppc"):
                        # Disable yaboot network booting for all interfaces on the system
                        for (name,interface) in system.interfaces.iteritems():

                            filename = "%s" % utils.get_config_filename(system, interface=name).lower()

                            # Remove symlink to the yaboot binary
                            f3 = os.path.join(self.bootloc, "ppc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)

                            # Remove the interface-specific config file
                            f3 = os.path.join(self.bootloc, "etc", filename)
                            if os.path.lexists(f3):
                                utils.rmfile(f3)

                        # Yaboot/OF doesn't support booting locally once you've
                        # booted off the network, so nothing left to do
                        return None
                    elif arch is not None and arch.startswith("s390"):
                        template = os.path.join(self.settings.pxe_template_dir,"pxelocal_s390x.template")
                    elif arch is not None and arch.startswith("ia64"):
                        template = os.path.join(self.settings.pxe_template_dir,"pxelocal_ia64.template")
                    else:
                        template = os.path.join(self.settings.pxe_template_dir,"pxelocal.template")
        else:
            # not a system record, so this is a profile record or an image
            if arch.startswith("s390"):
                template = os.path.join(self.settings.pxe_template_dir,"pxeprofile_s390x.template")
            if arch.startswith("arm"):
                template = os.path.join(self.settings.pxe_template_dir,"pxeprofile_arm.template")
            elif format == "grub":
                template = os.path.join(self.settings.pxe_template_dir,"grubprofile.template")
            elif distro and distro.os_version.startswith("esxi"):
                # ESXi uses a very different pxe method, see comment above in the system section
                template = os.path.join(self.settings.pxe_template_dir,"pxeprofile_esxi.template")
            else:
                template = os.path.join(self.settings.pxe_template_dir,"pxeprofile.template")


        if kernel_path is not None:
            metadata["kernel_path"] = kernel_path
        if initrd_path is not None:
            metadata["initrd_path"] = initrd_path

        # generate the kernel options and append line:
        kernel_options = self.build_kernel_options(system, profile, distro,
                image, arch, kickstart_path)
        metadata["kernel_options"] = kernel_options

        if distro and distro.os_version.startswith("esxi") and filename is not None:
            append_line = "BOOTIF=%s" % (os.path.basename(filename))
        elif metadata.has_key("initrd_path") and (not arch or arch not in ["ia64", "ppc", "ppc64", "arm"]):
            append_line = "append initrd=%s" % (metadata["initrd_path"])
        else:
            append_line = "append "
        append_line = "%s%s" % (append_line, kernel_options)
        if arch.startswith("ppc") or arch.startswith("s390"):
            # remove the prefix "append"
            # TODO: this looks like it's removing more than append, really
            # not sure what's up here...
            append_line = append_line[7:]
        metadata["append_line"] = append_line

        # store variables for templating
        metadata["menu_label"] = ""
        if profile:
            if not arch in [ "ia64", "ppc", "ppc64", "s390", "s390x" ]:
                metadata["menu_label"] = "MENU LABEL %s" % profile.name
                metadata["profile_name"] = profile.name
        elif image:
            metadata["menu_label"] = "MENU LABEL %s" % image.name
            metadata["profile_name"] = image.name

        if system:
            metadata["system_name"] = system.name


        # get the template
        if kernel_path is not None:
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()
        else:
            # this is something we can't PXE boot
            template_data = "\n"

        # save file and/or return results, depending on how called.
        buffer = self.templar.render(template_data, metadata, None)
        if filename is not None:
            self.logger.info("generating: %s" % filename)
            fd = open(filename, "w")
            fd.write(buffer)
            fd.close()
        return buffer

    def build_kernel_options(self, system, profile, distro, image, arch,
            kickstart_path):
        """
        Builds the full kernel options line.
        """

        if system is not None:
            blended = utils.blender(self.api, False, system)
        elif profile is not None:
            blended = utils.blender(self.api, False, profile)
        else:
            blended = utils.blender(self.api, False, image)

        append_line = ""
        kopts = blended.get("kernel_options", dict())
        # support additional initrd= entries in kernel options.
        if "initrd" in kopts:
            append_line = ",%s" % kopts.pop("initrd")
        hkopts = utils.hash_to_string(kopts)
        append_line = "%s %s" % (append_line, hkopts)
        # FIXME - the append_line length limit is architecture specific
        # TODO: why is this checked here, before we finish adding everything?
        if len(append_line) >= 255:
            self.logger.warning("warning: kernel option length exceeds 255")

        # kickstart path rewriting (get URLs for local files)
        if kickstart_path is not None and kickstart_path != "":

            # FIXME: need to make shorter rewrite rules for these URLs

            try:
                ipaddress = socket.gethostbyname_ex(blended["http_server"])[2][0]
            except socket.gaierror:
                ipaddress = blended["http_server"]
            if system is not None and kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cblr/svc/op/ks/system/%s" % (ipaddress, system.name)
            elif kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cblr/svc/op/ks/profile/%s" % (ipaddress, profile.name)

            if distro.breed is None or distro.breed == "redhat":
                append_line = "%s ks=%s" % (append_line, kickstart_path)
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, kickstart_path)
            elif distro.breed == "debian" or distro.breed == "ubuntu":
                append_line = "%s auto=true url=%s" % (append_line, kickstart_path)

                # rework kernel options for debian distros
                translations = { 'ksdevice':"interface" , 'lang':"locale" }
                for k,v in translations.iteritems():
                    append_line = append_line.replace("%s="%k,"%s="%v)

                # interface=bootif causes a failure
                append_line = append_line.replace("interface=bootif","")
            elif distro.breed == "vmware":
                if distro.os_version.find("esxi") != -1:
                    # ESXi is very picky, it's easier just to redo the
                    # entire append line here since 
                    append_line = " ks=%s %s" % (kickstart_path, hkopts)
                    # ESXi likes even fewer options, so we remove them too
                    append_line = append_line.replace("kssendmac","")
                else:
                    append_line = "%s vmkopts=debugLogToSerial:1 mem=512M ks=%s" % \
                        (append_line, kickstart_path)
                # interface=bootif causes a failure
                append_line = append_line.replace("ksdevice=bootif","")

        if distro is not None and (distro.breed in [ "debian", "ubuntu" ]):
            # Hostname is required as a parameter, the one in the preseed is
            # not respected, so calculate if we have one here.
            # We're trying: first part of FQDN in hostname field, then system
            # name, then profile name.
            # In Ubuntu, this is at least used for the volume group name when
            # using LVM.
            domain = "local.lan"
            if system is not None:
                if system.hostname is not None and system.hostname != "":
                    # If this is a FQDN, grab the first bit
                    hostname = system.hostname.split(".")[0]
                    _domain = system.hostname.split(".")[1:]
                    if _domain:
                        domain = ".".join( _domain )
                else:
                    hostname = system.name
            else:
                hostname = profile.name

            # At least for debian deployments configured for DHCP networking
            # this values are not used, but specifying here avoids questions
            append_line = "%s hostname=%s" % (append_line, hostname)
            append_line = "%s domain=%s" % (append_line, domain)

            # A similar issue exists with suite name, as installer requires
            # the existence of "stable" in the dists directory
            append_line = "%s suite=%s" % (append_line, distro.os_version)

        # append necessary kernel args for arm architectures
        if arch is not None and arch.startswith("arm"):
            append_line = "%s fixrtc vram=48M omapfb.vram=0:24M" % append_line

        return append_line

    def write_templates(self,obj,write_file=False,path=None):
        """
        A semi-generic function that will take an object
        with a template_files hash {source:destiation}, and 
        generate a rendered file.  The write_file option 
        allows for generating of the rendered output without
        actually creating any files.

        The return value is a hash of the destination file
        names (after variable substitution is done) and the
        data in the file.
        """

        results = {}

        try:
           templates = obj.template_files
        except:
           return results

        blended = utils.blender(self.api, False, obj)

        ksmeta = blended.get("ks_meta",{})
        try:
            del blended["ks_meta"]
        except:
            pass
        blended.update(ksmeta) # make available at top level

        templates = blended.get("template_files",{})
        try:
            del blended["template_files"]
        except:
            pass
        blended.update(templates) # make available at top level

        (success, templates) = utils.input_string_or_hash(templates)

        if not success:
            return results


        for template in templates.keys():
            dest = templates[template]
            if dest is None:
               continue
 
            # Run the source and destination files through 
            # templar first to allow for variables in the path 
            template = self.templar.render(template, blended, None).strip()
            dest     = self.templar.render(dest, blended, None).strip()
            # Get the path for the destination output
            dest_dir = os.path.dirname(dest)

            # If we're looking for a single template, skip if this ones
            # destination is not it.
            if not path is None and path != dest:
               continue

            # If we are writing output to a file, force all templated 
            # configs into the rendered directory to ensure that a user 
            # granted cobbler privileges via sudo can't overwrite 
            # arbitrary system files (This also makes cleanup easier).
            if os.path.isabs(dest_dir):
               if write_file:
                   raise CX(" warning: template destination (%s) is an absolute path, skipping." % dest_dir)
                   continue
            else:
                dest_dir = os.path.join(self.settings.webdir, "rendered", dest_dir)
                dest = os.path.join(dest_dir, os.path.basename(dest))
                if not os.path.exists(dest_dir):
                    utils.mkdir(dest_dir)

            # Check for problems
            if not os.path.exists(template):
               raise CX("template source %s does not exist" % template)
               continue
            elif write_file and not os.path.isdir(dest_dir):
               raise CX("template destination (%s) is invalid" % dest_dir)
               continue
            elif write_file and os.path.exists(dest): 
               raise CX("template destination (%s) already exists" % dest)
               continue
            elif write_file and os.path.isdir(dest):
               raise CX("template destination (%s) is a directory" % dest)
               continue
            elif template == "" or dest == "": 
               raise CX("either the template source or destination was blank (unknown variable used?)" % dest)
               continue
            
            template_fh = open(template)
            template_data = template_fh.read()
            template_fh.close()

            buffer = self.templar.render(template_data, blended, None)
            results[dest] = buffer

            if write_file:
                self.logger.info("generating: %s" % dest)
                fd = open(dest, "w")
                fd.write(buffer)
                fd.close()

        return results

    def generate_gpxe(self,what,name):
       if what.lower() not in ("profile","system"):
           return "# gpxe is only valid for profiles and systems"

       distro = None
       if what == "profile":
           obj = self.api.find_profile(name=name)
           distro = obj.get_conceptual_parent()
       else:
           obj = self.api.find_system(name=name)
           distro = obj.get_conceptual_parent().get_conceptual_parent()

       # For multi-arch distros, the distro name in ks_mirror
       # may not contain the arch string, so we need to figure out
       # the path based on where the kernel is stored. We do this 
       # because some distros base future downloads on the initial
       # URL passed in, so all of the files need to be at this location
       # (which is why we can't use the images link, which just contains
       # the kernel and initrd).
       ks_mirror_name = string.join(distro.kernel.split('/')[-2:-1],'')

       blended = utils.blender(self.api, False, obj)

       ksmeta = blended.get("ks_meta",{})
       try:
           del blended["ks_meta"]
       except:
           pass
       blended.update(ksmeta) # make available at top level

       blended['distro'] = distro.name
       blended['ks_mirror_name'] = ks_mirror_name
       blended['kernel_name'] = os.path.basename(distro.kernel)
       blended['initrd_name'] = os.path.basename(distro.initrd)

       if what == "profile":
           blended['append_line'] = self.build_kernel_options(obj,None,distro,None,None,blended['kickstart'])
       else:
           blended['append_line'] = self.build_kernel_options(None,obj,distro,None,None,blended['kickstart'])

       template = None
       if distro.breed in ['redhat','debian','ubuntu','suse']:
           # all of these use a standard kernel/initrd setup so
           # they all use the same gPXE template
           template = os.path.join(self.settings.pxe_template_dir,"gpxe_%s_linux.template" % what.lower())
       elif distro.breed == 'vmware':
           if distro.os_version == 'esx4':
               # older ESX is pretty much RHEL, so it uses the standard kernel/initrd setup
               template = os.path.join(self.settings.pxe_template_dir,"gpxe_%s_linux.template" % what.lower())
           elif distro.os_version == 'esxi4':
               template = os.path.join(self.settings.pxe_template_dir,"gpxe_%s_esxi4.template" % what.lower())
           elif distro.os_version == 'esxi5':
               template = os.path.join(self.settings.pxe_template_dir,"gpxe_%s_esxi5.template" % what.lower())

       if not template:
           return "# unsupported breed/os version"

       if not os.path.exists(template):
           return "# gpxe template not found for the %s named %s (filename=%s)" % (what,name,template)

       template_fh = open(template)
       template_data = template_fh.read()
       template_fh.close()

       return self.templar.render(template_data, blended, None)

    def generate_bootcfg(self,what,name):
       if what.lower() not in ("profile","system"):
           return "# bootcfg is only valid for profiles and systems"

       distro = None
       if what == "profile":
           obj = self.api.find_profile(name=name)
           distro = obj.get_conceptual_parent()
       else:
           obj = self.api.find_system(name=name)
           distro = obj.get_conceptual_parent().get_conceptual_parent()

       # For multi-arch distros, the distro name in ks_mirror
       # may not contain the arch string, so we need to figure out
       # the path based on where the kernel is stored. We do this
       # because some distros base future downloads on the initial
       # URL passed in, so all of the files need to be at this location
       # (which is why we can't use the images link, which just contains
       # the kernel and initrd).
       ks_mirror_name = string.join(distro.kernel.split('/')[-2:-1],'')

       blended = utils.blender(self.api, False, obj)

       ksmeta = blended.get("ks_meta",{})
       try:
           del blended["ks_meta"]
       except:
           pass
       blended.update(ksmeta) # make available at top level

       blended['distro'] = ks_mirror_name

       template = os.path.join(self.settings.pxe_template_dir,"bootcfg_%s_%s.template" % (what.lower(),distro.os_version))
       if not os.path.exists(template):
           return "# boot.cfg template not found for the %s named %s (filename=%s)" % (what,name,template)

       template_fh = open(template)
       template_data = template_fh.read()
       template_fh.close()

       return self.templar.render(template_data, blended, None)

