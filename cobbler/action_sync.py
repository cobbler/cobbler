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
import yaml # Howell-Clark version
import sub_process
import sys
import glob
import traceback
import errno

import utils
from cexceptions import *
import templar 
import kickgen

import item_distro
import item_profile
import item_repo
import item_system

from Cheetah.Template import Template

from utils import _


class BootSync:
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
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)
        self.kickgen     = kickgen.KickGen(config)
        self.bootloc     = utils.tftpboot_location()

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            raise CX(_("cannot find directory: %s") % self.bootloc)

        # run pre-triggers...
        utils.run_triggers(None, "/var/lib/cobbler/triggers/sync/pre/*")

        # in case the pre-trigger modified any objects...
        self.api.deserialize()
        self.distros  = self.config.distros()
        self.profiles = self.config.profiles()
        self.systems  = self.config.systems()
        self.settings = self.config.settings()
        self.repos    = self.config.repos()

        # execute the core of the sync operation
        self.clean_trees()
        self.copy_bootloaders()
        self.copy_distros()
        for x in self.systems:
            self.write_all_system_files(x)
        self.retemplate_all_yum_repos()
        if self.settings.manage_dhcp:
           # these functions DRT for ISC or dnsmasq
           self.write_dhcp_file()
           self.regen_ethers()
           self.regen_hosts()
        self.make_pxe_menu()

        # run post-triggers
        utils.run_triggers(None, "/var/lib/cobbler/triggers/sync/post/*")
        return True

    def copy_bootloaders(self):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in
        /var/lib/cobbler/settings.
        """
        for loader in self.settings.bootloaders.keys():
            path = self.settings.bootloaders[loader]
            newname = os.path.basename(path)
            destpath = os.path.join(self.bootloc, newname)
            utils.copyfile(path, destpath)
        utils.copyfile("/var/lib/cobbler/menu.c32", os.path.join(self.bootloc, "menu.c32"))

        # Copy memtest to tftpboot if package is installed on system          
        for memtest in glob.glob('/boot/memtest*'):
            base = os.path.basename(memtest)
            utils.copyfile(memtest,os.path.join(self.bootloc,"images",base))

    def write_dhcp_file(self):
        """
        DHCP files are written when manage_dhcp is set in
        /var/lib/cobbler/settings.
        """
        
        settings_file = self.settings.dhcpd_conf
        template_file = "/etc/cobbler/dhcp.template"
        mode = self.settings.manage_dhcp_mode.lower()
        if mode == "dnsmasq":
            settings_file = self.settings.dnsmasq_conf
            template_file = "/etc/cobbler/dnsmasq.template"

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error writing template to file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # build each per-system definition
        # as configured, this only works for ISC, patches accepted
        # from those that care about Itanium.  elilo seems to be unmaintained
        # so additional maintaince in other areas may be required to keep
        # this working.

        elilo = os.path.basename(self.settings.bootloaders["ia64"])

        system_definitions = {}
        counter = 0

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.

        for system in self.systems:
            profile = system.get_conceptual_parent()
            distro  = profile.get_conceptual_parent()
            for (name, interface) in system.interfaces.iteritems():

                mac  = interface["mac_address"]
                ip   = interface["ip_address"]
                host = interface["hostname"]

                if mac is None or mac == "":
                    # can't write a DHCP entry for this system
                    continue 
 
                counter = counter + 1
                systxt = "" 

                if mode == "isc":

                    # the label the entry after the hostname if possible
                    if host is not None and host != "":
                        systxt = "\nhost %s {\n" % host
                        if self.settings.isc_set_host_name:
                            systxt = systxt + "    option host-name = %s;\n" % host
                    else:
                        systxt = "\nhost generic%d {\n" % counter

                    if distro.arch == "ia64":
                        # can't use pxelinux.0 anymore
                        systxt = systxt + "    filename \"/%s\";\n" % elilo
                    systxt = systxt + "    hardware ethernet %s;\n" % mac
                    if ip is not None and ip != "":
                        systxt = systxt + "    fixed-address %s;\n" % ip
                    systxt = systxt + "}\n"

                else:
                    # dnsmasq.  don't have to write IP and other info here, but we do tag
                    # each MAC based on the arch of it's distro, if it needs something other
                    # than pxelinux.0 -- for these arches, and these arches only, a dnsmasq
                    # reload (full "cobbler sync") would be required after adding the system
                    # to cobbler, just to tag this relationship.

                    if ip is not None and ip != "":
                        if distro.arch.lower() == "ia64":
                            systxt = "dhcp-host=net:ia64," + ip + "\n"
                        # support for other arches needs modifications here
                        else:
                            systxt = ""

                dhcp_tag = interface["dhcp_tag"]
                if dhcp_tag == "":
                   dhcp_tag = "default"

                if not system_definitions.has_key(dhcp_tag):
                    system_definitions[dhcp_tag] = ""
                system_definitions[dhcp_tag] = system_definitions[dhcp_tag] + systxt

        # we are now done with the looping through each interface of each system

        metadata = {
           "insert_cobbler_system_definitions" : system_definitions.get("default",""),
           "date"           : time.asctime(time.gmtime()),
           "cobbler_server" : self.settings.server,
           "next_server"    : self.settings.next_server,
           "elilo"          : elilo
        }

        # now add in other DHCP expansions that are not tagged with "default"
        for x in system_definitions.keys():
            if x == "default":
                continue
            metadata["insert_cobbler_system_definitions_%s" % x] = system_definitions[x]   

        self.templar.render(template_data, metadata, settings_file, None)

    def regen_ethers(self):
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date
        # every time we add a system.
        # read 'man ethers' for format info
        fh = open("/etc/ethers","w+")
        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                mac = interface["mac_address"]
                ip  = interface["ip_address"]
                if mac is None or mac == "":
                    # can't write this w/o a MAC address
                    continue
                if ip is not None and ip != "":
                    fh.write(mac.upper() + "\t" + ip + "\n")
        fh.close()

    def regen_hosts(self):
        # dnsmasq knows how to read this database for host info
        # (other things may also make use of this later)
        fh = open("/var/lib/cobbler/cobbler_hosts","w+")
        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                mac  = interface["mac_address"]
                host = interface["hostname"]
                ip   = interface["ip_address"]
                if mac is None or mac == "":
                    continue
                if host is not None and host != "" and ip is not None and ip != "":
                    fh.write(ip + "\t" + host + "\n")
        fh.close()


    #def templatify(self, data, metadata, outfile):
    #    for x in metadata.keys():
    #        template_data = template_data.replace("$%s" % x, metadata[x])

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and virt tree info and then create
        directories.

        Note: for SELinux reasons, some information goes in /tftpboot, some in /var/www/cobbler
        and some must be duplicated in both.  This is because PXE needs tftp, and auto-kickstart
        and Virt operations need http.   Only the kernel and initrd images are duplicated, which is
        unfortunate, though SELinux won't let me give them two contexts, so symlinks are not
        a solution.  *Otherwise* duplication is minimal.
        """

        # clean out parts of webdir and all of /tftpboot/images and /tftpboot/pxelinux.cfg
        for x in os.listdir(self.settings.webdir):
            path = os.path.join(self.settings.webdir,x)
            if os.path.isfile(path):
                if not x.endswith(".py"):
                    utils.rmfile(path)
            if os.path.isdir(path):
                if not x in ["web", "webui", "localmirror","repo_mirror","ks_mirror","images","links","repo_profile","repo_system","svc"] :
                    # delete directories that shouldn't exist
                    utils.rmtree(path)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles","repo_profile","repo_system"]:
                    # clean out directory contents
                    utils.rmtree_contents(path)
        utils.rmtree_contents(os.path.join(self.bootloc, "pxelinux.cfg"))
        utils.rmtree_contents(os.path.join(self.bootloc, "images"))

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
            print _("sync distro: %s") % d.name
            self.copy_single_distro_files(d)

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
            if kernel.startswith(dirtree):
                utils.linkfile(kernel, os.path.join(distro_dir, b_kernel))
            else:
                utils.copyfile(kernel, os.path.join(distro_dir, b_kernel))
            if initrd.startswith(dirtree):
                utils.linkfile(initrd, os.path.join(distro_dir, b_initrd))
            else:
                utils.copyfile(initrd, os.path.join(distro_dir, b_initrd))

    def retemplate_all_yum_repos(self):
        for p in self.profiles:
            self.retemplate_yum_repos(p,True)
        for system in self.systems:
            self.retemplate_yum_repos(system,False)

    def retemplate_yum_repos(self,obj,is_profile):
        """
        Yum repository management files are in self.settings.webdir/repo_mirror/$name/config.repo
        and also potentially in listed in the source_repos structure of the distro object, however
        these files have server URLs in them that must be templated out.  This function does this.
        """
        blended  = utils.blender(self.api, False, obj)

        if is_profile:
           outseg = "repos_profile"
        else:
           outseg = "repos_system"

        input_files = []

        # chance old versions from upgrade do not have a source_repos
        # workaround for user bug
        if not blended.has_key("source_repos"):
            blended["source_repos"] = []

        # tack on all the install source repos IF there is more than one.
        # this is basically to support things like RHEL5 split trees
        # if there is only one, then there is no need to do this.

        for r in blended["source_repos"]:
            filename = self.settings.webdir + "/" + "/".join(r[0].split("/")[4:])
            input_files.append(filename)

        for repo in blended["repos"]:
            input_files.append(os.path.join(self.settings.webdir, "repo_mirror", repo, "config.repo"))

        for infile in input_files:
            if infile.find("ks_mirror") == -1:
                dispname = infile.split("/")[-2]
            else:
                dispname = infile.split("/")[-1].replace(".repo","")
            confdir = os.path.join(self.settings.webdir, outseg)
            outdir = os.path.join(confdir, blended["name"])
            utils.mkdir(outdir) 
            try:
                infile_h = open(infile)
            except:
                print _("WARNING: cobbler reposync needs to be run on repo (%s), then re-run cobbler sync") % dispname
                continue
            infile_data = infile_h.read()
            infile_h.close()
            outfile = os.path.join(outdir, "%s.repo" % (dispname))
            self.templar.render(infile_data, blended, outfile, None)


    def write_all_system_files(self,system):

        profile = system.get_conceptual_parent()
        if profile is None:
            raise CX(_("system %(system)s references a missing profile %(profile)s") % { "system" : system.name, "profile" : system.profile})
        distro = profile.get_conceptual_parent()
        if distro is None:
            raise CX(_("profile %(profile)s references a missing distro %(distro)s") % { "profile" : system.profile, "distro" : profile.distro})

        # this used to just generate a single PXE config file, but now must
        # generate one record for each described NIC ...
 
        counter = 0
        for (name,interface) in system.interfaces.iteritems():

            ip = interface["ip_address"]

            f1 = utils.get_config_filename(system,interface=name)

            # for tftp only ...
            if distro.arch in [ "x86", "x86_64", "standard"]:
                # pxelinux wants a file named $name under pxelinux.cfg
                f2 = os.path.join(self.bootloc, "pxelinux.cfg", f1)
            if distro.arch == "ia64":
                # elilo expects files to be named "$name.conf" in the root
                # and can not do files based on the MAC address
                if ip is not None and ip != "":
                    print _("Warning: Itanium system object (%s) needs an IP address to PXE") % system.name

                filename = "%s.conf" % utils.get_config_filename(system,interface=name)
                f2 = os.path.join(self.bootloc, filename)

            f3 = os.path.join(self.settings.webdir, "systems", f1)

            if system.netboot_enabled and system.is_pxe_supported():
                if distro.arch in [ "x86", "x86_64", "standard"]:
                    self.write_pxe_file(f2,system,profile,distro,False)
                if distro.arch == "ia64":
                    self.write_pxe_file(f2,system,profile,distro,True)
            else:
                # ensure the file doesn't exist
                utils.rmfile(f2)

        counter = counter + 1
        

    def make_pxe_menu(self):
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

        # build out the menu entries
        pxe_menu_items = ""
        for profile in profile_list:
            distro = profile.get_conceptual_parent()
            contents = self.write_pxe_file(None,None,profile,distro,False,include_header=False)
            if contents is not None:
                pxe_menu_items = pxe_menu_items + contents + "\n"

        # if we have any memtest files in images, make entries for them
        # after we list the profiles
        memtests = glob.glob(self.bootloc + "/images/memtest*")
        if len(memtests) > 0:
            pxe_menu_items = pxe_menu_items + "\n\n"
            for memtest in glob.glob(self.bootloc + '/memtest*'):
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



    def write_pxe_file(self,filename,system,profile,distro,is_ia64, include_header=True):
        """
        Write a configuration file for the boot loader(s).
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py

        NOTE: relevant to tftp only
        """

        # ---
        # system might have netboot_enabled set to False (see item_system.py), if so, 
        # don't do anything else and flag the error condition.
        if system is not None and not system.netboot_enabled:
            return None

        # ---
        # just some random variables
        template = None
        metadata = {}
        buffer = ""

        # ---
        # find kernel and initrd
        kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        
        # Find the kickstart if we inherit from another profile
        kickstart_path = utils.blender(self.api, True, profile)["kickstart"]

        # ---
        # choose a template
        if system is None:
            template = "/etc/cobbler/pxeprofile.template"
        elif not is_ia64:
            template = "/etc/cobbler/pxesystem.template"
        else:
            template = "/etc/cobbler/pxesystem_ia64.template"

        # now build the kernel command line
        if system is not None:
            blended = utils.blender(self.api, True, system)
        else:
            blended = utils.blender(self.api, True,profile)
        kopts = blended["kernel_options"]

        # generate the append line
        append_line = "append %s" % utils.hash_to_string(kopts)
        if not is_ia64:
            append_line = "%s initrd=%s" % (append_line, initrd_path)
        if len(append_line) >= 255 + len("append "):
            print _("warning: kernel option length exceeds 255")

        # kickstart path rewriting (get URLs for local files)
        if kickstart_path is not None and kickstart_path != "":

            if system is not None and kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cblr/svc/?op=ks&system=%s" % (blended["http_server"], system.name)
            elif kickstart_path.startswith("/") or kickstart_path.find("/cobbler/kickstarts/") != -1:
                kickstart_path = "http://%s/cblr/svc/?op=ks&profile=%s" % (blended["http_server"], profile.name)

            if distro.breed is None or distro.breed == "redhat":
                append_line = "%s ks=%s" % (append_line, kickstart_path)
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, kickstart_path)
            elif distro.breed == "debian":
                append_line = "%s auto=true url=%s" % (append_line, kickstart_path)
                append_line = append_line.replace("ksdevice","interface")

        # store variables for templating
        metadata["menu_label"] = ""
        if not is_ia64 and system is None:
            metadata["menu_label"] = "MENU LABEL %s" % profile.name
        metadata["profile_name"] = profile.name
        metadata["kernel_path"] = kernel_path
        metadata["initrd_path"] = initrd_path
        metadata["append_line"] = append_line

        # get the template
        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        # save file and/or return results, depending on how called.
        buffer = self.templar.render(template_data, metadata, None)
        if filename is not None:
            fd = open(filename, "w")
            fd.write(buffer)
            fd.close()
        return buffer




