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
import urllib2
import opt_parse  # importing this for backwards compat with 2.2
import exceptions
import sub_process
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

COBBLER_REQUIRED = 0.900

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
   "virt_ram","virt_disk","virt_type", "virt_path"
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

    p = opt_parse.OptionParser()
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
                 help="attach to this cobbler server")
    p.add_option("-S", "--static-interface",
                 dest="static_interface",
                 help="use static network configuration from this interface while installing")
    p.add_option("-t", "--port",
                 dest="port",
                 help="cobbler xmlrpc port (default 25151)")
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
                 help="Instead of writing a new bootloader when doing replace_self, just kexec the new kernel and initrd")

    (options, args) = p.parse_args()

    if not os.getuid() == 0:
        print "koan requires root access"
        return 3

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

class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        try:
            xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)
        except:
            # for RHEL3's xmlrpclib -- cobblerd should strip Nones anyway
            xmlrpclib.ServerProxy.__init__(self, url)

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
        if not self.server:
            if self.list_profiles:
                raise InfoException, "--list-profiles only valid with --server"
            if self.list_systems:
                raise InfoException, "--list-systems only valid with --server"
            if self.profile:
                raise InfoException, "--profile only valid with --server"
            if self.system:
                raise InfoException, "--system only valid with --server"
            if self.port:
                raise InfoException, "--port only valid with --server"


        # set up XMLRPC connection
        if self.server:

            if not self.port: 
                self.port = 25151 
        
            # server name can either be explicit or DISCOVER, which
            # means "check zeroconf" instead.

            uses_avahi = False
            if self.server == "DISCOVER": 
                uses_avahi = True
                if not os.path.exists("/usr/bin/avahi-browse"):
                    raise InfoException, "avahi-tools is not installed"
                potential_servers = self.avahi_search()
            else:
                potential_servers = [ self.server ]

            # zeroconf could have returned more than one server.
            # either way, let's see that we can connect to the servers
            # we might have gotten back -- occasionally zeroconf
            # does stupid things and publishes internal or 
            # multiple addresses

            connect_ok = False
            for server in potential_servers:

                # assume for now we are connected to the server
                # that we should be connected to

                self.server = server
                url = "http://%s:80/cobbler_api" % (server)
 
                # make a sample call to check for connectivity
                # we use this as opposed to version as version was not
                # in the original API

                try:
                    if uses_avahi:
                        print "- connecting to: %s" % server
                    try:
                        # first try port 80
                        self.xmlrpc_server = ServerProxy(url)
                        self.xmlrpc_server.get_profiles()
                    except:
                        # now try specified port in case Apache proxying
                        # is not configured
                        url = "http://%s:%s" % (server, self.port)
                        self.xmlrpc_server = ServerProxy(url)
                        self.xmlrpc_server.get_profiles()
                    connect_ok = True
                    break
                except:
                    pass
                
            # if connect_ok is still off, that means we never found
            # a match in the server list.  This is bad.

            if not connect_ok:
                self.connect_fail()
                 
            # ok, we have a valid connection.
            # if we discovered through zeroconf, show the user what they've 
            # connected to ...

            if uses_avahi:
                print "- connected to: %s" % self.server        

            # now check for the cobbler version.  Ideally this should be done
            # for each server, but if there is more than one cobblerd on the
            # network someone should REALLY be explicit anyhow.  So we won't
            # handle that and leave it to the network admins for now.

            version = None
            try:
                version = self.xmlrpc_server.version()
            except:
                raise InfoException("cobbler server is downlevel and needs to be updated")
             
            if version == "?": 
                print "warning: cobbler server did not report a version"
                print "         will attempt to proceed."

            elif COBBLER_REQUIRED > version:
                raise InfoException("cobbler server is downlevel, need version >= %s, have %s" % (COBBLER_REQUIRED, version))

            # if command line input was just for listing commands,
            # run them now and quit, no need for further work

            if self.list_items:
                self.list(self.list_items)
                return
            
        
            # if both --profile and --system were ommitted, autodiscover
            if self.is_virt:
                if (self.profile is None and self.system is None and self.image is None):
                    raise InfoException, "must specify --profile, --system, or --image"
            else:
                if (self.profile is None and self.system is None and self.image is None):
                    self.system = self.autodetect_system()



        # if --virt-type was specified and invalid, then fail
        if self.virt_type is not None:
            self.virt_type = self.virt_type.lower()
            if self.virt_type not in [ "qemu", "xenpv", "xenfv", "xen", "vmware", "vmwarew", "auto" ]:
               if self.virt_type == "xen":
                   self.virt_type = "xenpv"
               raise InfoException, "--virt-type should be qemu, xenpv, xenfv, vmware, vmwarew, or auto"

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
    
    #---------------------------------------------------

    def autodetect_system(self):
        """
        Determine the name of the cobbler system record that
        matches this MAC address.  FIXME: should use IP 
        matching as secondary lookup eventually to be more PXE-like
        """

        fd = os.popen("/sbin/ifconfig")
        mac = [line.strip() for line in fd.readlines()][0].split()[-1] #this needs to be replaced
        fd.close()
        if self.is_mac(mac) == False:
            raise InfoException, "Mac address not accurately detected"
        systems = self.get_data("systems")

        detected_systems = []
        for system in systems:
            for (iname, interface) in system['interfaces'].iteritems():
                if interface['mac_address'].upper() == mac.upper():
                    detected_systems.append(system['name'])
                    break

        if len(detected_systems) > 1:
            raise InfoException, "Multiple systems with matching mac addresses"
        elif len(detected_systems) == 0:
            raise InfoException, "No system matching MAC address %s found" % mac
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

        if profile_data.has_key("kickstart"):

            # fix URLs
            if profile_data["kickstart"].startswith("/"):
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

            url_parser = opt_parse.OptionParser()
            url_parser.add_option("--url", dest="url")

            nfs_parser = opt_parse.OptionParser()
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

            self.build_initrd(
                self.safe_load(profile_data,'initrd_local'),
                kickstart,
                profile_data
            )

            if len(k_args) > 255:
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
            k_args = self.calc_kernel_args(profile_data,replace_self=True)

            kickstart = self.safe_load(profile_data,'kickstart')

            self.build_initrd(
                self.safe_load(profile_data,'initrd_local'),
                kickstart,
                profile_data
            )

            if len(k_args) > 255:
                raise InfoException, "Kernel options are too long, 255 chars exceeded: %s" % k_args

            cmd = [ "/sbin/grubby",
                    "--add-kernel", self.safe_load(profile_data,'kernel_local'),
                    "--initrd", self.safe_load(profile_data,'initrd_local'),
                    "--args", k_args,
                    "--copy-default"
            ]
            if self.add_reinstall_entry:
               cmd.append("--title=Reinstall")
            else:
               cmd.append("--make-default")
               cmd.append("--title=kick%s" % int(time.time()))
               
            if self.live_cd:
               cmd.append("--bad-image-okay")
               cmd.append("--boot-filesystem=/dev/sda1")
               cmd.append("--config-file=/tmp/boot/boot/grub/grub.conf")
               # utils.subprocess_call(["/sbin/grubby","--remove-kernel","/boot/vmlinuz"])

            # Are we running on ppc?
            arch_cmd = sub_process.Popen("/bin/uname -m", stdout=sub_process.PIPE, shell=True)
            uname_str = arch_cmd.communicate()[0]
            if uname_str.startswith("ppc"):
               cmd.append("--yaboot")
            elif uname_str.startswith("s390"):
               cmd.append("--zipl")

            utils.subprocess_call(cmd)

            # Any post-grubby processing required (e.g. ybin, zipl, lilo)?
            if uname_str.startswith("ppc"):
                # FIXME - CHRP hardware uses a 'PPC PReP Boot' partition and doesn't require running ybin
                print "- applying ybin changes"
                cmd = [ "/sbin/ybin" ]
                sub_process.Popen(cmd, stdout=sub_process.PIPE).communicate()[0]
            elif uname_str.startswith("s390"):
                print "- applying zipl changes"
                cmd = [ "/sbin/zipl" ]
                sub_process.Popen(cmd, stdout=sub_process.PIPE).communicate()[0]
            else:
                # if grubby --bootloader-probe returns lilo,
                #    apply lilo changes
                cmd = [ "/sbin/grubby", "--bootloader-probe" ]
                probe_process = sub_process.Popen(cmd, stdout=sub_process.PIPE)
                which_loader = probe_process.communicate()[0]
                if probe_process.returncode == 0 and \
                       which_loader.find("lilo") != -1:
                    print "- applying lilo changes"
                    cmd = [ "/sbin/lilo" ]
                    sub_process.Popen(cmd, stdout=sub_process.PIPE).communicate()[0]

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

    def is_ip(self,strdata):
        """
        Is strdata an IP?
        warning: not IPv6 friendly
        """
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',strdata):
            return True
        return False

    #---------------------------------------------------

    def is_mac(self,strdata):
        """
        Return whether the argument is a mac address.
        """
        if strdata is None:
            return False
        strdata = strdata.upper()
        if re.search(r'[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F0-9]{2}:[A-F:0-9]{2}:[A-F:0-9]{2}',strdata):
            return True
        return False

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
            if kernel.startswith("/"):
                kernel = "http://%s/cobbler/images/%s/%s" % (self.server, distro, kernel_short)
            if initrd.startswith("/"):
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

    def calc_kernel_args(self, pd, replace_self=False):
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
            gateway = self.safe_load(interface_data, "gateway")

            hashv["ksdevice"] = self.static_interface
            if ip is not None:
                hashv["ip"] = ip
            if subnet is not None:
                hashv["netmask"] = subnet
            if gateway is not None:
                hashv["gateway"] = gateway

        if replace_self:
           hashv["ks"] = "file:ks.cfg"

        if self.kopts_override is not None:
           hash2 = utils.input_string_or_hash(self.kopts_override)
           hashv.update(hash2)
        options = ""
        for x in hashv.keys():
            if hashv[x] is None:
                options = options + "%s " % x
            else:
                options = options + "%s=%s " % (x, hashv[x])
        options = options.replace("lang ","lang= ")
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
        (uuid, create_func, fullvirt) = self.virt_choose(pd)

        virtname            = self.calc_virt_name(pd)

        ram                 = self.calc_virt_ram(pd)

        vcpus               = self.calc_virt_cpus(pd)
        path_list           = self.calc_virt_path(pd, virtname)
        size_list           = self.calc_virt_filesize(pd)
        disks               = self.merge_disk_data(path_list,size_list)

        results = create_func(
                name          =  virtname,
                ram           =  ram,
                disks         =  disks,
                uuid          =  uuid, 
                extra         =  kextra,
                vcpus         =  vcpus,
                profile_data  =  profile_data,       
                arch          =  arch,
                no_gfx        =  self.no_gfx,   
                fullvirt      =  fullvirt,    
                bridge        =  self.virt_bridge,
                virt_type     =  self.virt_type
        )

        print results
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
        elif self.virt_type == "qemu":
            fullvirt = True
            uuid    = None
            import qcreate
            creator = qcreate.start_install
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
        return (uuid, creator, fullvirt)

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
               prefix = "/opt/qemu/"
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
            args = "/usr/sbin/vgs -o vg_name"
            print "%s" % args
            vgnames = sub_process.Popen(args, shell=True, stdout=sub_process.PIPE).communicate()[0]
            print vgnames

            if vgnames.find(location) == -1:
                raise InfoException, "The volume group [%s] does not exist." % location
            
            # check free space
            args = "/usr/sbin/vgs --noheadings -o vg_free --units g %s" % location
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
                args = "/usr/sbin/lvs -o lv_name %s" % location
                print "%s" % args
                lvs_str=sub_process.Popen(args, stdout=sub_process.PIPE, shell=True).communicate()[0]
                print lvs_str
         
                name = "%s-disk%s" % (name,offset)
 
                # have to create it?
                if lvs_str.find(name) == -1:
                    args = "/usr/sbin/lvcreate -L %sG -n %s %s" % (virt_size, name, location)
                    print "%s" % args
                    lv_create = sub_process.call(args, shell=True)
                    if lv_create != 0:
                        raise InfoException, "LVM creation failed"

                # return partition location
                return "/dev/mapper/%s-%s" % (location.replace('-','--'), name.replace('-','--'))
            else:
                raise InfoException, "volume group needs %s GB free space." % virt_size


    def randomUUID(self):
        """
        Generate a random UUID.  Copied from xend/uuid.py
        """
        return [ random.randint(0, 255) for x in range(0, 16) ]

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

    def avahi_search(self):
        """
        If no --server is specified, attempt to scan avahi (mDNS) to find one
        """

        matches = []

        cmd = [ "/usr/bin/avahi-browse", "--all", "--terminate", "--resolve" ]
        print "- running: %s" % " ".join(cmd)
        cmdp = sub_process.Popen(cmd, shell=False, stdout=sub_process.PIPE)
        print "- analyzing zeroconf scan results"
        data = cmdp.communicate()[0]
        lines = data.split("\n")
        
        # FIXME: should switch to Python bindings at some point.
        match_mode = False
        for line in lines:
            if line.startswith("="):
                if line.find("cobblerd") != -1:
                   match_mode = True
                else:
                   match_mode = False
            if match_mode and line.find("address") != -1 and line.find("[") != -1:
                (first, last) = line.split("[",1)
                (addr, junk) = last.split("]",1)
                if addr.find(":") == -1:
                    # exclude IPv6 and MAC addrs that sometimes show up in results
                    # FIXME: shouldn't exclude IPv6?
                    matches.append(addr.strip())

        return matches

if __name__ == "__main__":
    main()
