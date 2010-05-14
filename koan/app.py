"""
koan = kickstart over a network

a tool for network provisioning of virtualization (xen,kvm/qemu,vmware)
and network re-provisioning of existing Linux systems.  
used with 'cobbler'. see manpage for usage.

Copyright 2006-2008 Red Hat, Inc.
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

import random
import os
import traceback
import tempfile

ANCIENT_PYTHON = 0
try:
    try:
        from optparse import OptionParser
    except:
        from opt_parse import OptionParser # importing this for backwards compat with 2.2
    try:
        import subprocess as sub_process
    except:
        import sub_process
except:
    # the main "replace-self" codepath of koan must support
    # Python 1.5.  Other sections may use 2.3 features (nothing newer)
    # provided they are conditionally imported.  This is to support
    # EL 2.1. -- mpd
    ANCIENT_PYTHON = 1
    True = 1
    False = 0

import exceptions
import time
import shutil
import errno
import re
import sys
import xmlrpclib
import string
import re
import glob
import socket
import utils
import time

COBBLER_REQUIRED = 1.300

"""
koan --virt [--profile=webserver|--system=name] --server=hostname
koan --replace-self --profile=foo --server=hostname [--kexec]
"""

DISPLAY_PARAMS = [
   "name",
   "distro","profile",
   "kickstart","ks_meta",
   "install_tree","kernel","initrd",
   "kernel_options",
   "repos",
   "virt_ram","virt_disk","virt_type", "virt_path", "virt_auto_boot"
]




def main():
    """
    Command line stuff...
    """

    try:
        utils.setupLogging("koan")
    except:
        # most likely running RHEL3, where we don't need virt logging anyway
        pass

    if ANCIENT_PYTHON:
        print "- command line usage on this version of python is unsupported"
        print "- usage via spacewalk APIs only.  Python x>=2.3 required"
        return

    p = OptionParser()
    p.add_option("-k", "--kopts",
                 dest="kopts_override",
                 help="append additional kernel options")
    p.add_option("-l", "--list",
                 dest="list_items",
                 help="lists remote items (EX: profiles, systems, or images)")
    p.add_option("-v", "--virt",
                 dest="is_virt",
                 action="store_true",
                 help="install new virtual guest")
    p.add_option("-u", "--update-files",
                 dest="is_update_files",
                 action="store_true",
                 help="update templated files from cobbler config management")
    p.add_option("-V", "--virt-name",
                 dest="virt_name",
                 help="use this name for the virtual guest")
    p.add_option("-r", "--replace-self",
                 dest="is_replace",
                 action="store_true",
                 help="reinstall this host at next reboot")
    p.add_option("-D", "--display",
                 dest="is_display",
                 action="store_true",
                 help="display the configuration stored in cobbler for the given object")
    p.add_option("-p", "--profile",
                 dest="profile",
                 help="use this cobbler profile")
    p.add_option("-y", "--system",
                 dest="system",
                 help="use this cobbler system")
    p.add_option("-i", "--image",
                 dest="image",
                 help="use this cobbler image")
    p.add_option("-s", "--server",
                 dest="server",
                 default=os.environ.get("COBBLER_SERVER",""),
                 help="attach to this cobbler server")
    p.add_option("-S", "--static-interface",
                 dest="static_interface",
                 help="use static network configuration from this interface while installing")
    p.add_option("-t", "--port",
                 dest="port",
                 help="cobbler xmlrpc port (default 25151)")
    p.add_option("-w", "--vm-poll",
                 dest="should_poll",
                 action="store_true",
                 help="for xen/qemu/KVM, poll & restart the VM after the install is done")
    p.add_option("-P", "--virt-path",
                 dest="virt_path",
                 help="override virt install location")  
    p.add_option("-T", "--virt-type",
                 dest="virt_type",
                 help="override virt install type")
    p.add_option("-B", "--virt-bridge",
                 dest="virt_bridge",
                 help="override virt bridge")
    p.add_option("-n", "--nogfx",
                 action="store_true", 
                 dest="no_gfx",
                 help="disable Xen graphics (xenpv,xenfv)")
    p.add_option("", "--virt-auto-boot",
                 action="store_true", 
                 dest="virt_auto_boot",
                 help="set VM for autoboot")
    p.add_option("", "--add-reinstall-entry",
                 dest="add_reinstall_entry",
                 action="store_true",
                 help="when used with --replace-self, just add entry to grub, do not make it the default")
    p.add_option("-C", "--livecd",
                 dest="live_cd",
                 action="store_true",
                 help="used by the custom livecd only, not for humans")
    p.add_option("", "--kexec",
                 dest="use_kexec",
                 action="store_true",
                 help="Instead of writing a new bootloader config when using --replace_self, just kexec the new kernel and initrd")
    p.add_option("", "--embed",
                 dest="embed_kickstart",
                 action="store_true",
                 help="When used with  --replace-self, embed the kickstart in the initrd to overcome potential DHCP timeout issues. (seldom needed)")
    p.add_option("", "--qemu-disk-type",
                 dest="qemu_disk_type",
                 help="when used with --virt_type=qemu, add select of disk drivers: ide,scsi,virtio")

    (options, args) = p.parse_args()


    try:
        k = Koan()
        k.list_items          = options.list_items
        k.server              = options.server
        k.is_virt             = options.is_virt
        k.is_update_files     = options.is_update_files
        k.is_replace          = options.is_replace
        k.is_display          = options.is_display
        k.profile             = options.profile
        k.system              = options.system
        k.image               = options.image
        k.live_cd             = options.live_cd
        k.virt_path           = options.virt_path
        k.virt_type           = options.virt_type
        k.virt_bridge         = options.virt_bridge
        k.no_gfx              = options.no_gfx
        k.add_reinstall_entry = options.add_reinstall_entry
        k.kopts_override      = options.kopts_override
        k.static_interface    = options.static_interface
        k.use_kexec           = options.use_kexec
        k.should_poll         = options.should_poll
        k.embed_kickstart     = options.embed_kickstart
        k.virt_auto_boot      = options.virt_auto_boot
        k.qemu_disk_type      = options.qemu_disk_type

        if options.virt_name is not None:
            k.virt_name          = options.virt_name
        if options.port is not None:
            k.port              = options.port
        k.run()

    except Exception, e:
        (xa, xb, tb) = sys.exc_info()
        try:
            getattr(e,"from_koan")
            print str(e)[1:-1] # nice exception, no traceback needed
        except:
            print xa
            print xb
            print string.join(traceback.format_list(traceback.extract_tb(tb)))
        return 1

    return 0

#=======================================================

class InfoException(exceptions.Exception):
    """
    Custom exception for tracking of fatal errors.
    """
    def __init__(self,value,**args):
        self.value = value % args
        self.from_koan = 1
    def __str__(self):
        return repr(self.value)

#=======================================================

class Koan:

    def __init__(self):
        """
        Constructor.  Arguments will be filled in by optparse...
        """
        self.server            = None
        self.system            = None
        self.profile           = None
        self.list_profiles     = None
        self.list_systems      = None
        self.is_virt           = None
        self.is_update_files   = None
        self.is_replace        = None
        self.port              = None
        self.static_interface  = None
        self.virt_name         = None
        self.virt_type         = None
        self.virt_path         = None
        self.qemu_disk_type    = None
        self.virt_auto_boot    = None

    #---------------------------------------------------

    def run(self):
        """
        koan's main function...
        """
        
        # we can get the info we need from either the cobbler server
        #  or a kickstart file
        if self.server is None:
            raise InfoException, "no server specified"

        # check to see that exclusive arguments weren't used together
        found = 0
        for x in (self.is_virt, self.is_replace, self.is_update_files, self.is_display, self.list_items):
            if x:
               found = found+1
        if found != 1:
            raise InfoException, "choose: --virt, --replace-self, --update-files, --list=what, or --display"
 

        # This set of options are only valid with --server
        if not self.server or self.server == "":
            if self.list_items or self.profile or self.system or self.port:
                raise InfoException, "--server is required"

        self.xmlrpc_server = utils.connect_to_server(server=self.server, port=self.port)

        if self.list_items:
            self.list(self.list_items)
            return
    
        if not os.getuid() == 0:
            if self.is_virt:
                print "warning: running as non root"
            else:
                print "this operation requires root access"
                return 3
        
        # if both --profile and --system were ommitted, autodiscover
        if self.is_virt:
            if (self.profile is None and self.system is None and self.image is None):
                raise InfoException, "must specify --profile, --system, or --image"
        else:
            if (self.profile is None and self.system is None and self.image is None):
                self.system = self.autodetect_system(allow_interactive=self.live_cd)
                if self.system is None:
                   while self.profile is None:
                      self.profile = self.ask_profile()


        # if --virt-type was specified and invalid, then fail
        if self.virt_type is not None:
            self.virt_type = self.virt_type.lower()
            if self.virt_type not in [ "qemu", "xenpv", "xenfv", "xen", "vmware", "vmwarew", "auto" ]:
               if self.virt_type == "xen":
                   self.virt_type = "xenpv"
               raise InfoException, "--virt-type should be qemu, xenpv, xenfv, vmware, vmwarew, or auto"

        # if --qemu-disk-type was called without --virt-type=qemu, then fail
        if (self.qemu_disk_type is not None):
            self.qemu_disk_type = self.qemu_disk_type.lower()
            if self.virt_type not in [ "qemu", "auto" ]:
               raise InfoException, "--qemu-disk-type must use with --virt-type=qemu"



        # if --static-interface and --profile was called together, then fail
        if self.static_interface is not None and self.profile is not None:
            raise InfoException, "--static-interface option is incompatible with --profile option use --system instead"

        # perform one of three key operations
        if self.is_virt:
            self.virt()
        elif self.is_replace:
            if self.use_kexec:
                self.kexec_replace()
            else:
                self.replace()
        elif self.is_update_files:
            self.update_files()
        else:
            self.display()

    # --------------------------------------------------   

    def ask_profile(self):
        """
        Used by the live CD mode, if the system can not be auto-discovered, show a list of available
        profiles and ask the user what they want to install.  
        """
        # FIXME: use a TUI library to make this more presentable.
        try:
            available_profiles = self.xmlrpc_server.get_profiles()
        except:
            traceback.print_exc()
            self.connect_fail()

        print "\n- which profile to install?\n"
      
        for x in available_profiles:
            print "%s" % x["name"]

        sys.stdout.write("\n?>")

        data = sys.stdin.readline().strip()
 
        for x in available_profiles:
            print "comp (%s,%s)" % (x["name"],data)
            if x["name"] == data:
                return data
        return None

    #---------------------------------------------------

    def autodetect_system(self, allow_interactive=False):
        """
        Determine the name of the cobbler system record that
        matches this MAC address. 
        """
        try:
            import rhpl
        except:
            raise CX("the rhpl module is required to autodetect a system.  Your OS does not have this, please manually specify --profile or --system")
        systems = self.get_data("systems")
        my_netinfo = utils.get_network_info()
        my_interfaces = my_netinfo.keys()
        mac_criteria = []
        ip_criteria = []
        for my_interface in my_interfaces:
            mac_criteria.append(my_netinfo[my_interface]["mac_address"].upper())
            ip_criteria.append(my_netinfo[my_interface]["ip_address"])

        detected_systems = []
        systems = self.get_data("systems")
        for system in systems:
            obj_name = system["name"]
            for (obj_iname, obj_interface) in system['interfaces'].iteritems():
                mac = obj_interface["mac_address"].upper()
                ip  = obj_interface["ip_address"].upper()
                for my_mac in mac_criteria:
                    if mac == my_mac:
                        detected_systems.append(obj_name)
                for my_ip in ip_criteria:
                    if ip == my_ip:
                        detected_systems.append(obj_name)

        detected_systems = utils.uniqify(detected_systems)

        if len(detected_systems) > 1:
            raise InfoException, "Error: Multiple systems matched"
        elif len(detected_systems) == 0:
            if not allow_interactive:
                mac_criteria = utils.uniqify(mac_criteria, purge="?")
                ip_criteria  = utils.uniqify(ip_criteria, purge="?")
                raise InfoException, "Error: Could not find a matching system with MACs: %s or IPs: %s" % (",".join(mac_criteria), ",".join(ip_criteria))
            else:
                return None
        elif len(detected_systems) == 1:
            print "- Auto detected: %s" % detected_systems[0]
            return detected_systems[0]

    #---------------------------------------------------

    def safe_load(self,hashv,primary_key,alternate_key=None,default=None):
        if hashv.has_key(primary_key): 
            return hashv[primary_key]
        elif alternate_key is not None and hashv.has_key(alternate_key):
            return hashv[alternate_key]
        else:
            return default

    #---------------------------------------------------

    def net_install(self,after_download):
        """
        Actually kicks off downloads and auto-ks or virt installs
        """

        # initialise the profile, from the server if any
        if self.profile:
            profile_data = self.get_data("profile",self.profile)
        elif self.system:
            profile_data = self.get_data("system",self.system)
        elif self.image:
            profile_data = self.get_data("image",self.image)
        else:
            # shouldn't end up here, right?
            profile_data = {}

        if profile_data.get("kickstart","") != "":

            # fix URLs
            if profile_data["kickstart"][0] == "/" or profile_data["template_remote_kickstarts"]:
               if not self.system:
                   profile_data["kickstart"] = "http://%s/cblr/svc/op/ks/profile/%s" % (profile_data['http_server'], profile_data['name'])
               else:
                   profile_data["kickstart"] = "http://%s/cblr/svc/op/ks/system/%s" % (profile_data['http_server'], profile_data['name'])
                
            # find_kickstart source tree in the kickstart file
            self.get_install_tree_from_kickstart(profile_data)

            # if we found an install_tree, and we don't have a kernel or initrd
            # use the ones in the install_tree
            if self.safe_load(profile_data,"install_tree"):
                if not self.safe_load(profile_data,"kernel"):
                    profile_data["kernel"] = profile_data["install_tree"] + "/images/pxeboot/vmlinuz"

                if not self.safe_load(profile_data,"initrd"):
                    profile_data["initrd"] = profile_data["install_tree"] + "/images/pxeboot/initrd.img"


        # find the correct file download location 
        if not self.is_virt:
            if os.path.exists("/boot/efi/EFI/redhat/elilo.conf"):
                # elilo itanium support, may actually still work
                download = "/boot/efi/EFI/redhat"
            else:
                # whew, we have a sane bootloader
                download = "/boot"

        else:
            # ensure we have a good virt type choice and know where
            # to download the kernel/initrd
            if self.virt_type is None:
                self.virt_type = self.safe_load(profile_data,'virt_type',default=None)
            if self.virt_type is None or self.virt_type == "":
                self.virt_type = "auto"

            # if virt type is auto, reset it to a value we can actually use
            if self.virt_type == "auto":

                if profile_data.get("xml_file","") != "":
                    raise InfoException("xmlfile based installations are not supported")

                elif profile_data.has_key("file"):
                    print "- ISO or Image based installation, always uses --virt-type=qemu"
                    self.virt_type = "qemu"
                    
                else:
                    # FIXME: auto never selects vmware, maybe it should if we find it?

                    if not ANCIENT_PYTHON:
                        cmd = sub_process.Popen("/bin/uname -r", stdout=sub_process.PIPE, shell=True)
                        uname_str = cmd.communicate()[0]
                        if uname_str.find("xen") != -1:
                            self.virt_type = "xenpv"
                        elif os.path.exists("/usr/bin/qemu-img"):
                            self.virt_type = "qemu"
                        else:
                            # assume Xen, we'll check to see if virt-type is really usable later.
                            raise InfoException, "Not running a Xen kernel and qemu is not installed"

                print "- no virt-type specified, auto-selecting %s" % self.virt_type

            # now that we've figured out our virt-type, let's see if it is really usable
            # rather than showing obscure error messages from Xen to the user :)

            if self.virt_type in [ "xenpv", "xenfv" ]:
                cmd = sub_process.Popen("uname -r", stdout=sub_process.PIPE, shell=True)
                uname_str = cmd.communicate()[0]
                # correct kernel on dom0?
                if uname_str.find("xen") == -1:
                   raise InfoException("kernel-xen needs to be in use")
                # xend installed?
                if not os.path.exists("/usr/sbin/xend"):
                   raise InfoException("xen package needs to be installed")
                # xend running?
                rc = sub_process.call("/usr/sbin/xend status", stderr=None, stdout=None, shell=True)
                if rc != 0:
                   raise InfoException("xend needs to be started")

            # for qemu
            if self.virt_type == "qemu":
                # qemu package installed?
                if not os.path.exists("/usr/bin/qemu-img"):
                    raise InfoException("qemu package needs to be installed")
                # is libvirt new enough?
                cmd = sub_process.Popen("rpm -q python-virtinst", stdout=sub_process.PIPE, shell=True)
                version_str = cmd.communicate()[0]
                if version_str.find("virtinst-0.1") != -1 or version_str.find("virtinst-0.0") != -1:
                    raise InfoException("need python-virtinst >= 0.2 to do installs for qemu/kvm")

            # for vmware
            if self.virt_type == "vmware" or self.virt_type == "vmwarew":
                # FIXME: if any vmware specific checks are required (for deps) do them here.
                pass

            if self.virt_type == "virt-image":
                if not os.path.exists("/usr/bin/virt-image"):
                    raise InfoException("virt-image not present, downlevel virt-install package?")

            # for both virt types
            if os.path.exists("/etc/rc.d/init.d/libvirtd"):
                rc = sub_process.call("/sbin/service libvirtd status", stdout=None, shell=True)
                if rc != 0:
                    # libvirt running?
                    raise InfoException("libvirtd needs to be running")


            if self.virt_type in [ "xenpv" ]:
                # we need to fetch the kernel/initrd to do this
                download = "/var/lib/xen" 
            elif self.virt_type in [ "xenfv", "vmware", "vmwarew" ] :
                # we are downloading sufficient metadata to initiate PXE, no D/L needed
                download = None 
            else: # qemu
                # fullvirt, can use set_location in virtinst library, no D/L needed yet
                download = None 

        # download required files
        if not self.is_display and download is not None:
           self.get_distro_files(profile_data, download)
  
        # perform specified action
        after_download(self, profile_data)

    #---------------------------------------------------

    def get_install_tree_from_kickstart(self,profile_data):
        """
        Scan the kickstart configuration for either a "url" or "nfs" command
           take the install_tree url from that

        """
        try:
            raw = utils.urlread(profile_data["kickstart"])
            lines = raw.splitlines()

            method_re = re.compile('(?P<urlcmd>\s*url\s.*)|(?P<nfscmd>\s*nfs\s.*)')

            url_parser = OptionParser()
            url_parser.add_option("--url", dest="url")

            nfs_parser = OptionParser()
            nfs_parser.add_option("--dir", dest="dir")
            nfs_parser.add_option("--server", dest="server")

            for line in lines:
                match = method_re.match(line)
                if match:
                    cmd = match.group("urlcmd")
                    if cmd:
                        (options,args) = url_parser.parse_args(cmd.split()[1:])
                        profile_data["install_tree"] = options.url
                        break
                    cmd = match.group("nfscmd")
                    if cmd:
                        (options,args) = nfs_parser.parse_args(cmd.split()[1:])
                        profile_data["install_tree"] = "nfs://%s:%s" % (options.server,options.dir)
                        break

            if self.safe_load(profile_data,"install_tree"):
                print "install_tree:", profile_data["install_tree"]
            else:
                print "warning: kickstart found but no install_tree found"
                        
        except:
            # unstable to download the kickstart, however this might not
            # be an error.  For instance, xen FV installations of non
            # kickstart OS's...
            pass

    #---------------------------------------------------

    def list(self,what):
        if what not in [ "images", "profiles", "systems", "distros", "repos" ]:
            raise InfoException("koan does not know how to list that")
        data = self.get_data(what)
        for x in data:
            if x.has_key("name"):
                print x["name"]
        return True

    #---------------------------------------------------

    def display(self):
        def after_download(self, profile_data):
            for x in DISPLAY_PARAMS:
                if profile_data.has_key(x):
                    value = profile_data[x]
                    if x == 'kernel_options':
                        value = self.calc_kernel_args(profile_data)
                    print "%20s  : %s" % (x, value)
        return self.net_install(after_download)

    #---------------------------------------------------
                 
    def virt(self):
        """
        Handle virt provisioning.
        """

        def after_download(self, profile_data):
            self.virt_net_install(profile_data)

        return self.net_install(after_download)

    #---------------------------------------------------

    def update_files(self):
        """
        Contact the cobbler server and wget any config-management
        files in cobbler that we are providing to nodes.  Basically
        this turns cobbler into a lighweight configuration management
        system for folks who are not needing a more complex CMS.
        
        Read more at:
        https://fedorahosted.org/cobbler/wiki/BuiltinConfigManagement
        """

        # FIXME: make this a utils.py function
        if self.profile:
            profile_data = self.get_data("profile",self.profile)
        elif self.system:
            profile_data = self.get_data("system",self.system)
        elif self.image:
            profile_data = self.get_data("image",self.image)
        else:
            # shouldn't end up here, right?
            profile_data = {}

        # BOOKMARK
        template_files = profile_data["template_files"]
        template_files = utils.input_string_or_hash(template_files)
        template_keys  = template_files.keys()

        print "- template map: %s" % template_files

        print "- processing for files to download..."
        for src in template_keys: 
            dest = template_files[src]
            save_as = dest
            dest = dest.replace("_","__")
            dest = dest.replace("/","_")
            if not save_as.startswith("/"):
                # this is a file in the template system that is not to be downloaded
                continue
            print "- file: %s" % save_as

            pattern = "http://%s/cblr/svc/op/template/%s/%s/path/%s"
            if profile_data.has_key("interfaces"):
                url = pattern % (profile_data["http_server"],"system",profile_data["name"],dest)
            else:
                url = pattern % (profile_data["http_server"],"profile",profile_data["name"],dest)
            if not os.path.exists(os.path.dirname(save_as)):
                os.makedirs(os.path.dirname(save_as))
            cmd = [ "/usr/bin/wget", url, "--output-document", save_as ]
            utils.subprocess_call(cmd)
       
        return True 

    #---------------------------------------------------
  
    def kexec_replace(self):
        """
        Prepare to morph existing system by downloading new kernel and initrd
        and preparing kexec to execute them. Allow caller to do final 'kexec
        -e' invocation; this allows modules such as network drivers to be
        unloaded (for cases where an immediate kexec would leave the driver in
        an invalid state.
        """
        def after_download(self, profile_data):
            k_args = self.calc_kernel_args(profile_data)
            kickstart = self.safe_load(profile_data,'kickstart')
            arch      = self.safe_load(profile_data,'arch')

            (make, version, rest) = utils.os_release()

            if (make == "centos" and version < 6) or (make == "redhat" and version < 6) or (make == "fedora" and version < 10):

                # embed the initrd in the kickstart file because of libdhcp and/or pump
                # needing the help due to some DHCP timeout potential in some certain
                # network configs.

                if self.embed_kickstart:
                    self.build_initrd(
                        self.safe_load(profile_data,'initrd_local'),
                        kickstart,
                        profile_data
                    )

            # Validate kernel argument length (limit depends on architecture --
            # see asm-*/setup.h).  For example:
            #   asm-i386/setup.h:#define COMMAND_LINE_SIZE 256
            #   asm-ia64/setup.h:#define COMMAND_LINE_SIZE  512
            #   asm-powerpc/setup.h:#define COMMAND_LINE_SIZE   512
            #   asm-s390/setup.h:#define COMMAND_LINE_SIZE  896
            #   asm-x86_64/setup.h:#define COMMAND_LINE_SIZE    256
            if arch.startswith("ppc") or arch.startswith("ia64"):
                if len(k_args) > 511:
                    raise InfoException, "Kernel options are too long, 512 chars exceeded: %s" % k_args
            elif arch.startswith("s390"):
                if len(k_args) > 895:
                    raise InfoException, "Kernel options are too long, 896 chars exceeded: %s" % k_args
            elif len(k_args) > 255:
                raise InfoException, "Kernel options are too long, 255 chars exceeded: %s" % k_args

            utils.subprocess_call([
                'kexec',
                '--load',
                '--initrd=%s' % (self.safe_load(profile_data,'initrd_local'),),
                '--command-line=%s' % (k_args,),
                self.safe_load(profile_data,'kernel_local')
            ])
            print "Kernel loaded; run 'kexec -e' to execute"
        return self.net_install(after_download)


    #---------------------------------------------------
        
    def get_boot_loader_info(self):
        if ANCIENT_PYTHON:
            # FIXME: implement this to work w/o subprocess
            if os.path.exists("/etc/grub.conf"):
               return (0, "grub")
            else:
               return (0, "lilo") 
        cmd = [ "/sbin/grubby", "--bootloader-probe" ]
        probe_process = sub_process.Popen(cmd, stdout=sub_process.PIPE)
        which_loader = probe_process.communicate()[0]
        return probe_process.returncode, which_loader

    def replace(self):
        """
        Handle morphing an existing system through downloading new
        kernel, new initrd, and installing a kickstart in the initrd,
        then manipulating grub.
        """
        try:
            shutil.rmtree("/var/spool/koan")
        except OSError, (err, msg):
            if err != errno.ENOENT:
                raise
        try:
            os.makedirs("/var/spool/koan")
        except OSError, (err, msg):
            if err != errno.EEXIST:
                raise
    

        def after_download(self, profile_data):
            if not os.path.exists("/sbin/grubby"):
                raise InfoException, "grubby is not installed"
            k_args = self.calc_kernel_args(profile_data,replace_self=1)

            kickstart = self.safe_load(profile_data,'kickstart')

            (make, version, rest) = utils.os_release()

            if (make == "centos" and version < 6) or (make == "redhat" and version < 6) or (make == "fedora" and version < 10):

                # embed the initrd in the kickstart file because of libdhcp and/or pump
                # needing the help due to some DHCP timeout potential in some certain
                # network configs.

                if self.embed_kickstart:
                    self.build_initrd(
                        self.safe_load(profile_data,'initrd_local'),
                        kickstart,
                        profile_data
                    )

            if not ANCIENT_PYTHON:
                arch_cmd = sub_process.Popen("/bin/uname -m", stdout=sub_process.PIPE, shell=True)
                arch = arch_cmd.communicate()[0]
            else:
                arch = "i386"

            # Validate kernel argument length (limit depends on architecture --
            # see asm-*/setup.h).  For example:
            #   asm-i386/setup.h:#define COMMAND_LINE_SIZE 256
            #   asm-ia64/setup.h:#define COMMAND_LINE_SIZE  512
            #   asm-powerpc/setup.h:#define COMMAND_LINE_SIZE   512
            #   asm-s390/setup.h:#define COMMAND_LINE_SIZE  896
            #   asm-x86_64/setup.h:#define COMMAND_LINE_SIZE    256
            if not ANCIENT_PYTHON:
                if arch.startswith("ppc") or arch.startswith("ia64"):
                    if len(k_args) > 511:
                        raise InfoException, "Kernel options are too long, 512 chars exceeded: %s" % k_args
                elif arch.startswith("s390"):
                    if len(k_args) > 895:
                        raise InfoException, "Kernel options are too long, 896 chars exceeded: %s" % k_args
                elif len(k_args) > 255:
                    raise InfoException, "Kernel options are too long, 255 chars exceeded: %s" % k_args

            cmd = [ "/sbin/grubby",
                    "--add-kernel", self.safe_load(profile_data,'kernel_local'),
                    "--initrd", self.safe_load(profile_data,'initrd_local'),
                    "--args", "\"%s\"" % k_args,
                    "--copy-default"
            ]
            boot_probe_ret_code, probe_output = self.get_boot_loader_info()
            if boot_probe_ret_code == 0 and string.find(probe_output, "lilo") >= 0:
                cmd.append("--lilo")

            if self.add_reinstall_entry:
               cmd.append("--title=Reinstall")
            else:
               cmd.append("--make-default")
               cmd.append("--title=kick%s" % int(time.time()))
               
            if self.live_cd:
               cmd.append("--bad-image-okay")
               cmd.append("--boot-filesystem=/")
               cmd.append("--config-file=/tmp/boot/boot/grub/grub.conf")

            # Are we running on ppc?
            if not ANCIENT_PYTHON:
               if arch.startswith("ppc"):
                   cmd.append("--yaboot")
               elif arch.startswith("s390"):
                   cmd.append("--zipl")

            utils.subprocess_call(cmd)

            # Any post-grubby processing required (e.g. ybin, zipl, lilo)?
            if not ANCIENT_PYTHON and arch.startswith("ppc"):
                # FIXME - CHRP hardware uses a 'PPC PReP Boot' partition and doesn't require running ybin
                print "- applying ybin changes"
                cmd = [ "/sbin/ybin" ]
                utils.subprocess_call(cmd)
            elif not ANCIENT_PYTHON and arch.startswith("s390"):
                print "- applying zipl changes"
                cmd = [ "/sbin/zipl" ]
                utils.subprocess_call(cmd)
            else:
                # if grubby --bootloader-probe returns lilo,
                #    apply lilo changes
                if boot_probe_ret_code == 0 and string.find(probe_output, "lilo") != -1:
                    print "- applying lilo changes"
                    cmd = [ "/sbin/lilo" ]
                    utils.subprocess_call(cmd)

            if not self.add_reinstall_entry:
                print "- reboot to apply changes"
            else:
                print "- reinstallation entry added"

        return self.net_install(after_download)

    #---------------------------------------------------

    def get_insert_script(self,initrd):
        """
        Create bash script for inserting kickstart into initrd.
        Code heavily borrowed from internal auto-ks scripts.
        """
        return r"""
        cd /var/spool/koan
        mkdir initrd
        gzip -dc %s > initrd.tmp
        if mount -o loop -t ext2 initrd.tmp initrd >&/dev/null ; then
            cp ks.cfg initrd/
            ln initrd/ks.cfg initrd/tmp/ks.cfg
            umount initrd
            gzip -c initrd.tmp > initrd_final
        else
            echo "mount failed; treating initrd as a cpio archive..."
            cd initrd
            cpio -id <../initrd.tmp
            cp /var/spool/koan/ks.cfg .
            ln ks.cfg tmp/ks.cfg
            find . | cpio -o -H newc | gzip -9 > ../initrd_final
            echo "...done"
        fi
        """ % initrd

    #---------------------------------------------------

    def build_initrd(self,initrd,kickstart,data):
        """
        Crack open an initrd and install the kickstart file.
        """

        # save kickstart to file
        ksdata = utils.urlread(kickstart)
        fd = open("/var/spool/koan/ks.cfg","w+")
        if ksdata is not None:
            fd.write(ksdata)
        fd.close()

        # handle insertion of kickstart based on type of initrd
        fd = open("/var/spool/koan/insert.sh","w+")
        fd.write(self.get_insert_script(initrd))
        fd.close()
        utils.subprocess_call([ "/bin/bash", "/var/spool/koan/insert.sh" ])
        shutil.copyfile("/var/spool/koan/initrd_final", initrd)

    #---------------------------------------------------

    def connect_fail(self):
        raise InfoException, "Could not communicate with %s:%s" % (self.server, self.port)

    #---------------------------------------------------

    def get_data(self,what,name=None):
        try:
            if what[-1] == "s":
                data = getattr(self.xmlrpc_server, "get_%s" % what)()
            else:
                data = getattr(self.xmlrpc_server, "get_%s_for_koan" % what)(name)
        except:
            traceback.print_exc()
            self.connect_fail()
        if data == {}:
            raise InfoException("No entry/entries found")
        return data
    
    #---------------------------------------------------

    def get_ips(self,strdata):
        """
        Return a list of IP address strings found in argument.
        warning: not IPv6 friendly
        """
        return re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',strdata)

    #---------------------------------------------------

    def get_macs(self,strdata):
        """
        Return a list of MAC address strings found in argument.
        """
        return re.findall(r'[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F:0-9]{2}:[A-F:0-9]{2}', strdata.upper())

    #---------------------------------------------------

    def is_ip(self,strdata):
        """
        Is strdata an IP?
        warning: not IPv6 friendly
        """
        return self.get_ips(strdata) and True or False

    #---------------------------------------------------

    def is_mac(self,strdata):
        """
        Return whether the argument is a mac address.
        """
        return self.get_macs(strdata) and True or False

    #---------------------------------------------------

    def get_distro_files(self,profile_data, download_root):
        """
        Using distro data (fetched from bootconf tree), determine
        what kernel and initrd to download, and save them locally.
        """
        os.chdir(download_root)
        distro = self.safe_load(profile_data,'distro')
        kernel = self.safe_load(profile_data,'kernel')
        initrd = self.safe_load(profile_data,'initrd')
        kernel_short = os.path.basename(kernel)
        initrd_short = os.path.basename(initrd)
        kernel_save = "%s/%s" % (download_root, kernel_short)
        initrd_save = "%s/%s" % (download_root, initrd_short)

        if self.server:
            if kernel[0] == "/":
                kernel = "http://%s/cobbler/images/%s/%s" % (self.server, distro, kernel_short)
            if initrd[0] == "/":
                initrd = "http://%s/cobbler/images/%s/%s" % (self.server, distro, initrd_short)

        try:
            print "downloading initrd %s to %s" % (initrd_short, initrd_save)
            print "url=%s" % initrd
            utils.urlgrab(initrd,initrd_save)

            print "downloading kernel %s to %s" % (kernel_short, kernel_save)
            print "url=%s" % kernel
            utils.urlgrab(kernel,kernel_save)
        except:
            traceback.print_exc()
            raise InfoException, "error downloading files"
        profile_data['kernel_local'] = kernel_save
        profile_data['initrd_local'] = initrd_save

    #---------------------------------------------------

    def calc_kernel_args(self, pd, replace_self=0):
        kickstart = self.safe_load(pd,'kickstart')
        options   = self.safe_load(pd,'kernel_options',default='')
        breed     = self.safe_load(pd,'breed')

        kextra    = ""
        if kickstart is not None and kickstart != "":
            if breed is not None and breed == "suse":
                kextra = "autoyast=" + kickstart
            else:
                kextra = "ks=" + kickstart 

        if options !="":
            kextra = kextra + " " + options
        # parser issues?  lang needs a trailing = and somehow doesn't have it.

        # convert the from-cobbler options back to a hash
        # so that we can override it in a way that works as intended

        hashv = utils.input_string_or_hash(kextra)

        if self.static_interface is not None and (breed is None or breed == "redhat"):
            interface_name = self.static_interface
            interfaces = self.safe_load(pd, "interfaces")
            if interface_name.startswith("eth"):
                alt_interface_name = interface_name.replace("eth", "intf")
                interface_data = self.safe_load(interfaces, interface_name, alt_interface_name)
            else:
                interface_data = self.safe_load(interfaces, interface_name)

            ip = self.safe_load(interface_data, "ip_address")
            subnet = self.safe_load(interface_data, "subnet")
            gateway = self.safe_load(pd, "gateway")

            hashv["ksdevice"] = self.static_interface
            if ip is not None:
                hashv["ip"] = ip
            if subnet is not None:
                hashv["netmask"] = subnet
            if gateway is not None:
                hashv["gateway"] = gateway

        if replace_self and self.embed_kickstart:
           hashv["ks"] = "file:ks.cfg"

        if self.kopts_override is not None:
           hash2 = utils.input_string_or_hash(self.kopts_override)
           hashv.update(hash2)
        options = utils.hash_to_string(hashv)
        options = string.replace(options, "lang ","lang= ")
        # if using ksdevice=bootif that only works for PXE so replace
        # it with something that will work
        options = string.replace(options, "ksdevice=bootif","ksdevice=link")
        return options

    #---------------------------------------------------

    def virt_net_install(self,profile_data):
        """
        Invoke virt guest-install (or tweaked copy thereof)
        """
        pd = profile_data
        self.load_virt_modules()

        arch                          = self.safe_load(pd,'arch','x86')
        kextra                        = self.calc_kernel_args(pd)
        (uuid, create_func, fullvirt, can_poll) = self.virt_choose(pd)

        virtname            = self.calc_virt_name(pd)

        ram                 = self.calc_virt_ram(pd)

        vcpus               = self.calc_virt_cpus(pd)
        path_list           = self.calc_virt_path(pd, virtname)
        size_list           = self.calc_virt_filesize(pd)
        disks               = self.merge_disk_data(path_list,size_list)
        virt_auto_boot      = self.calc_virt_autoboot(pd, self.virt_auto_boot)

        results = create_func(
                name             =  virtname,
                ram              =  ram,
                disks            =  disks,
                uuid             =  uuid,
                extra            =  kextra,
                vcpus            =  vcpus,
                profile_data     =  profile_data,
                arch             =  arch,
                no_gfx           =  self.no_gfx,
                fullvirt         =  fullvirt,
                bridge           =  self.virt_bridge,
                virt_type        =  self.virt_type,
                virt_auto_boot   =  virt_auto_boot,
                qemu_driver_type =  self.qemu_disk_type
        )

        print results

        if can_poll is not None and self.should_poll:
            import libvirt
            print "- polling for virt completion"
            conn = None
            if can_poll == "xen":
               conn = libvirt.open(None)
            elif can_poll == "qemu":
               conn = libvirt.open("qemu:///system")
            else:
               raise InfoException("Don't know how to poll this virt-type")
            ct = 0
            while True:
               time.sleep(3)
               state = utils.get_vm_state(conn, virtname)
               if state == "running":
                   print "- install is still running, sleeping for 1 minute (%s)" % ct
                   ct = ct + 1
                   time.sleep(60)
               elif state == "crashed":
                   print "- the install seems to have crashed."
                   return "failed"
               elif state == "shutdown":
                   print "- shutdown VM detected, is the install done?  Restarting!"
                   utils.find_vm(conn, virtname).create()    
                   return results
               else:
                   raise InfoException("internal error, bad virt state")

        if virt_auto_boot:
            if self.virt_type in [ "xenpv", "xenfv" ]:
                utils.create_xendomains_symlink(virtname)
            elif self.virt_type == "qemu":
               utils.libvirt_enable_autostart(virtname)
            else:
                print "- warning: don't know how to autoboot this virt type yet"
            # else...
        return results

    #---------------------------------------------------

    def load_virt_modules(self):
        try:
            import xencreate
            import qcreate
            import imagecreate
        except:
            traceback.print_exc()
            raise InfoException("no virtualization support available, install python-virtinst?")

    #---------------------------------------------------

    def virt_choose(self, pd):
        fullvirt = False
        can_poll = None
        if (self.image is not None) and (pd["image_type"] == "virt-clone"):
            fullvirt = True
            uuid = None
            import imagecreate
            creator = imagecreate.start_install
        elif self.virt_type in [ "xenpv", "xenfv" ]:
            uuid    = self.get_uuid(self.calc_virt_uuid(pd))
            import xencreate
            creator = xencreate.start_install
            if self.virt_type == "xenfv":
               fullvirt = True 
            can_poll = "xen"
        elif self.virt_type == "qemu":
            fullvirt = True
            uuid    = None
            import qcreate
            creator = qcreate.start_install
            can_poll = "qemu"
        elif self.virt_type == "vmware":
            import vmwcreate
            uuid = None
            creator = vmwcreate.start_install
        elif self.virt_type == "vmwarew":
            import vmwwcreate
            uuid = None
            creator = vmwwcreate.start_install
        else:
            raise InfoException, "Unspecified virt type: %s" % self.virt_type
        return (uuid, creator, fullvirt, can_poll)

    #---------------------------------------------------

    def merge_disk_data(self, paths, sizes):
        counter = 0
        disks = []
        for p in paths:
            path = paths[counter]
            if counter >= len(sizes): 
                size = sizes[-1]
            else:
                size = sizes[counter]
            disks.append([path,size])
            counter = counter + 1
        if len(disks) == 0:
            print "paths: ", paths
            print "sizes: ", sizes
            raise InfoException, "Disk configuration not resolvable!"
        return disks

    #---------------------------------------------------

    def calc_virt_name(self,profile_data):
        if self.virt_name is not None:
           # explicit override
           name = self.virt_name
        elif profile_data.has_key("interfaces"):
           # this is a system object, just use the name
           name = profile_data["name"]
        else:
           # just use the time, we used to use the MAC
           # but that's not really reliable when there are more
           # than one.
           name = time.ctime(time.time())
        # keep libvirt happy with the names
        return name.replace(":","_").replace(" ","_")


    #--------------------------------------------------

    def calc_virt_autoboot(self,data,override_autoboot=False):
        if override_autoboot:
           return True

        autoboot = self.safe_load(data,'virt_auto_boot',0)
        autoboot = str(autoboot).lower()

        if autoboot in [ "1", "true", "y", "yes" ]:
           return True

        return False

    #--------------------------------------------------

    def calc_virt_filesize(self,data,default_filesize=0):

        # MAJOR FIXME: are there overrides?  
        size = self.safe_load(data,'virt_file_size','xen_file_size',0)

        tokens = str(size).split(",")
        accum = []
        for t in tokens:
            accum.append(self.calc_virt_filesize2(data,size=t))
        return accum

    #---------------------------------------------------

    def calc_virt_filesize2(self,data,default_filesize=1,size=0):
        """
        Assign a virt filesize if none is given in the profile.
        """

        err = False
        try:
            int(size)
        except:
            err = True
        if size is None or size == '':
            err = True
        if err:
            print "invalid file size specified, using defaults"
            return default_filesize
        return int(size)

    #---------------------------------------------------

    def calc_virt_ram(self,data,default_ram=64):
        """
        Assign a virt ram size if none is given in the profile.
        """
        size = self.safe_load(data,'virt_ram','xen_ram',0)
        err = False
        try:
            int(size)
        except:
            err = True
        if size is None or size == '' or int(size) < default_ram:
            err = True
        if err:
            print "invalid RAM size specified, using defaults."
            return default_ram
        return int(size)

    #---------------------------------------------------

    def calc_virt_cpus(self,data,default_cpus=1):
        """
        Assign virtual CPUs if none is given in the profile.
        """
        size = self.safe_load(data,'virt_cpus',default=default_cpus)
        try:
            isize = int(size)
        except:
            traceback.print_exc()
            return default_cpus
        return isize

    #---------------------------------------------------

    def calc_virt_mac(self,data):
        if not self.is_virt:
            return None # irrelevant 
        if self.is_mac(self.system):
            return self.system.upper()
        return self.random_mac()

    #---------------------------------------------------

    def calc_virt_uuid(self,data):
        # TODO: eventually we may want to allow some koan CLI
        # option (or cobbler system option) for passing in the UUID.  
        # Until then, it's random.
        return None
        """
        Assign a UUID if none/invalid is given in the profile.
        """
        my_id = self.safe_load(data,'virt_uuid','xen_uuid',0)
        uuid_re = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        err = False
        try:
            str(my_id)
        except:
            err = True
        if my_id is None or my_id == '' or not uuid_re.match(id):
            err = True
        if err and my_id is not None:
            print "invalid UUID specified.  randomizing..."
            return None
        return my_id

    #----------------------------------------------------

    def calc_virt_path(self,pd,name):

        # input is either a single item or a string list
        # it's not in the arguments to this function .. it's from one of many
        # potential sources

        location = self.virt_path

        if location is None:
           # no explicit CLI override, what did the cobbler server say?
           location = self.safe_load(pd, 'virt_path', default=None)

        if location is None or location == "":
           # not set in cobbler either? then assume reasonable defaults
           if self.virt_type in [ "xenpv", "xenfv" ]:
               prefix = "/var/lib/xen/images/"
           elif self.virt_type == "qemu":
               prefix = "/var/lib/libvirt/images/"
           elif self.virt_type == "vmwarew":
               prefix = "/var/lib/vmware/%s/" % name
           else:
               prefix = "/var/lib/vmware/images/"
           if not os.path.exists(prefix):
               print "- creating: %s" % prefix
               os.makedirs(prefix)
           return [ "%s/%s-disk0" % (prefix, name) ]

        # ok, so now we have a user that either through cobbler or some other
        # source *did* specify a location.   It might be a list.
            
        virt_sizes = self.calc_virt_filesize(pd)

        path_splitted = location.split(",")
        paths = []
        count = -1
        for x in path_splitted:
            count = count + 1
            path = self.calc_virt_path2(pd,name,offset=count,location=x,sizes=virt_sizes)
            paths.append(path)
        return paths


    #---------------------------------------------------

    def calc_virt_path2(self,pd,name,offset=0,location=None,sizes=[]):

        # Parse the command line to determine if this is a 
        # path, a partition, or a volume group parameter
        #   Ex:   /foo
        #   Ex:   partition:/dev/foo
        #   Ex:   volume-group:/dev/foo/
            
        # chosing the disk image name (if applicable) is somewhat
        # complicated ...

        # use default location for the virt type

        if not location.startswith("/dev/") and location.startswith("/"):
            # filesystem path
            if os.path.isdir(location):
                return "%s/%s-disk%s" % (location, name, offset)
            elif not os.path.exists(location) and os.path.isdir(os.path.dirname(location)):
                return location
            else:
                raise InfoException, "invalid location: %s" % location                
        elif location.startswith("/dev/"):
            # partition
            if os.path.exists(location):
                return location
            else:
                raise InfoException, "virt path is not a valid block device"
        else:
            # it's a volume group, verify that it exists
            args = "vgs -o vg_name"
            print "%s" % args
            vgnames = sub_process.Popen(args, shell=True, stdout=sub_process.PIPE).communicate()[0]
            print vgnames

            if vgnames.find(location) == -1:
                raise InfoException, "The volume group [%s] does not exist." % location
            
            # check free space
            args = "LANG=C vgs --noheadings -o vg_free --units g %s" % location
            print args
            cmd = sub_process.Popen(args, stdout=sub_process.PIPE, shell=True)
            freespace_str = cmd.communicate()[0]
            freespace_str = freespace_str.split("\n")[0].strip()
            freespace_str = freespace_str.replace("G","") # remove gigabytes
            print "(%s)" % freespace_str
            freespace = int(float(freespace_str))

            virt_size = self.calc_virt_filesize(pd)

            if len(virt_size) > offset:
                virt_size = sizes[offset] 
            else:
                return sizes[-1]

            if freespace >= int(virt_size):
            
                # look for LVM partition named foo, create if doesn't exist
                args = "lvs -o lv_name %s" % location
                print "%s" % args
                lvs_str=sub_process.Popen(args, stdout=sub_process.PIPE, shell=True).communicate()[0]
                print lvs_str
         
                name = "%s-disk%s" % (name,offset)
 
                # have to create it?
                if lvs_str.find(name) == -1:
                    args = "lvcreate -L %sG -n %s %s" % (virt_size, name, location)
                    print "%s" % args
                    lv_create = sub_process.call(args, shell=True)
                    if lv_create != 0:
                        raise InfoException, "LVM creation failed"

                # partition location
                partition_location = "/dev/mapper/%s-%s" % (location,name.replace('-','--'))

                # check whether we have SELinux enabled system
                args = "/usr/sbin/selinuxenabled"
                selinuxenabled = sub_process.call(args)
                if selinuxenabled == 0:
                    # required context type
                    context_type = "virt_image_t"

                    # change security context type to required one
                    args = "/usr/bin/chcon -t %s %s" % (context_type, partition_location)
                    print "%s" % args
                    change_context = sub_process.call(args, close_fds=True, shell=True)

                    # modify SELinux policy in order to preserve security context
                    # between reboots
                    args = "/usr/sbin/semanage fcontext -a -t %s %s" % (context_type, partition_location)
                    print "%s" % args
                    change_context |= sub_process.call(args, close_fds=True, shell=True)
                    
                    if change_context != 0:
                        raise InfoException, "SELinux security context setting to LVM partition failed"

                # return partition location
                return partition_location

            else:
                raise InfoException, "volume group needs %s GB free space." % virt_size


    def randomUUID(self):
        """
        Generate a random UUID.  Copied from xend/uuid.py
        """
        rc = []
        for x in range(0, 16):
           rc.append(random.randint(0,255))
        return rc

    def uuidToString(self, u):
        """
        return uuid as a string
        """
        return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
            "%02x" * 6]) % tuple(u)

    def get_uuid(self,uuid):
        """
        return the passed-in uuid, or a random one if it's not set.
        """
        if uuid:
            return uuid
        return self.uuidToString(self.randomUUID())

if __name__ == "__main__":
    main()
