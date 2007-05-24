"""
Builds out a TFTP/cobbler boot tree based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006, Red Hat, Inc
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

import utils
import cobbler_msg
import cexceptions
import traceback
import errno

import item_distro
import item_profile
import item_system

from Cheetah.Template import Template

class BootSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=False):
        """
        Constructor
        """
        self.verbose  = verbose
        self.config   = config
        self.distros  = config.distros()
        self.profiles = config.profiles()
        self.systems  = config.systems()
        self.settings = config.settings()
        self.repos    = config.repos()

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.settings.tftpboot):
            raise cexceptions.CobblerException("no_dir",self.settings.tftpboot)
        # not having a /var/www/cobbler is ok, the app will create it since
        # no other package has to own it.
        self.clean_trees()
        self.copy_koan()
        self.copy_bootloaders()
        self.copy_distros()
        self.validate_kickstarts()
        self.build_trees()
        if self.settings.manage_dhcp:
           # these functions DRT for ISC or dnsmasq
           self.write_dhcp_file()
           self.regen_ethers()
           self.regen_hosts()
           self.restart_dhcp()
        self.make_pxe_menu()
        return True

    def restart_dhcp(self):
        """
        DHCP restarts need to be made when the config file is
        changed. ISC or DNSMASQ.  Support for ISC omshell not
        yet available (adding dynamically w/o restart).
        """
        try:
            mode = self.settings.manage_dhcp_mode.lower()
            service = "dhcpd"
            if mode == "dnsmasq":
                service = "dnsmasq"
            retcode = self.service(service, "restart")
            if retcode != 0:
                print >>sys.stderr, "Warning: %s restart failed" % service
        except OSError, e:
            print >>sys.stderr, "Warning: %s restart failed: " % service, e

    def copy_koan(self):
        """
        This is just for the "enchant" feature which a lot of folks
        probably don't use... enchant automates an SSH into a remote
        system, including koan installation if need be.
        """
        koan_path = self.settings.koan_path
        if koan_path is None or koan_path == "":
            return
        if not os.path.isfile(koan_path):
            raise cexceptions.CobblerException("exc_koan_path")
        base = os.path.basename(koan_path)
        self.copyfile(koan_path, os.path.join(self.settings.webdir, base))

    def copy_bootloaders(self):
        """
        Copy bootloaders to the configured tftpboot directory
        NOTE: we support different arch's if defined in
        /var/lib/cobbler/settings.
        """
        for loader in self.settings.bootloaders.keys():
            path = self.settings.bootloaders[loader]
            newname = os.path.basename(path)
            destpath = os.path.join(self.settings.tftpboot, newname)
            self.copyfile(path, destpath)
        self.copyfile("/var/lib/cobbler/menu.c32", os.path.join(self.settings.tftpboot, "menu.c32"))

    def write_dhcp_file(self):
        """
        DHCP files are written when manage_dhcp is set in
        /var/lib/cobbler/settings.
        """
        
        settings_file = self.settings.dhcpd_conf
        template_file = "/etc/cobbler/dhcp.template"
        mode = self.settings.manage_dhcp_mode.lower()
        # print "my mode is: %s" % mode
        if mode == "dnsmasq":
            settings_file = self.settings.dnsmasq_conf
            template_file = "/etc/cobbler/dnsmasq.template"

        try:
            f2 = open(template_file,"r")
        except:
            raise cexceptions.CobblerException("exc_no_template",template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # build each per-system definition
        # as configured, this only works for ISC, patches accepted
        # from those that care about Itanium.
        elilo = os.path.basename(self.settings.bootloaders["ia64"])

        system_definitions = ""
        counter = 0
        for system in self.systems:
            if not utils.is_mac(system.name):
                # can't do per-system dhcp features if the system
                # hostname is not a MAC, therefore the templating
                # gets to be pretty lame.  The general rule here is
                # if you want to PXE IA64 boxes, you need to use
                # the MAC as the system name.
                continue

            
            counter = counter + 1
            systxt = "" 
            if mode == "isc":

                systxt = "\nhost label%d {\n" % counter
                profile = self.profiles.find(system.profile)
                distro  = self.distros.find(profile.distro)
                if distro.arch == "ia64":
                    # can't use pxelinux.0 anymore
                    systxt = systxt + "    filename \"/%s\";\n" % elilo
                systxt = systxt + "    hardware ethernet %s;\n" % system.name
                if system.pxe_address != "":
                    systxt = systxt + "    fixed-address %s;\n" % system.pxe_address
                systxt = systxt + "    next-server %s;\n" % self.settings.next_server
                systxt = systxt + "}\n"

            else:
                # dnsmasq.  don't have to write IP and other info here, but we do tag
                # each MAC based on the arch of it's distro, if it needs something other
                # than pxelinux.0 -- for these arches, and these arches only, a dnsmasq
                # reload (full "cobbler sync") would be required after adding the system
                # to cobbler, just to tag this relationship.

                profile = self.profiles.find(system.profile)
                distro  = self.distros.find(profile.distro)
                if system.pxe_address != "":
                    if distro.arch.lower() == "ia64":
                        systxt = "dhcp-host=net:ia64," + system.pxe_address + "\n"
                    # support for other arches needs modifications here
                    else:
                        systxt = ""

            system_definitions = system_definitions + systxt

        metadata = {
           "insert_cobbler_system_definitions" : system_definitions,
           "date"           : time.asctime(time.gmtime()),
           "cobbler_server" : self.settings.server,
           "next_server"    : self.settings.next_server,
           "elilo"          : elilo
        }
        # print "writing to: %s" % settings_file
        self.apply_template(template_data, metadata, settings_file)

    def regen_ethers(self):
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date
        # every time we add a system.
        # read 'man ethers' for format info
        fh = open("/etc/ethers","w+")
        for sys in self.systems:
            if not utils.is_mac(sys.name):
                # hopefully no one uses non-mac system ID's anymore, but I'm not sure.
                # these need to be deprecated
                continue
            if sys.pxe_address != "":
                fh.write(sys.name.upper() + "\t" + sys.pxe_address + "\n")
        fh.close()

    def regen_hosts(self):
        # dnsmasq knows how to read this database for host info
        # (other things may also make use of this later)
        fh = open("/var/lib/cobbler/cobbler_hosts","w+")
        for sys in self.systems:
            if not utils.is_mac(sys.name):
                continue
            if sys.hostname != "" and sys.pxe_address != "":
                fh.write(sys.pxe_address + "\t" + sys.hostname + "\n")
        fh.close()


    def templatify(self, data, metadata, outfile):
        for x in metadata.keys():
            template_data = template_data.replace("$%s" % x, metadata[x])

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
                    self.rmfile(path)
            if os.path.isdir(path):
                if not x in ["localmirror","repo_mirror","ks_mirror","kickstarts","kickstarts_sys","distros","images","systems","profiles","links"] :
                    # delete directories that shouldn't exist
                    self.rmtree(path)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles"]:
                    # clean out directory contents
                    self.rmtree_contents(path)
        self.rmtree_contents(os.path.join(self.settings.tftpboot, "pxelinux.cfg"))
        self.rmtree_contents(os.path.join(self.settings.tftpboot, "images"))

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
            print "sync distro: %s" % d.name
            self.copy_single_distro_files(d)

    def copy_single_distro_files(self, d):
        for dirtree in [self.settings.tftpboot, self.settings.webdir]: 
            distros = os.path.join(dirtree, "images")
            distro_dir = os.path.join(distros,d.name)
            self.mkdir(distro_dir)
            kernel = utils.find_kernel(d.kernel) # full path
            initrd = utils.find_initrd(d.initrd) # full path
            if kernel is None or not os.path.isfile(kernel):
                raise cexceptions.CobblerException("sync_kernel", d.kernel, d.name)
            if initrd is None or not os.path.isfile(initrd):
                raise cexceptions.CobblerException("sync_initrd", d.initrd, d.name)
            b_kernel = os.path.basename(kernel)
            b_initrd = os.path.basename(initrd)
            self.copyfile(kernel, os.path.join(distro_dir, b_kernel))
            self.copyfile(initrd, os.path.join(distro_dir, b_initrd))

    def validate_kickstarts(self):
        """
        Similar to what we do for distros, ensure all the kickstarts
        in conf file are valid.   kickstarts are referenced by URL
        (http or ftp), can stay as is.  kickstarts referenced by absolute
        path (i.e. are files path) will be mirrored over http.
        """

        self.validate_kickstarts_per_profile()
        self.validate_kickstarts_per_system()
        return True

    def validate_kickstarts_per_profile(self):
        """
        Koan provisioning (Virt + auto-ks) needs kickstarts
        per profile.  Validate them as needed.  Local kickstarts
        get template substitution.  Since http:// kickstarts might
        get generated via magic URLs, those are *not* substituted.
        NFS kickstarts are also not substituted when referenced
        by NFS URL's as we don't copy those files over to the cobbler
        directories.  They are supposed to be live such that an
        admin can update those without needing to run 'sync' again.

        NOTE: kickstart only uses the web directory (if it uses them at all)
        """

        for g in self.profiles:
           print "sync profile: %s" % g.name
           self.validate_kickstart_for_specific_profile(g)

    def validate_kickstart_for_specific_profile(self,g):
        distro = self.distros.find(g.distro)
        if distro is None:
           raise cexceptions.CobblerException("orphan_distro2", g.name, g.distro)
        kickstart_path = utils.find_kickstart(g.kickstart)
        if kickstart_path is not None and os.path.exists(g.kickstart):
           # the input is an *actual* file, hence we have to copy it
           copy_path = os.path.join(
               self.settings.webdir,
               "kickstarts", # profile kickstarts go here
               g.name
           )
           self.mkdir(copy_path)
           dest = os.path.join(copy_path, "ks.cfg")
           try:
                will_it_blend = (distro.ks_meta, g.ks_meta)
                meta = self.blend_options(False, will_it_blend) 
                meta["yum_repo_stanza"] = self.generate_repo_stanza(g)
                meta["yum_config_stanza"] = self.generate_config_stanza(g)
                meta["kickstart_done"] = self.generate_kickstart_signal(g, is_system=False)
                kfile = open(kickstart_path)
                self.apply_template(kfile, meta, dest)
                kfile.close()
           except:
                traceback.print_exc() # leave this in, for now...
                msg = "err_kickstart2"
                raise cexceptions.CobblerException(msg,kickstart_path,dest)

    def generate_kickstart_signal(self, obj, is_system=False):
        pattern = "wget http://%s/cblr/watcher.py?%s_%s=%s -b"
        if is_system:
            return pattern % (self.settings.server, "system", "done", obj.name)
        else:
            return pattern % (self.settings.server, "profile", "done", obj.name)

    def generate_repo_stanza(self, profile):
        # returns the line of repo additions (Anaconda supports in FC-6 and later) that adds
        # the list of repos to things that Anaconda can install from.  This corresponds
        # will replace "TEMPLATE::yum_repo_stanza" in a cobbler kickstart file.
        buf = ""
        repos = profile.repos
        for r in repos:
            repo = self.repos.find(r)
            if repo is None:
                continue
            http_url = "http://%s/cblr/repo_mirror/%s" % (self.settings.server, repo.name)
            buf = buf + "repo --name=%s --baseurl=%s\n" % (repo.name, http_url)
        distro = self.distros.find(profile.distro)

        # tack on all the install source repos IF there is more than one.
        # this is basically to support things like RHEL5 split trees
        # if there is only one, then there is no need to do this.
        if len(distro.source_repos) > 1:
            for r in distro.source_repos:
                base = r[1].split("/")[-1].replace(".repo","")
                buf = buf + "repo --name=%s --baseurl=%s\n" % (base, r[1])

        return buf

    def generate_config_stanza(self, profile):
        # returns the line in post that would configure yum to use repos added with "cobbler repo add"
        repos = profile.repos
        buf = ""
        for r in repos:
            repo = self.repos.find(r)
            if repo is None: 
                continue
            repo.local_filename = repo.local_filename.replace(".repo","")
            if not (repo.local_filename is None) or (repo.local_filename == ""):
                buf = buf + "wget http://%s/cblr/repo_mirror/%s/config.repo --output-document=/etc/yum.repos.d/%s.repo\n" % (self.settings.server, repo.name, repo.local_filename)    

        # now install the core repos
        distro = self.distros.find(profile.distro)
        if self.settings.yum_core_mirror_from_server:
            for r in distro.source_repos:
                short = r[0].split("/")[-1]
                buf = buf + "wget %s --output-document=/etc/yum.repos.d/%s\n" % (r[0], short)

            # if there were any core repos, install the voodoo to disable the OS public core
            # location -- FIXME: should probably run sed on the files, rather than rename them.
            if len(distro.source_repos) > 0:
                for x in ["fedora-core", "Centos-Base"] :
                    buf = buf + "test -e /etc/yum.repos.d/%s.repo && mv /etc/yum.repos.d/%s.repo /etc/yum.repos.d/disabled-%s\n" % (x,x,x)

        return buf

    def validate_kickstarts_per_system(self):
        """
        PXE provisioning needs kickstarts evaluated per system.
        Profiles would normally be sufficient, but not in cases
        such as static IP, where we want to be able to do templating
        on a system basis.

        NOTE: kickstart only uses the web directory (if it uses them at all)
        """

        for s in self.systems:
            print "sync system: %s" % s.name
            self.validate_kickstart_for_specific_system(s)

    def validate_kickstart_for_specific_system(self,s):
        profile = self.profiles.find(s.profile)
        if profile is None:
            raise cexceptions.CobblerException("orphan_profile2",s.name,s.profile)
        distro = self.distros.find(profile.distro)
        kickstart_path = utils.find_kickstart(profile.kickstart)
        if kickstart_path and os.path.exists(kickstart_path):
            pxe_fn = self.get_pxe_filename(s.name)
            copy_path = os.path.join(self.settings.webdir,
                "kickstarts_sys", # system kickstarts go here
                pxe_fn
            )
            self.mkdir(copy_path)
            dest = os.path.join(copy_path, "ks.cfg")
            try:
                meta = self.blend_options(False,(
                    distro.ks_meta,
                    profile.ks_meta,
                    s.ks_meta
                ))
                meta["yum_repo_stanza"] = self.generate_repo_stanza(profile)
                meta["yum_config_stanza"] = self.generate_config_stanza(profile)
                meta["kickstart_done"]  = self.generate_kickstart_signal(profile, is_system=True)
                kfile = open(kickstart_path)
                self.apply_template(kfile, meta, dest)
                kfile.close()
            except:
                msg = "err_kickstart2"
                raise cexceptions.CobblerException(msg,s.kickstart,dest)

    def apply_template(self, data_input, metadata, out_path):
        """
        Take filesystem file kickstart_input, apply metadata using
        Cheetah and save as out_path.
        """


        if type(data_input) != str:
           data = data_input.read()
        else:
           data = data_input

        # backward support for Cobbler's legacy (and slightly more readable) 
        # template syntax.
        data = data.replace("TEMPLATE::","$")

        data = "#errorCatcher Echo\n" + data
       
        t = Template(source=data, searchList=[metadata])
        data_out = str(t)
        if out_path is not None:
            self.mkdir(os.path.dirname(out_path))
            fd = open(out_path, "w+")
            fd.write(data_out)
            fd.close()
        return data_out

    def build_trees(self):
        """
        Now that kernels and initrds are copied and kickstarts are all valid,
        build the pxelinux.cfg tree, which contains a directory for each
        configured IP or MAC address.  Also build a tree for Virt info.

        NOTE: some info needs to go in TFTP and HTTP directories, but not all.
        Usually it's just one or the other.

        """

        self.write_listings()

        # create pxelinux.cfg under tftpboot
        # and file for each MAC or IP (hex encoded 01-XX-XX-XX-XX-XX-XX)

        for d in self.distros:
            self.write_distro_file(d)

        for p in self.profiles:
            self.write_profile_file(p)

        for system in self.systems:
            self.write_all_system_files(system)

    def write_all_system_files(self,system):

        profile = self.profiles.find(system.profile)
        if profile is None:
            raise cexceptions.CobblerException("orphan_profile2",system.name,system.profile)
        distro = self.distros.find(profile.distro)
        if distro is None:
            raise cexceptions.CobblerException("orphan_distro2",system.profile,profile.distro)
        f1 = self.get_pxe_filename(system.name)

        # tftp only


        if distro.arch in [ "x86", "x86_64", "standard"]:
            # pxelinux wants a file named $name under pxelinux.cfg
            f2 = os.path.join(self.settings.tftpboot, "pxelinux.cfg", f1)
        if distro.arch == "ia64":
            # elilo expects files to be named "$name.conf" in the root
            # and can not do files based on the MAC address
            if system.pxe_address == "" or system.pxe_address is None or not utils.is_ip(system.pxe_address):
                raise cexceptions.CobblerException("exc_ia64_noip",system.name)


            filename = "%s.conf" % self.get_pxe_filename(system.pxe_address)
            f2 = os.path.join(self.settings.tftpboot, filename)

        f3 = os.path.join(self.settings.webdir, "systems", f1)


        if system.netboot_enabled:
            if distro.arch in [ "x86", "x86_64", "standard"]:
                self.write_pxe_file(f2,system,profile,distro,False)
            if distro.arch == "ia64":
                self.write_pxe_file(f2,system,profile,distro,True)
        else:
            # ensure the file doesn't exist
            self.rmfile(f2)

        self.write_system_file(f3,system)


    def get_pxe_filename(self,name_input):
        """
        The configuration file for each system pxe uses is either
        a form of the MAC address of the hex version of the IP.  Not sure
        about ipv6 (or if that works).  The system name in the config file
        is either a system name, an IP, or the MAC, so figure it out, resolve
        the host if needed, and return the pxe directory name.
        """
        if name_input == "default":
            return "default"
        name = utils.find_system_identifier(name_input)
        if utils.is_ip(name):
            return utils.get_host_ip(name)
        elif utils.is_mac(name):
            return "01-" + "-".join(name.split(":")).lower()
        else:
            raise cexceptions.CobblerException("err_resolv", name)
        
    def make_pxe_menu(self):
        # only do this if there is NOT a system named default.
        default = self.systems.find("default")
        if default is not None:
            return
        
        fname = os.path.join(self.settings.tftpboot, "pxelinux.cfg", "default")

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
            distro = self.distros.find(profile.distro)
            contents = self.write_pxe_file(None,None,profile,distro,False,include_header=False)
            if contents is not None:
                pxe_menu_items = pxe_menu_items + contents + "\n"
 
        # save the template.
        metadata = { "pxe_menu_items" : pxe_menu_items }
        outfile = os.path.join(self.settings.tftpboot, "pxelinux.cfg", "default")
        self.apply_template(template_data, metadata, outfile)
        template_src.close()


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
        kickstart_path = profile.kickstart

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
            kopts = self.blend_options(True,(
                self.settings.kernel_options,
                profile.kernel_options,
                distro.kernel_options,
                system.kernel_options
            ))
        else:
            kopts = self.blend_options(True,(
                self.settings.kernel_options,
                profile.kernel_options,
                distro.kernel_options
            ))


        # ---
        # generate the append line
        append_line = "append %s" % self.hash_to_string(kopts)
        if not is_ia64:
            append_line = "%s initrd=%s" % (append_line, initrd_path)
        if len(append_line) >= 255 + len("append "):
            print "warning: kernel option length exceeds 255"

        # ---
        # kickstart path rewriting (get URLs for local files)
        if kickstart_path is not None and kickstart_path != "":

            if system is not None and kickstart_path.startswith("/"):
                pxe_fn = self.get_pxe_filename(system.name)
                kickstart_path = "http://%s/cblr/kickstarts_sys/%s/ks.cfg" % (self.settings.server, pxe_fn)
            elif kickstart_path.startswith("/") or kickstart_path.find("/cobbler/kickstarts/") != -1:
                kickstart_path = "http://%s/cblr/kickstarts/%s/ks.cfg" % (self.settings.server, profile.name)

            if distro.breed is None or distro.breed == "redhat":
                append_line = "%s ks=%s" % (append_line, kickstart_path)
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, kickstart_path)

        # ---
        # store variables for templating
        metadata["menu_label"] = ""
        if not is_ia64 and system is None:
            metadata["menu_label"] = "MENU LABEL %s" % profile.name
        metadata["profile_name"] = profile.name
        metadata["kernel_path"] = kernel_path
        metadata["initrd_path"] = initrd_path
        metadata["append_line"] = append_line

        # ---
        # get the template
        template_fh = open(template)
        template_data = template_fh.read()
        template_fh.close()

        # ---
        # save file and/or return results, depending on how called.
        buffer = self.apply_template(template_data, metadata, None)
        if filename is not None:
            fd = self.open_file(filename, "w")
            self.tee(fd, buffer)
            self.close_file(fd)
        return buffer


    def write_listings(self):
        """
        Creates a very simple index of available systems and profiles
        that cobbler knows about.  Just the names, no details.
        """
        names1 = [x.name for x in self.profiles]
        names2 = [x.name for x in self.systems]
        data1 = yaml.dump(names1)
        data2 = yaml.dump(names2)
        fd1 = self.open_file(os.path.join(self.settings.webdir, "profile_list"), "w+")
        fd2 = self.open_file(os.path.join(self.settings.webdir, "system_list"), "w+")
        self.tee(fd1, data1)
        self.tee(fd2, data2)
        self.close_file(fd1)
        self.close_file(fd2)

    def write_distro_file(self,distro):
        """
        Create distro information for virt install

        NOTE: relevant to http only
        """

        clone = item_distro.Distro(self.config)
        clone.from_datastruct(distro.to_datastruct())

        filename = os.path.join(self.settings.webdir,"distros",clone.name)
        will_it_blend = (self.settings.kernel_options, distro.kernel_options)
        clone.kernel_options = self.blend_options(True,will_it_blend)
        fd = self.open_file(filename,"w+")
        # resolve to current values
        clone.kernel = utils.find_kernel(clone.kernel)
        clone.initrd = utils.find_initrd(clone.initrd)

        # convert storage to something that's koan readable        
        clone.kernel_options = self.hash_to_string(clone.kernel_options)
        clone.ks_meta = self.hash_to_string(clone.ks_meta)

        self.tee(fd,yaml.dump(clone.to_datastruct()))
        self.close_file(fd)

    def write_profile_file(self,profile):
        """
        Create profile information for virt install

        NOTE: relevant to http only
        """

        clone = item_profile.Profile(self.config)
        clone.from_datastruct(profile.to_datastruct())


        filename = os.path.join(self.settings.webdir,"profiles",clone.name)
        distro = self.distros.find(clone.distro)
        if distro is not None:
            will_it_blend = (self.settings.kernel_options, distro.kernel_options, clone.kernel_options)
            clone.kernel_options = self.blend_options(True,will_it_blend)
        # yaml file: http only
        fd = self.open_file(filename,"w+")
        # if kickstart path is local, we've already copied it into
        # the HTTP mirror, so make it something anaconda can get at

        # NOTE: we only want to write this to the webdir, not the settings
        # file, so we must make a clone, outside of the collection.

        # convert storage to something that's koan readable                   
        clone.kernel_options = self.hash_to_string(clone.kernel_options)
        clone.ks_meta = self.hash_to_string(clone.ks_meta)

        # make URLs for koan if the kickstart files are locally managed (which is preferred)
        if clone.kickstart and clone.kickstart.startswith("/"):
            clone.kickstart = "http://%s/cblr/kickstarts/%s/ks.cfg" % (self.settings.server, clone.name)
        self.tee(fd,yaml.dump(clone.to_datastruct()))
        self.close_file(fd)


    def write_system_file(self,filename,system):
        """
        Create system information for virt install

        NOTE: relevant to http only
        """

        # no real reason to clone this yet, but in case changes come later, might as well be safe.
        clone = item_system.System(self.config)
        clone.from_datastruct(system.to_datastruct())
        # koan expects strings, not cobbler's storage format
        clone.kernel_options = self.hash_to_string(clone.kernel_options)
        clone.ks_meta = self.hash_to_string(clone.ks_meta)

        fd = self.open_file(filename,"w+")
        self.tee(fd,yaml.dump(clone.to_datastruct()))
        self.close_file(fd)

    def tee(self,fd,text):
        #if self.verbose:
        #    print text
        fd.write(text)

    def open_file(self,filename,mode):
        return open(filename,mode)

    def close_file(self,fd):
        fd.close()

    def copyfile(self,src,dst):
        if self.verbose:
            print "%s -> %s" % (src,dst)
        try:
            return shutil.copyfile(src,dst)
        except IOError, ioe:
            raise cexceptions.CobblerException("need_perms2",src,dst)

    def rmfile(self,path):
        try:
            os.unlink(path)
            return True
        except OSError, ioe:
            if not ioe.errno == errno.ENOENT: # doesn't exist
                traceback.print_exc()
                raise cexceptions.CobblerException("no_delete",path)
            return True

    def rmtree_contents(self,path):
       what_to_delete = glob.glob("%s/*" % path)
       for x in what_to_delete:
           self.rmtree(x)

    def rmtree(self,path):
       if self.verbose:
           print "del %s" % (path)
       try:
           if os.path.isfile(path):
               return self.rmfile(path)
           else:
               return shutil.rmtree(path,ignore_errors=True)
       except OSError, ioe:
           traceback.print_exc()
           if not ioe.errno == errno.ENOENT: # doesn't exist
               raise cexceptions.CobblerException("no_delete",path)
           return True

    def mkdir(self,path,mode=0777):
       if self.verbose:
           print "mkdir %s" % (path)
       try:
           return os.makedirs(path,mode)
       except OSError, oe:
           if not oe.errno == 17: # already exists (no constant for 17?)
               traceback.print_exc()
               print oe.errno
               raise cexceptions.CobblerException("no_create", path)

    def service(self, name, action):
        """
        Call /sbin/service NAME ACTION
        """

        cmd = "/sbin/service %s %s" % (name, action)
        if self.verbose:
            print cmd
        return sub_process.call(cmd, shell=True)

    def blend_options(self, is_for_kernel, list_of_opts):
        """
        Given a list of options, take the values used by the
        first argument in the list unless overridden by those in the
        second (or further on).
        """
        results = {}
        buffer = ""
        for optslist in list_of_opts:
           for key in optslist:
               results[key] = optslist[key]

        if is_for_kernel and self.settings.syslog_port != 0:
            results["syslog"] = "%s:%s" % (self.settings.server, self.settings.syslog_port)

        return results

    def hash_to_string(self, hash):
        buffer = ""
        for key in hash:
           value = hash[key]
           if value is None:
               buffer = buffer + str(key) + " "
           else:
               buffer = buffer + str(key) + "=" + str(value) + " "
        return buffer

