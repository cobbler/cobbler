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

# the version of cobbler needed to interact with this version of koan
# this is an decimal value (major + 0.1 * minor + 0.01 * maint)
COBBLER_REQUIRED = 0.502

"""
koan --virt [--profile=webserver|--system=name] --server=hostname
koan --replace-self --profile=foo --server=hostname
"""

DISPLAY_PARAMS = [
   "name",
   "distro","profile",
   "kernel","initrd",
   "kernel_options","kickstart","ks_meta",
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
        print "- logging setup failed.  will ignore."

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
    p.add_option("-P", "--virt-path",
                 dest="virt_path",
                 help="virtual install location (see manpage)")  
    p.add_option("-T", "--virt-type",
                 dest="virt_type",
                 help="virtualization install type (xenpv,qemu)")
    p.add_option("-g", "--virt-graphics",
                 action="store_true",
                 dest="virt_graphics",
                 help="enables VNC virt graphics")
    p.add_option("-b", "--virt-bridge",
                 dest="virt_bridge",
                 help="which network bridge to use")

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
        k.live_cd           = options.live_cd
        k.virt_path         = options.virt_path
        k.virt_type         = options.virt_type
        k.virt_graphics     = options.virt_graphics
        k.virt_bridge       = options.virt_bridge
        if options.virt_name is not None:
            k.virt_name          = options.virt_name
        if options.port is not None:
            k.port              = options.port
        k.run()

    except InfoException, ie:
        print str(ie)
        return 1
    except:
        traceback.print_exc()
        return 3
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
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

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
        self.port              = 25151
        self.virt_name         = None
        self.virt_type         = None
        self.virt_path         = None 
        self.virt_graphics     = None
        self.virt_bridge       = None

    #---------------------------------------------------

    def run(self):
        """
        koan's main function...
        """

        # set up XMLRPC connection
        if self.server is None:
                raise InfoException, "no server specified"
        
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
            url = "http://%s:%s" % (server, self.port)
 
            # make a sample call to check for connectivity
            # we use this as opposed to version as version was not
            # in the original API

            try:
                if uses_avahi:
                    print "- attempting to connect to: %s" % server
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

        # check to see that exclusive arguments weren't used together
        # FIXME: these checks can be moved up before the network parts
 
        found = 0
        for x in (self.is_virt, self.is_replace, self.is_display):
            if x:
               found = found+1
        if found != 1:
            raise InfoException, "choose: --virt, --replace-self or --display"

        # if both --profile and --system were ommitted, autodiscover
        # FIXME: can be moved up before the network parts

        if self.is_virt:
            if (self.profile is None and self.system is None):
                raise InfoException, "must specify --profile or --system"
        else:
            if (self.profile is None and self.system is None):
                self.system = self.autodetect_system()


        # if --virt-type was specified and invalid, then fail
        if self.virt_type is not None:
            self.virt_type = self.virt_type.lower()
            if self.virt_type not in [ "qemu", "xenpv", "xen", "auto" ]:
               if self.virt_type == "xen":
                   self.virt_type = "xenpv"
               raise InfoException, "--virttype should be qemu, xenpv, or auto"

        if self.virt_bridge is None and self.is_virt:
            self.virt_bridge = self.autodetect_bridge()

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
	data = self.get_systems_xmlrpc()
	detectedsystem = [system['name'] for system in data if system['mac_address'].upper() == mac.upper()]
	if len(detectedsystem) > 1:
		raise InfoException, "Multiple systems with matching mac addresses"
	elif len(detectedsystem) == 0:
		raise InfoException, "No system matching MAC address %s found" % mac
	elif len(detectedsystem) == 1:
		print "- Auto detected: %s" % detectedsystem[0]
                return detectedsystem[0]

    #---------------------------------------------------

    def autodetect_bridge(self):
        """
        If the user did not specify a --virt-bridge to use
        then try to find bridges that may be useful.  This will
        always be less reliable than using --virt-bridge but
        for many folks they will only have one or they will
        have xenbr0.  This attempts to do the right thing
        for both Xen and qemu/KVM.
        """

        found = None

        # see if the one Xen usually creates is there
        # if there, use it
        cmd = sub_process.Popen("/sbin/ifconfig",shell=True,stdout=sub_process.PIPE)
        data = cmd.communicate()[0]
        if data.find("xenbr0") != -1:
            # commonly found in Xen installs, just use that
            found = "xenbr0"

        # if not, look for one the user might have created according
        # to convention. 
        if found is None:
            for x in range(0,10):
                pattern = "/etc/sysconfig/network-scripts/ifcfg-%s%s" 
                if os.path.exists(pattern % ("eth", x)):
                    if os.path.exists(pattern % ("peth", x)):
                        found = "eth%s" % x
                        break

        # no more places to look, either return it or explain
        # to the user how they can resolve the problem.
        if found is None:
            raise InfoException, "specific --virt-bridge not specified and could not guess which one to use, please see manpage for further instructions."
        else:
            print "- warning: explicit usage of --virt-bridge is recommended"
            print "- trying to use %s as the bridge" % found

        return found

    
    #---------------------------------------------------

    def urlread(self,url):
        """
        to support more distributions, implement (roughly) some 
        parts of urlread and urlgrab from urlgrabber, in ways that
        are less cool and less efficient.
        """
        print "- %s" % url # DEBUG
        fd = urllib2.urlopen(url)
        data = fd.read()
        fd.close()
        return data

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

        # load the data via XMLRPC
        if self.profile:
            profile_data = self.get_profile_xmlrpc(self.profile)
            filler = "kickstarts"
        else:
            profile_data = self.get_system_xmlrpc(self.system)
            filler = "kickstarts_sys"
        if profile_data.has_key("kickstart"):

            # fix URLs
            if profile_data["kickstart"].startswith("/"):
               profile_data["kickstart"] = "http://%s/cblr/%s/%s/ks.cfg" % (profile_data['server'], filler, profile_data['name'])
                
            # find_kickstart source tree in the kickstart file
            raw = self.urlread(profile_data["kickstart"])
            lines = raw.split("\n")
            for line in lines:
               reg = re.compile("--url=(.*)")
               matches = reg.findall(raw)
               if len(matches) != 0:
                   profile_data["install_tree"] = matches[0].strip()


        if self.is_virt and not profile_data.has_key("install_tree"):
            raise InfoException("Unable to find network install source (--url) in kickstart file: %s" % profile_data["kickstart"])

        # find the correct file download location 
        if not self.is_virt:
            download = "/boot"
            if self.live_cd:
                download = "/tmp/boot/boot"

        else:
            # ensure we have a good virt type choice and know where
            # to download the kernel/initrd
            if self.virt_type is None:
                self.virt_type = self.safe_load(profile_data,'virt_type',default=None)
            if self.virt_type is None or self.virt_type == "":
                self.virt_type = "auto"

            # if virt type is auto, reset it to a value we can actually use
            if self.virt_type == "auto":
                # BOOKMARK
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

            if self.virt_type == "xenpv":
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

            # for both virt types
            if os.path.exists("/etc/rc.d/init.d/libvirtd"):
                rc = sub_process.call("/sbin/service libvirtd status", stdout=None, shell=True)
                if rc != 0:
                    # libvirt running?
                    raise InfoException("libvirtd needs to be running")


            if self.virt_type == "xenpv":
                download = "/var/lib/xen" 
            else: # qemu
                download = None # fullvirt, can use set_location in virtinst library, no D/L needed yet

        # download required files
        if not self.is_display and download is not None:
           self.get_distro_files(profile_data, download)
  
        # perform specified action
        after_download(self, profile_data)

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
            for x in DISPLAY_PARAMS:
                if profile_data.has_key(x):
                    print "%20s  : %s" % (x, profile_data[x])
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
            k_args = self.safe_load(profile_data,'kernel_options')
            k_args = k_args + " ks=file:ks.cfg"

            self.build_initrd(
                self.safe_load(profile_data,'initrd_local'),
                self.safe_load(profile_data,'kickstart'),
                profile_data
            )
            k_args = k_args.replace("lang ","lang= ")

            cmd = [ "/sbin/grubby", 
                    "--bootloader-probe" ]

            which_loader = sub_process.Popen(cmd, stdout=sub_process.PIPE).communicate()[0]
 
            loader = "--grub"
            if which_loader.find("elilo") != -1:
                loader = "--elilo"
            elif which_loader.find("lilo") != -1:
                loader = "--lilo"

            cmd = [ "/sbin/grubby",
                    loader,
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

            if loader == "--lilo":
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
        print "- kickstart: %s" % kickstart
        if kickstart is None or kickstart == "":
            return None

        if kickstart.startswith("nfs"):
            ndir  = os.path.dirname(kickstart[6:])
            nfile = os.path.basename(kickstart[6:])
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
        elif kickstart.startswith("http") or kickstart.startswith("ftp"):
            print "- downloading %s" % kickstart
            try:
                return self.urlread(kickstart)
            except:
                raise InfoException, "Couldn't download: %s" % kickstart
        else:
            raise InfoException, "invalid kickstart URL"

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
        try:
            print "downloading initrd %s to %s" % (initrd_short, initrd_save)
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, initrd_short)
            print "url=%s" % url
            self.urlgrab(url,initrd_save)
            print "downloading kernel %s to %s" % (kernel_short, kernel_save)
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, kernel_short)
            print "url=%s" % url
            self.urlgrab(url,kernel_save)
        except:
            raise InfoException, "error downloading files"
        profile_data['kernel_local'] = kernel_save
        profile_data['initrd_local'] = initrd_save

    #---------------------------------------------------

    def calc_kernel_args(self, pd):
        kickstart = self.safe_load(pd,'kickstart')
        options   = self.safe_load(pd,'kernel_options')
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

        arch                = self.safe_load(pd,'arch','x86')
        kextra              = self.calc_kernel_args(pd)
        mac                 = self.calc_virt_mac(pd)
        (uuid, create_func) = self.virt_choose(pd)
        virtname            = self.calc_virt_name(pd,mac)
        ram                 = self.calc_virt_ram(pd)
        vcpus               = self.calc_virt_cpus(pd)
        path_list           = self.calc_virt_path(pd, virtname)
        size_list           = self.calc_virt_filesize(pd)
        disks               = self.merge_disk_data(path_list,size_list)

        results = create_func(
                name          =  virtname,
                ram           =  ram,
                disks         =  disks,
                mac           =  mac,  
                uuid          =  uuid, 
                extra         =  kextra,
                vcpus         =  vcpus,
                virt_graphics =  self.virt_graphics, 
                profile_data  =  profile_data,       
                bridge        =  self.virt_bridge,   
                arch          =  arch         
        )

        print results
        return results

    #---------------------------------------------------

    def load_virt_modules(self):
        try:
            import xencreate
            import qcreate
        except:
            print "no virtualization support available, install python-virtinst?"
            sys.exit(1)

    #---------------------------------------------------

    def virt_choose(self, pd):
        if self.virt_type == "xenpv":
            uuid    = self.get_uuid(self.calc_virt_uuid(pd))
            import xencreate
            creator = xencreate.start_paravirt_install
        elif self.virt_type == "qemu":
            uuid    = None
            import qcreate
            creator = qcreate.start_install
        else:
            raise InfoException, "Unspecified virt type: %s" % self.virt_type
        return (uuid, creator)

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

    def calc_virt_name(self,profile_data,mac):
        if self.virt_name is not None:
           # explicit override
           name = self.virt_name
        elif profile_data.has_key("mac_address"):
           # this is a system object, just use the name
           name = profile_data["name"]
        else:
           # just use the MAC, which we might have generated
           name = mac.upper()
        return name.replace(":","_") # keep libvirt happy


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
        if size is None or size == '' or int(size)<default_filesize:
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
        size = self.safe_load(data,'virt_cpus','xen_cpus',0)
        err = False
        try:
            int(size)
        except:
            err = True
        if size is None or size == '' or int(size) < default_cpus:
            err = True
        if err:
            return int(default_cpus)
        return int(size)

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
        id = self.safe_load(data,'virt_uuid','xen_uuid',0)
        uuid_re = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        err = False
        try:
            str(id)
        except:
            err = True
        if id is None or id == '' or not uuid_re.match(id):
            err = True
        if err and id is not None:
            print "invalid UUID specified.  randomizing..."
            return None
        return id

    #---------------------------------------------------

    def random_mac(self):
        """
        from xend/server/netif.py
        Generate a random MAC address.
        Uses OUI 00-16-3E, allocated to
        Xensource, Inc.  Last 3 fields are random.
        return: MAC address string
        """
        mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) ]
        return ':'.join(map(lambda x: "%02x" % x, mac))


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
           if self.virt_type == "xenpv":
               prefix = "/var/lib/xen/images/"
           elif self.virt_type == "qemu":
               prefix = "/opt/qemu/"
           if not os.path.exists(prefix):
               os.makedirs(prefix)
           return [ "%s/%s" % (prefix, name) ]

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
                return "%s/%s" % (location, name)
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
                return "/dev/mapper/%s-%s" % (location,name)
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
