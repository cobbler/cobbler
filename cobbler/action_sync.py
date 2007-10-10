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
from cexceptions import *
import traceback
import errno

import item_distro
import item_profile
import item_system

from Cheetah.Template import Template

from rhpl.translate import _, N_, textdomain, utf8


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
        self.load_snippet_cache()

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.settings.tftpboot):
            raise CX(_("cannot find directory: %s") % self.settings.tftpboot)
        self.clean_trees()
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
                print _("Warning: %s restart failed") % service
        except OSError, e:
            print _("Warning: %s restart failed: ") % service, e

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
                    else:
                        systxt = "\nhost generic%d {\n" % counter

                    if distro.arch == "ia64":
                        # can't use pxelinux.0 anymore
                        systxt = systxt + "    filename \"/%s\";\n" % elilo
                        systxt = systxt + "    hardware ethernet %s;\n" % mac
                    if ip is not None and ip != "":
                        systxt = systxt + "    fixed-address %s;\n" % ip
                    # not needed, as it's in the template.
                    # systxt = systxt + "    next-server %s;\n" % self.settings.next_server
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

                if not system_definitions.has_key(interface["dhcp_tag"]):
                    system_definitions[interface["dhcp_tag"]] = ""
                system_definitions[interface["dhcp_tag"]] = system_definitions[interface["dhcp_tag"]] + systxt

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

        self.apply_template(template_data, metadata, settings_file)

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
                    self.rmfile(path)
            if os.path.isdir(path):
                if not x in ["webui", "localmirror","repo_mirror","ks_mirror","kickstarts","kickstarts_sys","distros","images","systems","profiles","links"] :
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
            print _("sync distro: %s") % d.name
            self.copy_single_distro_files(d)

    def copy_single_distro_files(self, d):
        for dirtree in [self.settings.tftpboot, self.settings.webdir]: 
            distros = os.path.join(dirtree, "images")
            distro_dir = os.path.join(distros,d.name)
            self.mkdir(distro_dir)
            kernel = utils.find_kernel(d.kernel) # full path
            initrd = utils.find_initrd(d.initrd) # full path
            if kernel is None or not os.path.isfile(kernel):
                raise CX(_("kernel not found: %(file)s, distro: %(distro)s") % { "file" : d.kernel, "distro" : d.name })
            if initrd is None or not os.path.isfile(initrd):
                raise CX(_("initrd not found: %(file)s, distro: %(distro)s") % { "file" : d.initrd, "distro" : d.name })
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
           print _("sync profile: %s") % g.name
           self.validate_kickstart_for_specific_profile(g)

    def validate_kickstart_for_specific_profile(self,g):
        distro = g.get_conceptual_parent()
        meta = utils.blender(False, g)
        if distro is None:
           raise CX(_("profile %(profile)s references missing distro %(distro)s") % { "profile" : g.name, "distro" : g.distro })
        kickstart_path = utils.find_kickstart(meta["kickstart"])
        if kickstart_path is not None and os.path.exists(kickstart_path):
           # the input is an *actual* file, hence we have to copy it
           copy_path = os.path.join(
               self.settings.webdir,
               "kickstarts", # profile kickstarts go here
               g.name
           )
           self.mkdir(copy_path)
           dest = os.path.join(copy_path, "ks.cfg")
           try:
                meta = utils.blender(False, g)
                ksmeta = meta["ks_meta"]
                del meta["ks_meta"]
                meta.update(ksmeta) # make available at top level
                meta["yum_repo_stanza"] = self.generate_repo_stanza(g)
                meta["yum_config_stanza"] = self.generate_config_stanza(g)
                meta["kickstart_done"] = self.generate_kickstart_signal(g, None)
                meta["kernel_options"] = utils.hash_to_string(meta["kernel_options"])
                kfile = open(kickstart_path)
                self.apply_template(kfile, meta, dest)
                kfile.close()
           except:
                traceback.print_exc() # leave this in, for now...
                msg = "err_kickstart2"
                raise CX(_("Error while rendering kickstart file %(src)s to %(dest)s") % { "src" : kickstart_path, "dest" : dest })

    def generate_kickstart_signal(self, profile, system=None):
        """
        Do things that we do at the end of kickstarts...
        * signal the status watcher we're done
        * disable PXE if needed
        * save the original kickstart file for debug
        """

        # FIXME: watcher is more of a request than a packaged file
        # we should eventually package something and let it do something important"
        pattern1 = "wget http://%s/cblr/watcher.py?%s_%s=%s -b"
        pattern2 = "wget http://%s/cgi-bin/cobbler/nopxe.cgi?system=%s -b"
        pattern3 = "wget http://%s/cobbler/%s/%s/ks.cfg -O /root/cobbler.ks"

        blend_this = profile
        if system:
            blend_this = system

        blended = utils.blender(False, blend_this)
        kickstart = blended.get("kickstart",None)

        buf = ""
        if system is not None:
            buf = buf + pattern1 % (self.settings.server, "system", "done", system.name)
            if str(self.settings.pxe_just_once).upper() in [ "1", "Y", "YES", "TRUE" ]:
                buf = buf + "\n" + pattern2 % (self.settings.server, system.name)
            if kickstart and os.path.exists(kickstart):
                buf = buf + "\n" + pattern3 % (self.settings.server, "kickstarts_sys", system.name)

        else:
            buf = buf + pattern1 % (self.settings.server, "profile", "done", profile.name)
            if kickstart and os.path.exists(kickstart):
                buf = buf + "\n" + pattern3 % (self.settings.server, "kickstarts", profile.name)
            
        return buf

    def generate_repo_stanza(self, profile):
        # returns the line of repo additions (Anaconda supports in FC-6 and later) that adds
        # the list of repos to things that Anaconda can install from.  This corresponds
        # will replace "TEMPLATE::yum_repo_stanza" in a cobbler kickstart file.
        buf = ""
        repos = utils.blender(False, profile)["repos"]
        for r in repos:
            repo = self.repos.find(name=r)
            if repo is None:
                continue
            http_url = "http://%s/cblr/repo_mirror/%s" % (self.settings.server, repo.name)
            buf = buf + "repo --name=%s --baseurl=%s\n" % (repo.name, http_url)
        distro = profile.get_conceptual_parent()

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
        repos = utils.blender(False,profile)["repos"]
        buf = ""
        for r in repos:
            repo = self.repos.find(name=r)
            if repo is None: 
                continue
            repo.local_filename = repo.local_filename.replace(".repo","")
            if not (repo.local_filename is None) and not (repo.local_filename == ""):
                buf = buf + "wget http://%s/cblr/repo_mirror/%s/config.repo --output-document=/etc/yum.repos.d/%s.repo\n" % (self.settings.server, repo.name, repo.local_filename)    

        # now install the core repos
        distro = profile.get_conceptual_parent()
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
            print _("sync system: %s") % s.name
            self.validate_kickstart_for_specific_system(s)

    def validate_kickstart_for_specific_system(self,s):
        profile = s.get_conceptual_parent()
        if profile is None:
            raise CX(_("system %(system)s references missing profile %(profile)s") % { "system" : s.name, "profile" : s.profile })
        distro = profile.get_conceptual_parent()
        meta = utils.blender(False, s)
        kickstart_path = utils.find_kickstart(meta["kickstart"])
        if kickstart_path and os.path.exists(kickstart_path):
            copy_path = os.path.join(self.settings.webdir,
                "kickstarts_sys", # system kickstarts go here
                s.name
            )
            self.mkdir(copy_path)
            dest = os.path.join(copy_path, "ks.cfg")
            try:
                ksmeta = meta["ks_meta"]
                del meta["ks_meta"]
                meta.update(ksmeta) # make available at top level
                meta["yum_repo_stanza"] = self.generate_repo_stanza(profile)
                meta["yum_config_stanza"] = self.generate_config_stanza(profile)
                meta["kickstart_done"]  = self.generate_kickstart_signal(profile, s)
                meta["kernel_options"] = utils.hash_to_string(meta["kernel_options"])
                kfile = open(kickstart_path)
                self.apply_template(kfile, meta, dest)
                kfile.close()
            except:
                raise CX(_("Error templating file %(src)s to %(dest)s") % { "src" : meta["kickstart"], "dest" : dest })

    def load_snippet_cache(self):

        # first load all of the files in /var/lib/cobbler/snippets and load them, for use
        # in adding long bits to kickstart templates without having to have them hard coded
        # inside the sync code.

        snippet_cache = {} 
        snippets = glob.glob("%s/*" % self.settings.snippetsdir)
        for snip in snippets:
           if os.path.isdir(snip):
               continue
           snip_file = open(snip)
           data = snip_file.read()
           snip_file.close()
           snippet_cache[os.path.basename(snip)] = data
        self.snippet_cache = snippet_cache


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

        # replace contents of the data stream with items from the snippet cache
        # do not use Cheetah yet, Cheetah can't really be run twice on the same
        # stream and be expected to do the right thing
        newdata = ""
        for line in data.split("\n"):
            for x in self.snippet_cache:
                if not line.startswith("#"):
                    line = line.replace("SNIPPET::%s" % x, self.snippet_cache[x])
            newdata = "\n".join((newdata, line))
        data = newdata

        # HACK:  the ksmeta field may contain nfs://server:/mount in which
        # case this is likely WRONG for kickstart, which needs the NFS
        # directive instead.  Do this to make the templates work.
        newdata = ""
        if metadata.has_key("tree") and metadata["tree"].startswith("nfs://"): 
            for line in data.split("\n"):
               if line.find("--url") != -1 and line.find("url ") != -1:
                   rest = metadata["tree"][6:] # strip off "nfs://" part
                   (server, dir) = rest.split(":",2)
                   line = "nfs --server %s --dir %s" % (server,dir)
                   # but put the URL part back in so koan can still see
                   # what the original value was
                   line = line + "\n" + "#url --url=%s" % metadata["tree"]
               newdata = newdata + line + "\n"
            data = newdata 

        # tell Cheetah not to blow up if it can't find a symbol for something
        data = "#errorCatcher Echo\n" + data

        # now do full templating scan, where we will also templatify the snippet insertions
        t = Template(source=data, searchList=[metadata])
        try:
            data_out = str(t)
        except:
            print _("There appears to be an formatting error in the template file.")
            print _("For completeness, the traceback from Cheetah has been included below.")
            raise

        # now apply some magic post-filtering that is used by cobbler import and some
        # other places, but doesn't use Cheetah.  Forcing folks to double escape
        # things would be very unwelcome.

        for x in metadata:
           if type(metadata[x]) == str:
               data_out = data_out.replace("@@%s@@" % x, metadata[x])

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
                f2 = os.path.join(self.settings.tftpboot, "pxelinux.cfg", f1)
            if distro.arch == "ia64":
                # elilo expects files to be named "$name.conf" in the root
                # and can not do files based on the MAC address
                if ip is not None and ip != "":
                    print _("Warning: Itanium system object (%s) needs an IP address to PXE") % system.name

                filename = "%s.conf" % utils.get_config_filename(system,interface=name)
                f2 = os.path.join(self.settings.tftpboot, filename)

            f3 = os.path.join(self.settings.webdir, "systems", f1)

            if system.netboot_enabled and system.is_pxe_supported():
                if distro.arch in [ "x86", "x86_64", "standard"]:
                    self.write_pxe_file(f2,system,profile,distro,False)
                if distro.arch == "ia64":
                    self.write_pxe_file(f2,system,profile,distro,True)
            else:
                # ensure the file doesn't exist
                self.rmfile(f2)

            self.write_system_file(f3,system)

        counter = counter + 1
        

    def make_pxe_menu(self):
        # only do this if there is NOT a system named default.
        default = self.systems.find(name="default")
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
            distro = profile.get_conceptual_parent()
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
            kopts = utils.blender(True,system)["kernel_options"]
        else:
            kopts = utils.blender(True,profile)["kernel_options"]

        # ---
        # generate the append line
        append_line = "append %s" % utils.hash_to_string(kopts)
        if not is_ia64:
            append_line = "%s initrd=%s" % (append_line, initrd_path)
        if len(append_line) >= 255 + len("append "):
            print _("warning: kernel option length exceeds 255")

        # ---
        # kickstart path rewriting (get URLs for local files)
        if kickstart_path is not None and kickstart_path != "":

            if system is not None and kickstart_path.startswith("/"):
                kickstart_path = "http://%s/cblr/kickstarts_sys/%s/ks.cfg" % (self.settings.server, system.name)
            elif kickstart_path.startswith("/") or kickstart_path.find("/cobbler/kickstarts/") != -1:
                kickstart_path = "http://%s/cblr/kickstarts/%s/ks.cfg" % (self.settings.server, profile.name)

            if distro.breed is None or distro.breed == "redhat":
                append_line = "%s ks=%s" % (append_line, kickstart_path)
            elif distro.breed == "suse":
                append_line = "%s autoyast=%s" % (append_line, kickstart_path)
            elif distro.breed == "debian":
                append_line = "%s auto=true url=%s" % (append_line, kickstart_path)
                append_line = append_line.replace("ksdevice","interface")

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
            fd = open(filename, "w")
            fd.write(buffer)
            fd.close()
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
        fd1 = open(os.path.join(self.settings.webdir, "profile_list"), "w+")
        fd2 = open(os.path.join(self.settings.webdir, "system_list"), "w+")
        fd1.write(data1)
        fd2.write(data2)
        fd1.close()
        fd2.close()

    def write_distro_file(self,distro):
        """
        Create distro information for koan install
        """
        blended = utils.blender(True, distro)
        filename = os.path.join(self.settings.webdir,"distros",distro.name)
        fd = open(filename, "w+")
        fd.write(yaml.dump(blended))
        fd.close() 

    def write_profile_file(self,profile):
        """
        Create profile information for virt install

        NOTE: relevant to http only
        """

        blended = utils.blender(True, profile)
        filename = os.path.join(self.settings.webdir,"profiles",profile.name)
        fd = open(filename, "w+")
        if blended.has_key("kickstart") and blended["kickstart"].startswith("/"):
            # write the file location as needed by koan
            blended["kickstart"] = "http://%s/cblr/kickstarts/%s/ks.cfg" % (self.settings.server, profile.name)
        fd.write(yaml.dump(blended))
        fd.close()

    def write_system_file(self,filename,system):
        """
        Create system information for virt install

        NOTE: relevant to http only
        """

        blended = utils.blender(True, system)
        filename = os.path.join(self.settings.webdir,"systems",system.name)
        fd = open(filename, "w+")
        fd.write(yaml.dump(blended))
        fd.close()

    def copyfile(self,src,dst):
        try:
            return shutil.copyfile(src,dst)
        except IOError, ioe:
            raise CX(_("Error copying %(src)s to %(dst)s") % { "src" : src, "dst" : dst})

    def rmfile(self,path):
        try:
            os.unlink(path)
            return True
        except OSError, ioe:
            if not ioe.errno == errno.ENOENT: # doesn't exist
                traceback.print_exc()
                raise CX(_("Error deleting %s") % path)
            return True

    def rmtree_contents(self,path):
       what_to_delete = glob.glob("%s/*" % path)
       for x in what_to_delete:
           self.rmtree(x)

    def rmtree(self,path):
       try:
           if os.path.isfile(path):
               return self.rmfile(path)
           else:
               return shutil.rmtree(path,ignore_errors=True)
       except OSError, ioe:
           traceback.print_exc()
           if not ioe.errno == errno.ENOENT: # doesn't exist
               raise CX(_("Error deleting %s") % path)
           return True

    def mkdir(self,path,mode=0777):
       try:
           return os.makedirs(path,mode)
       except OSError, oe:
           if not oe.errno == 17: # already exists (no constant for 17?)
               traceback.print_exc()
               print oe.errno
               raise CX(_("Error creating") % path)

    def service(self, name, action):
        """
        Call /sbin/service NAME ACTION
        """

        cmd = "/sbin/service %s %s" % (name, action)
        return sub_process.call(cmd, shell=True)

