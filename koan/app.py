"""
koan = kickstart over a network

a tool for network provisioning of virtualization (xen,kvm/qemu) 
and network re-provisioning of existing Linux systems.  
used with 'cobbler'. see manpage for usage.

Copyright 2006-2007 Red Hat, Inc.
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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

# the version of cobbler needed to interact with this version of koan
# this is an decimal value (major + 0.1 * minor + 0.01 * maint)
COBBLER_REQUIRED = 0.603 # FIXME: version should be parsed better than this

"""
koan --virt [--profile=webserver|--system=name] --server=hostname
koan --replace-self --profile=foo --server=hostname
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

def setupLogging(appname, debug=False):
    """
    set up logging ... code borrowed/adapted from virt-manager
    """
    import logging
    import logging.handlers
    vi_dir = os.path.expanduser("~/.koan")
    if not os.access(vi_dir,os.W_OK):
        try:
            os.mkdir(vi_dir)
        except IOError, e:
            raise RuntimeError, "Could not create %d directory: " % vi_dir, e

    dateFormat = "%a, %d %b %Y %H:%M:%S"
    fileFormat = "[%(asctime)s " + appname + " %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamFormat = "%(asctime)s %(levelname)-8s %(message)s"
    filename = os.path.join(vi_dir, appname + ".log")

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    fileHandler = logging.handlers.RotatingFileHandler(filename, "a",
                                                       1024*1024, 5)

    fileHandler.setFormatter(logging.Formatter(fileFormat,
                                               dateFormat))
    rootLogger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(logging.Formatter(streamFormat,
                                                 dateFormat))
    if debug:
        streamHandler.setLevel(logging.DEBUG)
    else:
        streamHandler.setLevel(logging.ERROR)
    rootLogger.addHandler(streamHandler)


def main():
    """
    Command line stuff...
    """

    try:
        setupLogging("koan")
    except:
        # most likely running RHEL3, where we don't need virt logging anyway
        pass

    # FIXME: overrides for --virt-mac have been requested

    p = opt_parse.OptionParser()
    p.add_option("-C", "--livecd",
                 dest="live_cd",
                 action="store_true",
                 help="indicates koan is running from custom LiveCD")
    p.add_option("-l", "--list-profiles",
                 dest="list_profiles",
                 action="store_true",
                 help="list profiles the server can provision")
    p.add_option("-L", "--list-systems",
                 dest="list_systems",
                 action="store_true",
                 help="list systems the server can provision")
    p.add_option("-v", "--virt",
                 dest="is_virt",
                 action="store_true",
                 help="requests new virtualized image installation")
    p.add_option("-V", "--virt-name",
                 dest="virt_name",
                 help="create the virtual guest with this name")
    p.add_option("-r", "--replace-self",
                 dest="is_replace",
                 action="store_true",
                 help="requests re-provisioning of this host")
    p.add_option("-D", "--display",
                 dest="is_display",
                 action="store_true",
                 help="display the configuration, don't install it")
    p.add_option("-p", "--profile",
                 dest="profile",
                 help="cobbler profile to install")
    p.add_option("-y", "--system",
                 dest="system",
                 help="cobbler system to install")
    p.add_option("-s", "--server",
                 dest="server",
                 help="specify the cobbler server")
    p.add_option("-t", "--port",
                 dest="port",
                 help="cobbler xmlrpc port (default 25151)")
    p.add_option("-A", "--autonet",
                 dest="autonet",
                 action="store_true",
                 help="have koan try to automatically set up networking on the kernel command line")
    p.add_option("-P", "--virt-path",
                 dest="virt_path",
                 help="virtual install location (see manpage)")  
    p.add_option("-T", "--virt-type",
                 dest="virt_type",
                 help="virtualization install type (xenpv,xenfv,qemu,vmware)")
    p.add_option("-n", "--nogfx",
                 action="store_true", 
                 dest="no_gfx",
                 help="disable Xen graphics (xenpv,xenfv)")
    p.add_option("", "--no-cobbler",
                 dest="no_cobbler",
                 help="specify URL for kickstart directly, bypassing the cobbler server")

    (options, args) = p.parse_args()

    if not os.getuid() == 0:
        print "koan requires root access"
        return 3

    try:
        k = Koan()
        k.list_systems      = options.list_systems
        k.list_profiles     = options.list_profiles
        k.server            = options.server
        k.is_virt           = options.is_virt
        k.is_replace        = options.is_replace
        k.is_display        = options.is_display
        k.profile           = options.profile
        k.system            = options.system
        k.autonet           = options.autonet
        k.live_cd           = options.live_cd
        k.virt_path         = options.virt_path
        k.virt_type         = options.virt_type
        k.no_gfx            = options.no_gfx
        k.no_cobbler         = options.no_cobbler

        if options.virt_name is not None:
            k.virt_name          = options.virt_name
        if options.port is not None:
            k.port              = options.port
        k.run()

    except Exception, e:
        (xa, xb, tb) = sys.exc_info()
        if str(xb).find("InfoException") != -1:
            traceback.print_exc()
        else:
            print str(xb)
    return 0

