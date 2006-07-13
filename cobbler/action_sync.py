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
import shutil
import yaml
from Cheetah.Template import Template

import utils
import cobbler_msg
import cexceptions

class BootSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.verbose  = True
        self.config   = config
        self.distros  = config.distros()
        self.profiles = config.profiles()
        self.systems  = config.systems()
        self.settings = config.settings()


    def run(self,dryrun=False,verbose=True):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.settings.tftpboot):
            raise cexceptions.CobblerException("no_dir",self.settings.tftpboot)
        self.verbose = verbose
        self.dryrun = dryrun
        self.clean_trees()
        self.copy_pxelinux()
        self.copy_distros()
        self.validate_kickstarts()
        self.configure_httpd()
        self.build_trees()
        return True


    def copy_pxelinux(self):
        """
        Copy syslinux to the configured tftpboot directory
        """
        self.copy(self.settings.pxelinux, os.path.join(self.settings.tftpboot, "pxelinux.0"))

    def configure_httpd(self):
        """
        Create a config file to Apache that will allow access to the
        cobbler infrastructure available over TFTP over HTTP also.
        """
        if not os.path.exists("/etc/httpd/conf.d"):
           self.sync_log(cobbler_msg.lookup("no_httpd"))
           return
        f = self.open_file("/etc/httpd/conf.d/cobbler.conf","w+")
        config_data = """
        #
        # This configuration file allows 'cobbler' boot info
        # to be accessed over HTTP in addition to PXE.
        AliasMatch ^/cobbler(/.*)?$ "/tftpboot$1"
        <Directory "/tftpboot">
            Options Indexes
            AllowOverride None
            Order allow,deny
            Allow from all
        </Directory>
        """
        config_data.replace("/tftpboot",self.settings.tftpboot)
        self.tee(f, config_data)
        self.close_file(f)

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and xen tree info.
        """
        for x in ["pxelinux.cfg","images","systems","distros","profiles","kickstarts","kickstarts_sys"]:
            path = os.path.join(self.settings.tftpboot,x)
            self.rmtree(path)
            self.mkdir(path)

    def copy_distros(self):
        """
        A distro is a kernel and an initrd.  Copy all of them and error
        out if any files are missing.  The conf file was correct if built
        via the CLI or API, though it's possible files have been moved
        since or perhaps they reference NFS directories that are no longer
        mounted.
        """
        # copy is a 4-letter word but tftpboot runs chroot, thus it's required.
        distros = os.path.join(self.settings.tftpboot, "images")
        for d in self.distros:
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
        Koan provisioning (Xen + auto-ks) needs kickstarts
        per profile.  Validate them as needed.  Local kickstarts
        get template substitution.  Since http:// kickstarts might
        get generated via magic URLs, those are *not* substituted.
        NFS kickstarts are also not substituted when referenced
        by NFS URL's as we don't copy those files over to the cobbler
        directories.  They are supposed to be live such that an
        admin can update those without needing to run 'sync' again.
        """

        for g in self.profiles:
           distro = self.distros.find(g.distro)
           self.sync_log(cobbler_msg.lookup("sync_mirror_ks"))
           kickstart_path = utils.find_kickstart(g.kickstart)
           if kickstart_path and os.path.exists(kickstart_path):
              # the input is an *actual* file, hence we have to copy it
              copy_path = os.path.join(
                  self.settings.tftpboot,
                  "kickstarts", # profile kickstarts go here
                  g.name
              )
              self.mkdir(copy_path)
              dest = os.path.join(copy_path, "ks.cfg")
              # FIXME -- uncomment try for now
              #try:
              meta = self.blend_options(False, (
                distro.ks_meta,
                g.ks_meta,
              ))
              self.apply_template(kickstart_path, meta, dest)
              #except:
              #msg = "err_kickstart2" % (g.kickstart,dest)
              #raise cexceptions.CobblerException(msg)

    def validate_kickstarts_per_system(self):
        """
        PXE provisioning needs kickstarts evaluated per system.
        Profiles would normally be sufficient, but not in cases
        such as static IP, where we want to be able to do templating
        on a system basis.

        FIXME: be sure PXE configs reference the new kickstarts_sys path
        instead.
        """

        for s in self.systems:
            profile = self.profiles.find(s.profile)
            distro = self.distros.find(profile.distro)
            kickstart_path = utils.find_kickstart(profile.kickstart)
            if kickstart_path and os.path.exists(kickstart_path):
                pxe_fn = self.get_pxelinux_filename(s.name)
                copy_path = os.path.join(self.settings.tftpboot,
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
                    self.apply_template(kickstart_path, meta, dest)
                except:
                    msg = "err_kickstart2" % (g.kickstart, dest)
                    raise cexpcetions.CobblerException(msg)

    def apply_template(self, kickstart_input, metadata, out_path):
        """
        Take filesystem file kickstart_input, apply metadata using
        Cheetah and save as out_path.
        """
        fd = open(kickstart_input)
        data = fd.read()
        fd.close()
        print metadata # FIXME: temporary
        t = Template(
            "#errorCatcher Echo\n%s" % data,
            searchList=[metadata],
        )
        computed = str(t)
        fd = open(out_path, "w+")
        fd.write(computed)
        fd.close()

    def build_trees(self):
        """
        Now that kernels and initrds are copied and kickstarts are all valid,
        build the pxelinux.cfg tree, which contains a directory for each
        configured IP or MAC address.  Also build a parallel 'xeninfo' tree
        for xen-net-install info.
        """
        self.sync_log(cobbler_msg.lookup("sync_buildtree"))
        # create pxelinux.cfg under tftpboot
        # and file for each MAC or IP (hex encoded 01-XX-XX-XX-XX-XX-XX)

        for d in self.distros:
            self.sync_log(cobbler_msg.lookup("sync_processing") % d.name)
            # TODO: add check to ensure all distros have profiles (=warning)
            filename = os.path.join(self.settings.tftpboot,"distros",d.name)
            d.kernel_options = self.blend_options(True,(
               self.settings.kernel_options,
               d.kernel_options
            ))
            self.write_distro_file(filename,d)

        for p in self.profiles:
            self.sync_log(cobbler_msg.lookup("sync_processing") % p.name)
            # TODO: add check to ensure all profiles have distros (=error)
            # TODO: add check to ensure all profiles have systems (=warning)
            filename = os.path.join(self.settings.tftpboot,"profiles",p.name)
            distro = self.distros.find(p.distro)
            if distro is not None:
                p.kernel_options = self.blend_options(True,(
                   self.settings.kernel_options,
                   distro.kernel_options,
                   p.kernel_options
                ))
            self.write_profile_file(filename,p)

        for system in self.systems:
            self.sync_log(cobbler_msg.lookup("sync_processing") % system.name)
            profile = self.profiles.find(system.profile)
            if profile is None:
                raise cexceptions.CobblerException("orphan_profile2",system.name,system.profile)
            distro = self.distros.find(profile.distro)
            if distro is None:
                raise cexceptions.CobblerException("orphan_distro2",system.profile,profile.distro)
            f1 = self.get_pxelinux_filename(system.name)
            f2 = os.path.join(self.settings.tftpboot, "pxelinux.cfg", f1)
            f3 = os.path.join(self.settings.tftpboot, "systems", f1)
            self.write_pxelinux_file(f2,system,profile,distro)
            self.write_system_file(f3,system)


    def get_pxelinux_filename(self,name_input):
        """
        The configuration file for each system pxelinux uses is either
        a form of the MAC address of the hex version of the IP.  Not sure
        about ipv6 (or if that works).  The system name in the config file
        is either a system name, an IP, or the MAC, so figure it out, resolve
        the host if needed, and return the pxelinux directory name.
        """
        name = utils.find_system_identifier(name_input)
        if utils.is_ip(name):
            return utils.get_host_ip(name)
        elif utils.is_mac(name):
            return "01-" + "-".join(name.split(":")).lower()
        else:
            raise cexceptions.CobblerException("err_resolv", name)


    def write_pxelinux_file(self,filename,system,profile,distro):
        """
        Write a configuration file for the pxelinux boot loader.
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py
        """
        kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        kickstart_path = profile.kickstart
        self.sync_log(cobbler_msg.lookup("writing") % filename)
        self.sync_log("---------------------------------")
        fd = self.open_file(filename,"w+")
        self.tee(fd,"default linux\n")
        self.tee(fd,"prompt 0\n")
        self.tee(fd,"timeout 1\n")
        self.tee(fd,"label linux\n")
        self.tee(fd,"   kernel %s\n" % kernel_path)
        kopts = self.blend_options(True,(
           self.settings.kernel_options,
           profile.kernel_options,
           distro.kernel_options,
           system.kernel_options
        ))
        nextline = "   append %s initrd=%s" % (kopts,initrd_path)
        if kickstart_path is not None and kickstart_path != "":
            # if kickstart path is on disk, we've already copied it into
            # the HTTP mirror, so make it something anaconda can get at
            if kickstart_path.startswith("/"):
                pxe_fn = self.get_pxelinux_filename(system.name)
                kickstart_path = "http://%s/cobbler/kickstarts_sys/%s/ks.cfg" % (self.settings.server, pxe_fn)
            nextline = nextline + " ks=%s" % kickstart_path
        self.tee(fd, nextline)
        self.close_file(fd)
        self.sync_log("--------------------------------")


    def write_distro_file(self,filename,distro):
        """
        Create distro information for xen-net-install
        """
        fd = self.open_file(filename,"w+")
        # resolve to current values
        distro.kernel = utils.find_kernel(distro.kernel)
        distro.initrd = utils.find_initrd(distro.initrd)
        self.tee(fd,yaml.dump(distro.to_datastruct()))
        self.close_file(fd)


    def write_profile_file(self,filename,profile):
        """
        Create profile information for xen-net-install
        """
        fd = self.open_file(filename,"w+")
        # if kickstart path is local, we've already copied it into
        # the HTTP mirror, so make it something anaconda can get at
        if profile.kickstart and profile.kickstart.startswith("/"):
            profile.kickstart = "http://%s/cobbler/kickstarts/%s/ks.cfg" % (self.settings.server, profile.name)
        self.tee(fd,yaml.dump(profile.to_datastruct()))
        self.close_file(fd)


    def write_system_file(self,filename,system):
        """
        Create system information for xen-net-install
        """
        fd = self.open_file(filename,"w+")
        self.tee(fd,yaml.dump(system.to_datastruct()))
        self.close_file(fd)

    def tee(self,fd,text):
        """
        For dryrun support:  send data to screen and potentially to disk
        """
        self.sync_log(text)
        if not self.dryrun:
            fd.write(text)

    def open_file(self,filename,mode):
        """
        For dryrun support:  open a file if not in dryrun mode.
        """
        if self.dryrun:
            return None
        return open(filename,mode)

    def close_file(self,fd):
        """
	For dryrun support:  close a file if not in dryrun mode.
	"""
        if not self.dryrun:
            fd.close()

    def copyfile(self,src,dst):
       """
       For dryrun support:  potentially copy a file.
       """
       self.sync_log(cobbler_msg.lookup("copying") % (src,dst))
       if self.dryrun:
           return True
       try:
           return shutil.copyfile(src,dst)
       except IOError, ioe:
           raise cexceptions.CobblerException("need_perms2",src,dst)


    def copy(self,src,dst):
       """
       For dryrun support: potentially copy a file.
       """
       self.sync_log(cobbler_msg.lookup("copying") % (src,dst))
       if self.dryrun:
           return True
       try:
           return shutil.copy(src,dst)
       except IOError, ioe:
           raise cexceptions.CobblerException("need_perms2",src,dst)

    def rmtree(self,path):
       """
       For dryrun support:  potentially delete a tree.
       """
       self.sync_log(cobbler_msg.lookup("removing") % (path))
       if self.dryrun:
           return True
       try:
           return shutil.rmtree(path)
       except OSError, ioe:
           if not ioe.errno == 2: # already exists
               raise cexceptions.CobblerException("no_delete",path)

    def mkdir(self,path,mode=0777):
       """
       For dryrun support:  potentially make a directory.
       """
       self.sync_log(cobbler_msg.lookup("mkdir") % (path))
       if self.dryrun:
           return True
       try:
           return os.mkdir(path,mode)
       except:
           raise cexceptions.CobblerException("no_create", path)

    def sync_log(self,message):
       """
       Used to differentiate dryrun output from the real thing
       automagically
       """
       if self.verbose:
           if self.dryrun:
               if not message:
                   message = ""
               print cobbler_msg.lookup("dryrun") % str(message)
           else:
               print message

    def blend_options(self, is_for_kernel, list_of_opts):
        """
        Given a list of options, take the values used by the
        first argument in the list unless overridden by those in the
        second (or further on), according to --key=value formats.

        This is used such that we can have default kernel options
        in /etc and then distro, profile, and system options with various
        levels of configurability overriding them.  This also works
        for template metadata (--ksopts)

        The output when is_for_kernel is true is a space delimited list.
        When is_for_kernel is false, it's just a hash (which Cheetah requires).
        """
        internal = {}
        results = []
        # for all list of kernel options
        for items in list_of_opts:
           # get each option
           tokens=items.split(" ")
           # deal with key/value pairs and single options alike
           for token in tokens:
              key_value = token.split("=")
              if len(key_value) == 1:
                  internal[key_value[0]] = ""
              else:
                  internal[key_value[0]] = key_value[1]
        if not is_for_kernel:
            return internal
        # the kernel requires a flat string for options, and we want
        # to remove certain invalid options.
        # go back through the final list and render the single
        # items AND key/value items
        for key in internal.keys():
           data = internal[key]
           if (key == "ks" or key == "initrd" or key == "append"):
               # the user REALLY doesn't want to do this...
               continue
           if data == "":
               results.append(key)
           else:
               results.append("%s=%s" % (key,internal[key]))
        # end result is a new fragment of an options string
        return " ".join(results)

