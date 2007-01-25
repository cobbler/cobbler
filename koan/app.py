"""
koan = kickstart over a network

a tool for network provisioning of virtualization and network re-provisioning
of existing Linux systems.  used with 'cobbler'. see manpage for usage.

Copyright 2006 Red Hat, Inc.
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import yaml          # Howell-Evans version
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
import virtcreate

"""
koan --virt [--profile=webserver|--system=name] --server=hostname
koan --replace-self --profile=foo --server=hostname
"""

def main():
    """
    Command line stuff...
    """
    p = optparse.OptionParser()
    p.add_option("-l", "--list-profiles",
                 dest="list_profiles",
                 action="store_true",
                 help="list profiles the server can provision")
    p.add_option("-L", "--list-systems",
                 dest="list_systems",
                 action="store_true",
                 help="list systems the server can provision")
    p.add_option("-x", "--xen",
                 dest="is_virt",
                 action="store_true",
                 help="alias for --virt")
    p.add_option("-v", "--virt",
                 dest="is_virt",
                 action="store_true",
                 help="requests new virtualized image installation")
    p.add_option("-r", "--replace-self",
                 dest="is_auto_kickstart",
                 action="store_true",
                 help="requests re-provisioning of this host")
    p.add_option("-p", "--profile",
                 dest="profile",
                 help="cobbler profile to install")
    p.add_option("-y", "--system",
                 dest="system",
                 help="cobbler system to install")
    p.add_option("-s", "--server",
                 dest="server",
                 help="specify the cobbler server")
    p.add_option("-q", "--quiet",
                 dest="verbose",
                 action="store_false",
                 help="run (more) quietly")
    (options, args) = p.parse_args()

    full_access = 1
    for x in [ "/etc", "/boot", "/var/spool"]:
        if not os.access(x, os.O_RDWR):
            print "Unable to write to %s (which usually means root)" % x
            full_access = 0

    if not full_access:
        return 3

    try:
        k = Koan()
        k.list_systems      = options.list_systems
        k.list_profiles     = options.list_profiles
        k.server            = options.server
        k.is_virt           = options.is_virt
        k.is_auto_kickstart = options.is_auto_kickstart
        k.profile           = options.profile
        k.system            = options.system
        k.verbose           = options.verbose
        #k.interactive       = options.interactive
        k.run()
    except InfoException, ie:
        print str(ie)
        return 1
    except virtcreate.VirtCreateException, xce:
        print str(xce)
        return 2
    except:
        traceback.print_exc()
        return 3
    return 0


class InfoException(exceptions.Exception):
    """
    Custom exception for tracking of fatal errors.
    """
    pass

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
        self.verbose           = None
        self.is_virt           = None
        self.is_auto_kickstart = None
        self.dryrun            = None
        # self.interactive       = False

    def run(self):
        if self.server is None:
            raise InfoException, "no server specified"
        if self.list_systems:
            self.do_list_systems()
        if self.list_profiles:
            self.do_list_profiles()
        if (self.list_systems or self.list_profiles):
            return
        if not self.is_virt and not self.is_auto_kickstart:
            raise InfoException, "must use either --virt or --replace-self"
        if self.is_virt and self.is_auto_kickstart:
            raise InfoException, "must use either --virt or --replace-self"
        if not self.server:
            raise InfoException, "no server specified"
        if self.verbose is None:
            self.verbose = True
        if (not self.profile and not self.system):
            raise InfoException, "must specify --profile or --system"
        if self.profile and self.system:
            raise InfoException, "--profile and --system are exclusive"
        if self.is_virt:
            self.do_virt()
        else:
            self.do_auto_kickstart()

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

    def urlgrab(self,url,saveto):
        """
        like urlread, but saves contents to disk.
        see comments for urlread as to why it's this way.
        """
        data = self.urlread(url)
        fd = open(saveto, "w+")
        fd.write(data)
        fd.close()

    def debug(self,msg):
        """
        Debug print if verbose is set.
        """
        if self.verbose:
            print "- %s" % msg
        return msg

    def mkdir(self,path):
        """
        A more verbose and tolerant mkdir
        """
        self.debug("mkdir: %s" % path)
        try:
            os.mkdir(path)
        except OSError, (err, msg):
            if err != errno.EEXIST:
                raise OSError(errno,msg)

    def rmtree(self,path):
        """
        A more verbose and tolerant rmtree
        """
        self.debug("removing: %s" % path)
        try:
            shutil.rmtree(path)
        except OSError, (err, msg):
            if err != errno.ENOENT:
                raise OSError(errno,msg)

    def copyfile(self,src,dest):
        """
        A more verbose copyfile
        """
        self.debug("copying %s to %s" % (src,dest))
        return shutil.copyfile(src,dest)

    def subprocess_call(self,cmd,fake_it=False,ignore_rc=False):
        """
        Wrapper around subprocess.call(...)
        """
        self.debug(cmd)
        if fake_it:
            self.debug("(SIMULATED)")
            return 0
        rc = sub_process.call(cmd)
        if rc != 0 and not ignore_rc:
            raise InfoException, "command failed (%s)" % rc
        return rc

    def safe_load(self,hash,primary_key,alternate_key=None,default=None):
        if hash.has_key(primary_key): 
            return hash[primary_key]
        elif alternate_key is not None and hash.has_key(alternate_key):
            return hash[alternate_key]
        else:
            return default

    def do_net_install(self,download_root,after_download):
        """
        Actually kicks off downloads and auto-ks or virt installs
        """
        self.debug("processing profile: %s" % self.profile)
        if self.profile:
            profile_data = self.get_profile_yaml(self.profile)
        else:
            profile_data = self.get_system_yaml(self.system)
        self.debug(profile_data)
        if not 'distro' in profile_data:
            raise InfoException, "invalid response from boot server"
        distro = self.safe_load(profile_data,'distro')
        distro_data = self.get_distro_yaml(distro)
        self.debug(distro_data)
        self.get_distro_files(distro_data, download_root)
        after_download(self, distro_data, profile_data)

    def do_list_profiles(self):
        return self.do_list(True)

    def do_list_systems(self):
        return self.do_list(False)

    def url_read(self,url):
        fd = urllib2.urlopen(url)
        data = fd.read()
        fd.close()
        return data

    def do_list(self,is_profiles):
        if is_profiles:
           urlseg = "profile_list"
           what = "profiles"
        else:
           urlseg = "system_list"
           what = "systems"
        print "listing defined %s..." % what
        data = None
        try:
            url = "http://%s/cobbler/%s" % (self.server, urlseg)
            self.debug("url=%s" % url)
            # FIXME
            data = self.urlread(url)
            data = yaml.load(data).next() # first record
            data = data.sort()
            for x in data:
                print "%s" % x
            return True
        except:
            raise InfoException, "couldn't access listing information"
        return False # shouldn't be here
                 
    def do_virt(self):
        """
        Handle virt provisioning.
        """
        def after_download(self, distro_data, profile_data):
            self.do_virt_net_install(profile_data, distro_data)
        return self.do_net_install("/tmp",after_download)

    def do_auto_kickstart(self):
        """
        Handle morphing an existing system through downloading new
        kernel, new initrd, and installing a kickstart in the initrd,
        then manipulating grub.
        """
        self.rmtree("/var/spool/koan")
        self.mkdir("/var/spool/koan")

        def after_download(self, distro_data, profile_data):
            if not os.path.exists("/sbin/grubby"):
                raise InfoException, "grubby is not installed"
            k_args = self.safe_load(distro_data,'kernel_options')
            k_args = k_args + " ks=file:ks.cfg"
            self.build_initrd(
                self.safe_load(distro_data,'initrd_local'), 
                self.safe_load(profile_data,'kickstart')
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
                    "--add-kernel", self.safe_load(distro_data,'kernel_local'),
                    "--initrd", self.safe_load(distro_data,'initrd_local'),
                    "--make-default",
                    "--title", "kick%s" % int(time.time()),
                    "--args", k_args,
                    "--copy-default"
            ]
            self.subprocess_call(cmd, fake_it=self.dryrun)

            if loader == "--lilo":
                print "- applying lilo changes"
                cmd = [ "/sbin/lilo" ]
                sub_process.Popen(cmd, stdout=sub_process.PIPE).communicate()[0]

            self.debug("reboot to apply changes")
        return self.do_net_install("/boot",after_download)

    def get_kickstart_data(self,kickstart):
        """
        Get contents of data in network kickstart file.
        """
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
            self.debug("urlread %s" % kickstart)
            try:
                # FIXME
                inf = self.urlread(kickstart)
            except:
                raise InfoException, "Couldn't download: %s" % kickstart
            return inf
        else:
            raise InfoException, "invalid kickstart URL"

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

    def build_initrd(self,initrd,kickstart):
        """
        Crack open an initrd and install the kickstart file.
        """

        # save kickstart to file
        ksdata = self.get_kickstart_data(kickstart)
        fd = open("/var/spool/koan/ks.cfg","w+")
        if ksdata is not None:
            fd.write(ksdata)
        fd.close()

        # handle insertion of kickstart based on type of initrd
        fd = open("/var/spool/koan/insert.sh","w+")
        fd.write(self.get_insert_script(initrd))
        fd.close()
        self.subprocess_call([ "/bin/bash", "/var/spool/koan/insert.sh" ])
        self.copyfile("/var/spool/koan/initrd_final", initrd)

    def get_profile_yaml(self,profile_name):
        """
        Fetches profile yaml from a from a remote bootconf tree.
        """
        self.debug("fetching configuration for profile: %s" % profile_name)
        try:
            url = "http://%s/cobbler/profiles/%s" % (self.server,profile_name)
            self.debug("url=%s" % url)
            # FIXME
            data = self.urlread(url)
            return yaml.load(data).next() # first record
        except:
            raise InfoException, "couldn't download profile information: %s" % profile_name

    def is_ip(self,strdata):
        """
        Is strdata an IP?
        warning: not IPv6 friendly
        """
        if re.search(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}',strdata):
            return True
        return False

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

    def fix_mac(self,strdata):
        """ Make a MAC look PXE-ish """
        return "01-" + "-".join(strdata.split(":")).lower()

    def fix_ip(self,ip):
        """ Make an IP look PXE-ish """
        handle = sub_process.Popen("/usr/bin/gethostip %s" % ip, shell=True, stdout=sub_process.PIPE)
        out = handle.stdout
        results = out.read()
        return results.split(" ")[-1][0:8]

    def pxeify(self,system_name):
        """
        If the input system name is an IP or MAC, make it conform with
        what the app expects.
        """
        if system_name == "default":
            return "default"
        elif self.is_ip(system_name):
            return self.fix_ip(system_name)
        elif self.is_mac(system_name):
            return self.fix_mac(system_name)
        return system_name

    def get_system_yaml(self,system_name):
        """
        If user specifies --system, return the profile data
        but use the system kickstart and kernel options in place
        of what was specified in the system's profile.
        """
        old_system_name = system_name
        system_name = self.pxeify(system_name)
        system_data = None
        self.debug("fetching configuration for system: %s" % old_system_name)
        try:
            url = "http://%s/cobbler/systems/%s" % (self.server,system_name)
            self.debug("url=%s" % url)
            # FIXME 
            data = self.urlread(url)
            system_data = yaml.load(data).next() # first record
        except:
            raise InfoException, "couldn't download profile information: %s" % system_name
        profile_data = self.get_profile_yaml(self.safe_load(system_data,'profile'))
        # system overrides the profile values where relevant
        profile_data.update(system_data)
        # still have to override the kickstart since these are not in the
        # YAML (kickstarts are per-profile but template eval'd for each system)
        try_this = "http://%s/cobbler/kickstarts_sys/%s/ks.cfg" % (self.server,system_name)
        try:
            # can only use a per-system kickstart if it exists.  It may
            # be that the cobbler config file already references a http
            # kickstart, hence the per-system kickstart is just a per
            # profile kickstart, and we can't use it.
            # FIXME
            self.urlread(try_this)
            profile_data['kickstart'] = try_this
        except:
            # just use the profile kickstart, whatever it is
            pass
        print profile_data
        return profile_data

    def get_distro_yaml(self,distro_name):
        """
        Fetches distribution yaml from a remote bootconf tree.
        """
        self.debug("fetching configuration for distro: %s" % distro_name)
        try:
            url = "http://%s/cobbler/distros/%s" % (self.server,distro_name)
            self.debug("url=%s" % url)
            # FIXME
            data = self.urlread(url)
            return yaml.load(data).next() # first record
        except:
            raise InfoException, "couldn't download distro information: %s" % distro_name

    def get_distro_files(self,distro_data, download_root):
        """
        Using distro data (fetched from bootconf tree), determine
        what kernel and initrd to download, and save them locally.
        """
        os.chdir(download_root)
        distro = self.safe_load(distro_data,'name')
        kernel = self.safe_load(distro_data,'kernel')
        initrd = self.safe_load(distro_data,'initrd')
        kernel_short = os.path.basename(kernel)
        initrd_short = os.path.basename(initrd)
        kernel_save = "%s/%s" % (download_root, kernel_short)
        initrd_save = "%s/%s" % (download_root, initrd_short)
        try:
            self.debug("downloading initrd %s to %s" % (initrd_short, initrd_save))
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, initrd_short)
            self.debug("url=%s" % url)
            self.urlgrab(url,initrd_save)
            self.debug("downloading kernel %s to %s" % (kernel_short, kernel_save))
            url = "http://%s/cobbler/images/%s/%s" % (self.server, distro, kernel_short)
            self.debug("url=%s" % url)
            self.urlgrab(url,kernel_save)
        except:
            raise InfoException, "error downloading files"
        distro_data['kernel_local'] = kernel_save
        self.debug("kernel saved = %s" % kernel_save)
        distro_data['initrd_local'] = initrd_save
        self.debug("initrd saved = %s" % initrd_save)

    def do_virt_net_install(self,profile_data,distro_data):
        """
        Invoke virt guest-install (or tweaked copy thereof)
        """
        pd = profile_data
        dd = distro_data

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

        results = virtcreate.start_paravirt_install(
            name=self.calc_virt_name(pd),
            ram=self.calc_virt_ram(pd),
            disk= virtcreate.get_disk(self.calc_virt_filename(pd),
                self.calc_virt_filesize(pd)),
            mac=virtcreate.get_mac(self.calc_virt_mac(pd)),
            uuid=virtcreate.get_uuid(self.calc_virt_uuid(pd)),
            kernel=self.safe_load(dd,'kernel_local'),
            initrd=self.safe_load(dd,'initrd_local'),
            extra=kextra
            # interactive=self.interactive
        )
        print results

    def calc_virt_name(self,data):
        """
        Turn the suggested name into a non-conflicting name.
        Currently this is Xen specific, may change later.
        """
        name = self.safe_load(data,'virt_name','xen_name')
        if name is None or name == "":
            name = self.profile
        path = "/etc/xen/%s" % name
        file_id = 0
        if os.path.exists(path):
            for fid in xrange(1,9999):
                path = "/etc/xen/%s_%s" % (name, fid)
                if not os.path.exists(path):
                    file_id = fid
                    break
        if file_id != 0:
            name = "%s_%s" % (name,file_id)
        data['virt_name'] = name
        return name

    def calc_virt_uuid(self,data):
        # TODO: eventually we may want to allow some koan CLI
        # option for passing in the UUID.  Until then, it's random.
        return None

    def calc_virt_filename(self,data):
        """
        Determine where to store the virtualization file.
        """
        if not os.path.exists("/var/lib/virtimages"):
             try:
                 os.mkdir("/var/lib/virtimages")
             except:
                 pass
        vname = self.safe_load(data,'virt_name','xen_name')
        return os.path.join("/var/lib/virtimages","%s.disk" % vname)

    def calc_virt_filesize(self,data):
        """
        Assign a virt filesize if none is given in the profile.
        """
        size = self.safe_load(data,'virt_file_size','xen_file_size',0)
        err = False
        try:
            int(size)
        except:
            err = True
        if size is None or size == '' or int(size)<1:
            err = True
        if err:
            self.debug("invalid file size specified, defaulting to 1 GB")
            return 1
        return int(size)

    def calc_virt_ram(self,data):
        """
        Assign a virt ram size if none is given in the profile.
        """
        size = self.safe_load(data,'virt_ram','xen_ram',0)
        err = False
        try:
            int(size)
        except:
            err = True
        if size is None or size == '' or int(size) < 256:
            err = True
        if err:
            self.debug("invalid RAM size specified, defaulting to 256 MB")
            return 256
        return int(size)


    def calc_virt_mac(self,data):
        """
        For now, we have no preference.
        """
        if not self.is_virt:
            return None
        if self.is_mac(self.system):
            return self.system.upper()
        return None

if __name__ == "__main__":
    main()