#=======================================================

class InfoException(exceptions.Exception):
    """
    Custom exception for tracking of fatal errors.
    """
    pass

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
        self.is_replace        = None
        self.dryrun            = None
        self.port              = None
        self.autonet           = None
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
        if self.server is None and self.no_cobbler is None:
            raise InfoException, "no server specified"

        # check to see that exclusive arguments weren't used together
        found = 0
        for x in (self.is_virt, self.is_replace, self.is_display, self.list_profiles, self.list_systems):
            if x:
               found = found+1
        if found != 1:
            if not self.no_cobbler:
                raise InfoException, "choose: --virt, --replace-self or --display"
            else:
                raise InfoException, "missing argument: --replace-self ?"
 

        # for now, kickstart only works with --replace-self
        if self.no_cobbler and self.is_virt:
            raise InfoException, "--no-cobbler does not work with --virt"


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

            if self.list_systems:
                self.list(False)
                return
            if self.list_profiles:
                self.list(True)
                return
        
            # if both --profile and --system were ommitted, autodiscover
            if self.is_virt:
                if (self.profile is None and self.system is None):
                    raise InfoException, "must specify --profile or --system"
            else:
                if (self.profile is None and self.system is None):
                    self.system = self.autodetect_system()



        # if --virt-type was specified and invalid, then fail
        if self.virt_type is not None:
            self.virt_type = self.virt_type.lower()
            if self.virt_type not in [ "qemu", "xenpv", "xenfv", "xen", "vmware", "auto" ]:
               if self.virt_type == "xen":
                   self.virt_type = "xenpv"
               raise InfoException, "--virttype should be qemu, xenpv, vmware, or auto"

        # perform one of three key operations
        if self.is_virt:
            self.virt()
        elif self.is_replace:
            self.replace()
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
        systems = self.get_systems_xmlrpc()

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

    def urlread(self,url):
        """
        to support more distributions, implement (roughly) some 
        parts of urlread and urlgrab from urlgrabber, in ways that
        are less cool and less efficient.
        """
        print "- reading URL: %s" % url
        if url is None or url == "":
            raise InfoException, "invalid URL: %s" % url

        elif url.startswith("nfs"):
            try:
                ndir  = os.path.dirname(url[6:])
                nfile = os.path.basename(url[6:])
                nfsdir = tempfile.mkdtemp(prefix="koan_nfs",dir="/tmp")
                nfsfile = os.path.join(nfsdir,nfile)
                cmd = ["mount","-t","nfs","-o","ro", ndir, nfsdir]
                self.subprocess_call(cmd)
                fd = open(nfsfile)
                data = fd.read()
                fd.close()
                cmd = ["umount",nfsdir]
                self.subprocess_call(cmd)
                return data
            except:
                raise InfoException, "Couldn't mount and read URL: %s" % url
            
        elif url.startswith("http") or url.startswith("ftp"):
            try:
                fd = urllib2.urlopen(url)
                data = fd.read()
                fd.close()
                return data
            except:
                raise InfoException, "Couldn't download: %s" % url
        elif url.startswith("file"):
            try:
                fd = open(url[5:])
                data = fd.read()
                fd.close()
                return data
            except:
                raise InfoException, "Couldn't read file from URL: %s" % url
                
        else:
            raise InfoException, "Unhandled URL protocol: %s" % url

    #---------------------------------------------------

    def urlgrab(self,url,saveto):
        """
        like urlread, but saves contents to disk.
        see comments for urlread as to why it's this way.
        """
        data = self.urlread(url)
        fd = open(saveto, "w+")
        fd.write(data)
        fd.close()

    #---------------------------------------------------

    def subprocess_call(self,cmd,ignore_rc=False):
        """
        Wrapper around subprocess.call(...)
        """
        print "- %s" % cmd
        rc = sub_process.call(cmd)
        if rc != 0 and not ignore_rc:
            raise InfoException, "command failed (%s)" % rc
        return rc

    #---------------------------------------------------

    def safe_load(self,hash,primary_key,alternate_key=None,default=None):
        if hash.has_key(primary_key): 
            return hash[primary_key]
        elif alternate_key is not None and hash.has_key(alternate_key):
            return hash[alternate_key]
        else:
            return default

    #---------------------------------------------------

    def net_install(self,after_download):
        """
        Actually kicks off downloads and auto-ks or virt installs
        """

        # initialise the profile, from the server if any
        if self.profile:
            profile_data = self.get_profile_xmlrpc(self.profile)
            filler = "kickstarts"
        elif self.system:
            profile_data = self.get_system_xmlrpc(self.system)
            filler = "kickstarts_sys"
        else:
            profile_data = {}
            filler = None

        if self.no_cobbler:
            # if the value given to no_cobbler has no url protocol
            #    specifier, add "file:" and make it absolute 

            slash_idx = self.no_cobbler.find("/")
            if slash_idx != -1:
                colon_idx = self.no_cobbler.find(":",0,slash_idx)
            else:
                colon_idx = self.no_cobbler.find(":")

            if colon_idx == -1:
                # no protocol specifier
                profile_data["kickstart"] = "file:%s" % os.path.abspath(self.no_cobbler)
                
            else:
                # protocol specifier
                profile_data["kickstart"] = self.no_cobbler

        if profile_data.has_key("kickstart"):

            # fix URLs
            if filler and profile_data["kickstart"].startswith("/"):
               profile_data["kickstart"] = "http://%s/cblr/%s/%s/ks.cfg" % (profile_data['server'], filler, profile_data['name'])
                
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
            if self.live_cd:
                download = "/tmp/boot/boot"

            elif os.path.exists("/boot/efi/EFI/redhat/elilo.conf"):
                download = "/boot/efi/EFI/redhat"

            else:
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
                # note: auto never selects vmware, maybe it should if we find it?
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
                    raise InfoException("need python-virtinst >= 0.2 to do net installs for qemu/kvm")

            # for vmware
            if self.virt_type == "vmware":
                # FIXME: if any vmware specific checks are required (for deps) do them here.
                pass

            # for both virt types
            if os.path.exists("/etc/rc.d/init.d/libvirtd"):
                rc = sub_process.call("/sbin/service libvirtd status", stdout=None, shell=True)
                if rc != 0:
                    # libvirt running?
                    raise InfoException("libvirtd needs to be running")


            if self.virt_type in [ "xenpv", "xenfv" ]:
                download = "/var/lib/xen" 
            elif self.virt_type in [ "vmware" ] :
                download = None # we are downloading sufficient metadata to initiate PXE
            else: # qemu
                download = None # fullvirt, can use set_location in virtinst library, no D/L needed yet

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
            raw = self.urlread(profile_data["kickstart"])
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

    def url_read(self,url):
        fd = urllib2.urlopen(url)
        data = fd.read()
        fd.close()
        return data
    
    #---------------------------------------------------

    def list(self,is_profiles):
        if is_profiles:
            data = self.get_profiles_xmlrpc()
        else:
            data = self.get_systems_xmlrpc()
        for x in data:
            if x.has_key("name"):
                print x["name"]
        return True

    #---------------------------------------------------

    def display(self):
        def after_download(self, profile_data):
            # DEBUG
            print profile_data
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
            k_args = self.safe_load(profile_data,'kernel_options',default='')
            k_args = k_args + " ks=file:ks.cfg"

            kickstart = self.safe_load(profile_data,'kickstart')

            self.build_initrd(
                self.safe_load(profile_data,'initrd_local'),
                kickstart,
                profile_data
            )

            if self.autonet is not None:
                k_args = k_args + ' ' + self.get_netconfig(kickstart)

            if len(k_args) > 255:
                raise InfoException, "Kernel options are too long, 255 chars exceeded: %s" % k_args


            k_args = k_args.replace("lang ","lang= ")

            cmd = [ "/sbin/grubby",
                    "--add-kernel", self.safe_load(profile_data,'kernel_local'),
                    "--initrd", self.safe_load(profile_data,'initrd_local'),
                    "--make-default",
                    "--title", "kick%s" % int(time.time()),
                    "--args", k_args,
                    "--copy-default"
            ]
            if self.live_cd:
               cmd.append("--bad-image-okay")
               cmd.append("--boot-filesystem=/dev/sda1")
               cmd.append("--config-file=/tmp/boot/boot/grub/grub.conf")
            self.subprocess_call(cmd)


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

            print "- reboot to apply changes"


        return self.net_install(after_download)

    #---------------------------------------------------

    def get_kickstart_data(self,kickstart,data):
        """
        Get contents of data in network kickstart file.
        """
        return self.urlread(kickstart)

    #---------------------------------------------------

    def get_insert_script(self,initrd):
        """
        Create bash script for inserting kickstart into initrd.
        Code heavily borrowed from internal auto-ks scripts.
        """
        return """
        cd /var/spool/koan
        mkdir initrd
        gzip -dc %s > initrd.tmp
        if file initrd.tmp | grep "filesystem data" >& /dev/null; then
            mount -o loop -t ext2 initrd.tmp initrd
            cp ks.cfg initrd/
            ln initrd/ks.cfg initrd/tmp/ks.cfg
            umount initrd
            gzip -c initrd.tmp > initrd_final
        else
            echo "cpio"
            cat initrd.tmp | (
               cd initrd ; \
               cpio -id ; \
               cp /var/spool/koan/ks.cfg . ; \
               ln ks.cfg tmp/ks.cfg ; \
               find . | \
               cpio -c -o | gzip -9 ) \
            > initrd_final
            echo "done"
        fi
        """ % initrd

    #---------------------------------------------------

    def build_initrd(self,initrd,kickstart,data):
        """
        Crack open an initrd and install the kickstart file.
        """

        # save kickstart to file
        ksdata = self.get_kickstart_data(kickstart,data)
        fd = open("/var/spool/koan/ks.cfg","w+")
        if ksdata is not None:
            fd.write(ksdata)
        fd.close()

        # handle insertion of kickstart based on type of initrd
        fd = open("/var/spool/koan/insert.sh","w+")
        fd.write(self.get_insert_script(initrd))
        fd.close()
        self.subprocess_call([ "/bin/bash", "/var/spool/koan/insert.sh" ])
        shutil.copyfile("/var/spool/koan/initrd_final", initrd)

    #---------------------------------------------------
    def get_netconfig_from_running_system(self):
        """
        Get the network configuration from the running system (as opposed
        to config files, which are distribution-specific).  This isn't going to
        be 100% correct on multi-homed machines, but should work in 98% of the
        sane cases in the wild.
        """
        ret = dict()

        # get the hostname from the system
        ret['hostname'] = socket.gethostname()
        try:
            ret['ip'] = socket.gethostbyname( ret['hostname'] )
        except:
            # ignore the error, but still print the trace
            traceback.print_exc()

        if ret.has_key('ip'):
            iface = self.get_local_interface( ip=ret['ip'] )
            if iface is not None: ret.update(**iface)
        else:
            iface = self.get_local_interface()
            if iface is not None: ret.update(**iface)

        # if cobbler knows about this system, prefer cobbler's data
        if self.system is not None and (ret.has_key('mac') or ret.has_key('ip') or ret.has_key('hostname')):
            try:
                systems = self.get_systems_xmlrpc()

                for system in systems:
                    if ret.has_key('mac') and system['mac_address'].upper() == ret['mac'].upper():
                        ret.update(system)
                        break
                    if ret.has_key('ip') and system['ip_address'] == ret['ip']:
                        ret.update(system)
                        break
                    if ret.has_key('hostname') and system['hostname'] == ret['hostname']:
                        ret.update(system)
                        break
            except:
                # ignore the error, but still print the trace
                traceback.print_exc()

        # get the first nameserver configured on the local system
        fd = open("/etc/resolv.conf", "r")
        for line in fd.readlines():
            if line.startswith('nameserver'):
                ret['nameserver'] = line.split()[1]
                break
        fd.close()

        return ret

    def get_netconfig_from_kickstart(self,kickstart):
        """
        Scan the kickstart configuration for a network --bootproto static line.
        """
        ret = dict()
        lines = []

        if os.path.exists("/var/spool/koan/ks.cfg"):
            fd = open("/var/spool/koan/ks.cfg", "r")
            lines = fd.readlines()
            fd.close()
        else: 
            ksdata = self.get_kickstart_data(kickstart,None)
            lines = ksdata.splitlines()

        network_re = re.compile('\s*network\s+--')
        for line in lines:
            if network_re.match(line):
                p = opt_parse.OptionParser()
                p.add_option("--bootproto",  dest="bootproto")
                p.add_option("--ip",         dest="ip")
                p.add_option("--netmask",    dest="netmask")
                p.add_option("--gateway",    dest="gateway")
                p.add_option("--hostname",   dest="hostname")
                p.add_option("--nameserver", dest="nameserver")
                # ignored, but required for clean parsing
                p.add_option("--device",     dest="device")
                p.add_option("--onboot",     dest="onboot")
                p.add_option("--nodns",      dest="nodns")
                (options,args) = p.parse_args( line.split()[1:] )

                if options.bootproto and options.bootproto == 'static':
                    ret['ip']         = options.ip
                    ret['netmask']    = options.netmask
                    ret['gateway']    = options.gateway
                    ret['hostname']   = options.hostname
                    ret['nameserver'] = options.nameserver

                break
        return ret

    def get_netconfig(self,kickstart):
        """
        If this is a --replace-self run, get the running network configuration and
        put it on the kernel command line so DHCP isn't required.

        If it's a new kickstart, check the kickstart for a static network
        configuration and push that into the kernel command line.
        """
        kargs      = ""
        netconf = {
            'hostname':   None,
            'ip':         None,
            'netmask':    None,
            'nameserver': None,
            'gateway':    None
        }

        if self.is_replace:
            conf = self.get_netconfig_from_running_system()
            if conf is not None: netconf.update( conf )

        # Always try to get the network configuration kickstart.  This will
        # override anything set in the 'if self.is_replace' block above.
        ksconf = self.get_netconfig_from_kickstart(kickstart)
        if ksconf is not None: netconf.update( ksconf )
 
        if netconf['ip'] is not None:
            kargs = kargs + " ip=%s" % netconf['ip']
        if netconf['netmask'] is not None:
            kargs = kargs + " netmask=%s" % netconf['netmask']
        if netconf['hostname'] is not None:
            kargs = kargs + " hostname=%s" % netconf['hostname']
        if netconf['nameserver'] is not None:
            kargs = kargs + " nameserver=%s" % netconf['nameserver']
        if netconf['gateway'] is not None:
            kargs = kargs + " gateway=%s" % netconf['gateway']

        return kargs

    #---------------------------------------------------

    def connect_fail(self):
        raise InfoException, "Could not communicate with %s:%s" % (self.server, self.port)

    #---------------------------------------------------

    def get_profiles_xmlrpc(self):
        try:
            data = self.xmlrpc_server.get_profiles()
        except:
            traceback.print_exc()
            self.connect_fail()
        if data == {}:
            raise InfoException("No profiles found on cobbler server")
        return data

    #---------------------------------------------------

    def get_profile_xmlrpc(self,profile_name):
        """
        Fetches profile yaml from a from a remote bootconf tree.
        """
        try:
            data = self.xmlrpc_server.get_profile_for_koan(profile_name)
        except:
            traceback.print_exc()
            self.connect_fail()
        if data == {}:
            raise InfoException("no cobbler entry for this profile")
        return data

    #---------------------------------------------------

    def get_systems_xmlrpc(self):
        try:
            return self.xmlrpc_server.get_systems()
        except:
            traceback.print_exc()
            self.connect_fail()

    #---------------------------------------------------

    def get_local_interface(self,ip=None,mac=None,iface=None,want_all=None):
        """
        Fetches interfaces, macs, ips, netmask (in cidr notation), and optionally
        default route using iproute2.

        The default is to return a best-guess of the primary interface on the
        system.   If a system is hooked up with a default route, it will be chosen.
        Otherwise, eth0 is preferred.   After that, the "most configured" interface
        will be returned.  If no appropriate-looking interfaces are found, None will
        be returned.

        Options:
            ip: specify an ip to search for, return only that interface
            mac: sepcify a mac to search for, return only that interface
            iface: return only the specified interface
            want_all: (boolean) return all information in a dict

        """
        interfaces = dict()
        iface_re = re.compile('\d+: ([a-z]+[0-9]+): <.*> mtu \d+', re.IGNORECASE)
    
        mac_re = re.compile('.*link/ether ([a-z0-9:]{17}) ', re.IGNORECASE)
        if mac is not None:
            mac_re = re.compile('.*link/ether (%s) ' % mac, re.IGNORECASE)
    
        ip_re = re.compile('.*inet ([\.0-9]+)/(\d+) ')
        if ip is not None:
            ip_re = re.compile('.*inet (%s)/(\d+) ' % ip)
    
        sys_iface = None
        fd = os.popen("/sbin/ip address show")
        for line in fd.readlines():
            mac_match   = mac_re.match(line)
            iface_match = iface_re.match(line)
            ip_match    = ip_re.match(line)
    
            if iface_match:
                sys_iface = iface_match.group(1)
                interfaces[sys_iface] = { 'iface': sys_iface }
            if mac_match and sys_iface:
                interfaces[sys_iface]['mac'] = mac_match.group(1)
            if ip_match and sys_iface:
                interfaces[sys_iface]['ip']      = ip_match.group(1)
                interfaces[sys_iface]['netmask_int'] = ip_match.group(2)
                interfaces[sys_iface]['netmask'] = self.netmask_i2dq( ip_match.group(2) )
    
        fd.close()
    
        # get the default route
        fd = os.popen("/sbin/ip route show")
        for line in fd.readlines():
            if line.startswith('default via '):
                parts = line.split()
                interfaces[parts[4]]['gateway'] = parts[2]
                break
        fd.close()
    
        if want_all is not None:
            return interfaces
        elif mac:
            for i in interfaces.values():
                if i.has_key('mac') and i['mac'] == mac: return i
        elif ip:
            for i in interfaces.values():
                if i.has_key('ip') and i['ip'] == ip: return i
        elif iface:
            # this can and should throw an error if the interface doesn't exist
            return interfaces[iface]
        else:
            ret = None
    
            # but even more likely, we want the device the default route is on
            for i in interfaces.values():
                if i.has_key('gateway'): ret = i

            if ret is None:
                for i in interfaces.values():
                    if i.has_key('ip') and i.has_key('mac'): ret = i

            # eth0 is the most likely cnadidate
            if ret is None and interfaces.has_key('eth0'):
                ret = interfaces['eth0']
    
            return ret

    def netmask_i2dq(self,nm):
        """
        Convert a netmask from integer to dotted-quad notation.
        """
        intval = 0xffffffff << (32 - int(nm))
        ret = "%u.%u.%u.%u" % ((intval >> 24) & 0x000000ff,
                              ((intval & 0x00ff0000) >> 16),
                              ((intval & 0x0000ff00) >> 8),
                               (intval & 0x000000ff))
        return ret

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

    def get_system_xmlrpc(self,system_name):
        """
        If user specifies --system, return the profile data
        but use the system kickstart and kernel options in place
        of what was specified in the system's profile.
        """
        system_data = None
        try:
            system_data = self.xmlrpc_server.get_system_for_koan(system_name)
        except:
            traceback.print_exc()
            self.connect_fail()
        if system_data == {}:
            raise InfoException("no cobbler entry for system")        
        return system_data

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
            self.urlgrab(initrd,initrd_save)
            print "downloading kernel %s to %s" % (kernel_short, kernel_save)

            print "url=%s" % kernel
            self.urlgrab(kernel,kernel_save)
        except:
            raise InfoException, "error downloading files"
        profile_data['kernel_local'] = kernel_save
        profile_data['initrd_local'] = initrd_save

    #---------------------------------------------------

    def calc_kernel_args(self, pd):
        kickstart = self.safe_load(pd,'kickstart')
        options   = self.safe_load(pd,'kernel_options',default='')

        if self.autonet is not None:
            options = options + ' ' + self.get_netconfig(kickstart)

        kextra    = ""
        if kickstart != "":
            kextra = kextra + "ks=" + kickstart
        if kickstart != "" and options !="":
            kextra = kextra + " "
        if options != "":
            kextra = kextra + options
        # parser issues?  lang needs a trailing = and somehow doesn't have it.
        kextra = kextra.replace("lang ","lang= ")

        return kextra

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
                fullvirt      =  fullvirt      
        )

        print "Kernel arguments: %s" % kextra
        print results
        return results

    #---------------------------------------------------

    def load_virt_modules(self):
        try:
            import xencreate
            import qcreate
        except:
            raise InfoException("no virtualization support available, install python-virtinst?")

    #---------------------------------------------------

    def virt_choose(self, pd):
        fullvirt = False
        if self.virt_type in [ "xenpv", "xenfv" ]:
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
        else:
            raise InfoException, "Unspecified virt type: %s" % self.virt_type
        return (uuid, creator, False)

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

    #---------------------------------------------------

    #def random_mac(self):
    #    """
    #    from xend/server/netif.py
    #    Generate a random MAC address.
    #    Uses OUI 00-16-3E, allocated to
    #    Xensource, Inc.  Last 3 fields are random.
    #    return: MAC address string
    #    """
    #    mac = [ 0x00, 0x16, 0x3e,
    #        random.randint(0x00, 0x7f),
    #        random.randint(0x00, 0xff),
    #        random.randint(0x00, 0xff) ]
    #    return ':'.join(map(lambda x: "%02x" % x, mac))


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
           else:
               prefix = "/var/lib/vmware/images/"
           if not os.path.exists(prefix):
               print "- creating: %s" % prefix # DEBUG
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
                return "/dev/mapper/%s-%s" % (location,name.replace('-','--'))
            else:
                raise InfoException, "volume group [%s] needs %s GB free space." % virt_size


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
