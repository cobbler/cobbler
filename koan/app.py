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
import optparse
import exceptions
import sub_process
import time
import shutil
import errno
import re
import sys
import xmlrpclib
import string
import qcreate

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

def main():
    """
    Command line stuff...
    """
    p = optparse.OptionParser()
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
                 help="specify virtualization install type (xenpv,qemu)")
    p.add_option("-g", "--virt-graphics",
                 action="store_true",
                 dest="virt_graphics",
                 help="enable virt graphics (varies with --virt-type)")
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

    #---------------------------------------------------

    def run(self):
        """
        koan's main function...
        """

        # set up XMLRPC connection
        if self.server is None:
            raise InfoException, "no server specified"
        url = "http://%s:%s" % (self.server, self.port)
        self.xmlrpc_server = ServerProxy(url)

        # if command line input was just for listing commands,
        # run them now and quit
        if self.list_systems:
            self.list(False)
            return
        if self.list_profiles:
            self.list(True)
            return

        # check to see that exclusive arguments weren't used together
        found = 0
        for x in (self.is_virt, self.is_replace, self.is_display):
            if x:
               found = found+1
        if found != 1:
            raise InfoException, "choose: --virt, --replace-self or --display"

        # if both --profile and --system were ommitted, autodiscover
        if (not self.profile and not self.system):
            self.system = self.autodetect_system()

        # if --virt-type was specified and invalid, then fail
        if self.virt_type is not None:
            if self.virt_type not in [ "qemu", "xenpv" ]:
               raise InfoException, "--virttype should be qemu or xenpv"

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

    def urlread(self,url):
        """
        to support more distributions, implement (roughly) some 
        parts of urlread and urlgrab from urlgrabber, in ways that
        are less cool and less efficient.
        """
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
            if profile_data["kickstart"].startswith("/"):
               profile_data["kickstart"] = "http://%s/cblr/%s/%s/ks.cfg" % (profile_data['server'], filler, profile_data['name'])
       
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
                self.virt_type = 'xenpv'

            if self.virt_type == "xenpv":
                download = "/var/lib/xen" 
            else:
                # FIXME: should use temp dir to allow parallel installs?
                download = "/var/spool/koan" 

        # download required files
        if not self.is_display:
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
            os.mkdir("/var/spool/koan")
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
        print "kernel saved = %s" % kernel_save
        profile_data['initrd_local'] = initrd_save
        print "initrd saved = %s" % initrd_save

    #---------------------------------------------------

    def virt_net_install(self,profile_data):
        """
        Invoke virt guest-install (or tweaked copy thereof)
        """
        pd = profile_data

        kextra = ""
        lkickstart = self.safe_load(pd,'kickstart')
        loptions   = self.safe_load(pd,'kernel_options')
        if lkickstart != "" or loptions != "":
            if lkickstart != "":
                kextra = kextra + "ks=" + lkickstart
            if lkickstart !="" and loptions !="":
                kextra = kextra + " "
            if loptions != "":
                kextra = kextra + loptions

        # parser issues?  lang needs a trailing = and somehow doesn't have it.
        kextra = kextra.replace("lang ","lang= ")

        if self.virt_type == "xenpv":
            try:
                import xencreate
            except:
                print "no virtualization support available, install python-virtinst?"
                sys.exit(1)

        # if the object has a "profile" entry, then it's a system
        # and we pass in the name straight.  If it's not, pass in None
        # for the Name, such that we can use the MAC or the override value.
        pro = self.safe_load(pd,'profile')
        if pro is None or pro == "":
            # this is a system object, use name as entered
            name = self.safe_load(pd,'name')
        else:
            # this is a profile object, use MAC or override value
            name = None

        mac = self.calc_virt_mac(pd)
        if self.virt_type == "xenpv":
            uuid    = xencreate.get_uuid(self.calc_virt_uuid(pd))
            creator = xencreate.start_paravirt_install
        elif self.virt_type == "qemu":
            uuid    = None
            creator = qcreate.start_install
        else:
            raise InfoException, "Unspecified virt type: %s" % self.virt_type

        virtname = self.calc_virt_name(pd,mac)

        results = creator(
                name          =  virtname,
                ram           =  self.calc_virt_ram(pd),
                disk          =  self.calc_virt_filesize(pd),
                mac           =  mac,
                uuid          =  uuid,
                kernel        =  self.safe_load(pd,'kernel_local'),
                initrd        =  self.safe_load(pd,'initrd_local'),
                extra         =  kextra,
                vcpus         =  self.calc_virt_cpus(pd),
                path          =  self.calc_virt_path(pd, virtname),
                virt_graphics =  self.virt_graphics
        )

        print results

    #---------------------------------------------------

    def calc_virt_name(self,profile_data,mac):
        if self.virt_name is not None:
           # explicit override
           return self.virt_name
        if profile_data.has_key("mac_address"):
           # this is a system object, just use the name
           return profile_data["name"]
        # just use the MAC, which we might have generated
        return mac.replace(":","_").upper()

    #---------------------------------------------------

    def calc_virt_filesize(self,data,default_filesize=1):
        """
        Assign a virt filesize if none is given in the profile.
        """
        size = self.safe_load(data,'virt_file_size','xen_file_size',0)
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
            print "invalid number of VCPUS specified, using defaults"
            return default_cpus
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


    #---------------------------------------------------

    def calc_virt_path(self,pd,name):
        """
        Assign virtual disk location.
        """

        # determine if any suggested location info is available
        if self.virt_path is None:
            # no explicit CLI override, what did the cobbler server say?
            location = self.safe_load(pd, 'virt_path', default=None)
        if location is None or location == "":  
            # not set in cobbler either? then assume reasonable defaults
            location = None            
            if location == None:
                if self.virt_type == "xenpv":
                    prefix = "/var/lib/xen/images/"
                elif self.virt_type == "qemu":
                    prefix = "/opt/qemu/"
                if not os.path.exists(prefix):
                    os.makedirs(prefix)
                return "%s/%s" % (prefix, name)

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
            args = "/usr/sbin/lvs --noheadings -o vg_free --units g %s" % location
            print args
            cmd = sub_process.Popen(args, stdout=sub_process.PIPE, shell=True)
            freespace_str = cmd.communicate()[0]
            print freespace_str
            freespace = int(float(freespace_str.strip()[0:-1]))
            virt_size = self.safe_load(data,'virt_file_size','xen_file_size',0)
           
            if freespace >= int(virt_size):
            
                # look for LVM partition named foo, create if doesn't exist
                args = "/usr/sbin/lvs -o lv_name %s" % location
                print "%s" % args
                lvs_str=sub_process.Popen(args, stdout=sub_process.PIPE, shell=True).communicate()[0]
                print lvs_str
          
                # have to create it?
                if not lvs_str.find(name):
                    args = "/usr/sbin/lvcreate -L %sG -n %s %s" % (virt_size, name, location)
                    print "%s" % args
                    lv_create = sub_process.call(args, shell=True)
                    if lv_create != 0:
                        raise InfoException, "LVM creation failed"

                # return partition location
                return "/dev/%s/%s" % (location,name)
            else:
                raise InfoException, "volume group [%s] needs %s GB free space." % virt_size


if __name__ == "__main__":
    main()
