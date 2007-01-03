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

import utils
import cobbler_msg
import cexceptions
import traceback
import errno



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
        self.repos    = config.repos()

    def run(self,dryrun=False,verbose=True):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.settings.tftpboot):
            raise cexceptions.CobblerException("no_dir",self.settings.tftpboot)
        # not having a /var/www/cobbler is ok, the app will create it since
        # no other package has to own it.
        self.needs_http_restart = False
        self.verbose = verbose
        self.dryrun = dryrun
        self.clean_trees()
        self.copy_koan()
        self.copy_bootloaders()
        self.copy_distros()
        self.validate_kickstarts()
        self.configure_httpd()
        self.build_trees()
        if self.settings.manage_dhcp:
            self.write_dhcp_file()
            self.restart_dhcp()
        # self.consider_restarting_apache()
        return True

    def restart_dhcp(self):
        try:
            retcode = self.service("dhcpd", "restart")
            if retcode != 0:
                print >>sys.stderr, "Warning: dhcpd restart failed"
        except OSError, e:
            print >>sys.stderr, "Warning: dhcpd restart failed: ", e

    def copy_koan(self):
        koan_path = self.settings.koan_path
        print "koan path = %s" % koan_path
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
            print "loader path = %s" % path
            newname = os.path.basename(path)
            print "loader new name = %s" % newname
            destpath = os.path.join(self.settings.tftpboot, newname)
            print "destpath = %s" % destpath
            self.copyfile(path, destpath)

    def write_dhcp_file(self):

        try:
            f2 = open("/etc/cobbler/dhcp.template","r")
        except:
            raise cexceptions.CobblerException("exc_no_template")
        template_data = ""
        f1 = self.open_file("/etc/dhcpd.conf","w+")
        template_data = f2.read()
        f2.close()

        # build each per-system definition
        system_definitions = ""
        counter = 0
        elilo = os.path.basename(self.settings.bootloaders["ia64"])
        for system in self.systems:
            if not utils.is_mac(system.name):
                # can't do per-system dhcp features if the system
                # hostname is not a MAC, therefore the templating
                # gets to be pretty lame.  The general rule here is
                # if you want to PXE IA64 boxes, you need to use
                # the MAC as the system name.
                continue
            systxt = ""
            counter = counter + 1
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
            system_definitions = system_definitions + systxt

        metadata = {
           "insert_cobbler_system_definitions" : system_definitions,
           "date" : time.asctime(time.gmtime()),
           "next_server" : self.settings.next_server
        }
        for x in metadata.keys():
            template_data = template_data.replace("$%s" % x, metadata[x])
        self.tee(f1,template_data)
        self.close_file(f1)

    def configure_httpd(self):
        """
        Create a config file to Apache that will allow access to the
        cobbler infrastructure available over TFTP over HTTP also.
        """
        
        conf_file = "/etc/httpd/conf.d/cobbler.conf"
        self.needs_http_restart = True

        if not os.path.exists("/etc/httpd/conf.d"):
           print cobbler_msg.lookup("no_httpd")
           return

        # now we're going to figure out whether we actually need to write
        # the file.  If the file exists and contains self.settings.webdir,
        # then we don't.  and if the file is already there, then we really
        # don't have to restart the service either.

        if os.path.exists(conf_file):
            fh = open(conf_file, "r")
            data = fh.read()
            if data.find(self.settings.webdir) != -1:
                self.needs_http_restart=False
            fh.close()

        if not self.needs_http_restart:
            return

        f = self.open_file(conf_file,"w+")
        config_data = """
        #
        # This configuration file allows 'cobbler' boot info
        # to be accessed over HTTP in addition to PXE.
        AliasMatch ^/cobbler(/.*)?$ "/cobbler_webdir$1"
        <Directory "/cobbler_webdir">
            Options Indexes FollowSymLinks
            AllowOverride None
            Order allow,deny
            Allow from all
            AddHandler mod_python .py
            PythonOutputFilter watcher WATCHER
            AddOutputFilter WATCHER ks.cfg
            AddOutputFilter WATCHER .rpm
            AddOutputFilter WATCHER .xml
            AddOutputFilter WATCHER initrd.img
            AddOutputFilter WATCHER vmlinuz
            AddOutputFilter WATCHER .py
            PythonDebug On
        </Directory>
        """
        # this defaults to /var/www/cobbler if user didn't change it
        config_data = config_data.replace("/cobbler_webdir",self.settings.webdir)
        self.tee(f, config_data)
        self.close_file(f)

        if self.needs_http_restart:
            self.service("httpd", "reload")

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and virt tree info.

        Note: for SELinux reasons, some information goes in /tftpboot, some in /var/www/cobbler
        and some must be duplicated in both.  This is because PXE needs tftp, and auto-kickstart
        and Virt operations need http.   Only the kernel and initrd images are duplicated, which is
        unfortunate, though SELinux won't let me give them two contexts, so symlinks are not
        a solution.  *Otherwise* duplication is minimal.
        """

        # clean out all of /tftpboot
        for x in os.listdir(self.settings.webdir):
            path = os.path.join(self.settings.webdir,x)
            if os.path.isfile(path):
                if not x.endswith(".py"):
                    self.rmfile(path)
            if os.path.isdir(path):
                if not x in ["localmirror","repo_mirror","ks_mirror"] :
                    # new versions of cobbler use repo_mirror for repos and ks_mirror for
                    # basic kickstart tree core data.  older versions just used "local_mirror" so we
                    # do have to leave the "localmirror" in there to avoid breaking users on upgrades
                    self.rmtree(path)
        self.rmtree(os.path.join(self.settings.tftpboot, "pxelinux.cfg"))
        self.rmtree(os.path.join(self.settings.tftpboot, "images"))
        self.rmfile(os.path.join(self.settings.tftpboot, "pxelinux.0"))
        self.rmfile(os.path.join(self.settings.tftpboot, "elilo-3.6-ia64.efi"))

        # make some directories in /tftpboot
        for x in ["pxelinux.cfg","images"]:
            path = os.path.join(self.settings.tftpboot,x)
            self.mkdir(path)

        # make some directories in /var/www/cobbler
        for x in ["systems","distros","profiles","kickstarts","kickstarts_sys","images"]:
            path = os.path.join(self.settings.webdir, x)
            self.mkdir(path)

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
        for dirtree in [self.settings.tftpboot, self.settings.webdir]:
            distros = os.path.join(dirtree, "images")
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
           distro = self.distros.find(g.distro)
           kickstart_path = utils.find_kickstart(g.kickstart)
           if kickstart_path and os.path.exists(kickstart_path):
              # the input is an *actual* file, hence we have to copy it
              copy_path = os.path.join(
                  self.settings.webdir,
                  "kickstarts", # profile kickstarts go here
                  g.name
              )
              self.mkdir(copy_path)
              dest = os.path.join(copy_path, "ks.cfg")
              try:
                   meta = self.blend_options(False, (
                       distro.ks_meta,
                       g.ks_meta,
                   ))
                   meta["yum_repo_stanza"] = self.generate_repo_stanza(g)
                   meta["yum_config_stanza"] = self.generate_config_stanza(g)
                   meta["kickstart_done"] = self.generate_kickstart_done(g, is_system=False)
                   self.apply_template(kickstart_path, meta, dest)
              except:
                   traceback.print_exc() # leave this in, for now...
                   msg = "err_kickstart2"
                   raise cexceptions.CobblerException(msg,kickstart_path,dest)

    def generate_kickstart_done(self, obj, is_system=False):
        pattern = "wget http://%s/cobbler/watcher.py?%s_done=%s --output-document=kickstart_done"
        if is_system:
            return pattern % (self.settings.server, "system", obj.name)
        else:
            return pattern % (self.settings.server, "profile", obj.name)

    def generate_repo_stanza(self, profile):
        # returns the line of repo additions (Anaconda supports in FC-6 and later) that adds
        # the list of repos to things that Anaconda can install from.  This corresponds
        # will replace "TEMPLATE::yum_repo_stanza" in a cobbler kickstart file.
        buf = ""
        repos = profile.repos
        repos = repos.split(" ")
        for r in repos:
            repo = self.repos.find(r)
            if repo is None:
                continue
            http_url = "http://%s/cobbler/repo_mirror/%s" % (self.settings.server, repo.name)
            buf = buf + "repo --name=%s --baseurl=%s\n" % (repo.name, http_url)
        return buf

    def generate_config_stanza(self, profile):
        # returns the line in post that would configure yum to use repos added with "cobbler repo add"
        repos = profile.repos
        repos = repos.split(" ")
        buf = ""
        for r in repos:
            repo = self.repos.find(r)
            if repo is None: 
                continue
            if not (repo.local_filename is None and repo.local_filename != ""):
                buf = buf + "wget http://%s/cobbler/repo_mirror/%s/config.repo --output-document=/etc/yum.repos.d/%s.repo\n" % (self.settings.server, repo.name, repo.local_filename)    
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
                    meta["kickstart_done"] = self.generate_kickstart_done(profile, is_system=True)
                    self.apply_template(kickstart_path, meta, dest)
                except:
                    msg = "err_kickstart2"
                    raise cexceptions.CobblerException(msg,s.kickstart,dest)

    def apply_template(self, kickstart_input, metadata, out_path):
        """
        Take filesystem file kickstart_input, apply metadata using
        Cheetah and save as out_path.
        """
        fd = open(kickstart_input)
        data = fd.read()
        fd.close()
        for x in metadata.keys():
            if x != "":
               data = data.replace("TEMPLATE::%s" % x, metadata[x])
        self.mkdir(os.path.basename(out_path))
        fd = open(out_path, "w+")
        fd.write(data)
        fd.close()

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
            # TODO: add check to ensure all distros have profiles (=warning)
            filename = os.path.join(self.settings.webdir,"distros",d.name)
            d.kernel_options = self.blend_options(True,(
               self.settings.kernel_options,
               d.kernel_options
            ))
            # yaml file: http only
            self.write_distro_file(filename,d)

        for p in self.profiles:
            # TODO: add check to ensure all profiles have distros (=error)
            # TODO: add check to ensure all profiles have systems (=warning)
            filename = os.path.join(self.settings.webdir,"profiles",p.name)
            distro = self.distros.find(p.distro)
            if distro is not None:
                p.kernel_options = self.blend_options(True,(
                   self.settings.kernel_options,
                   distro.kernel_options,
                   p.kernel_options
                ))
            # yaml file: http only
            self.write_profile_file(filename,p)

        # Copy default PXE file if it exists; if there's none, ignore
        # FIXME: Log something inobtrusive ifthe default file is missing
        src = "/etc/cobbler/default.pxe"
        if os.path.exists(src):
            nocopy = False
            for system in self.systems:
                if system.name == "default":
                    nocopy = True
                    break
            if not nocopy:
                dst = os.path.join(self.settings.tftpboot, "pxelinux.cfg", "default")
                self.copyfile(src, dst)

        for system in self.systems:
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

            if distro.arch in [ "x86", "x86_64", "standard"]:
                self.write_pxe_file(f2,system,profile,distro,False)
            if distro.arch == "ia64":
                self.write_pxe_file(f2,system,profile,distro,True)
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


    def write_pxe_file(self,filename,system,profile,distro,is_ia64):
        """
        Write a configuration file for the boot loader(s).
        More system-specific configuration may come in later, if so
        that would appear inside the system object in api.py

        NOTE: relevant to tftp only
        """
        kernel_path = os.path.join("/images",distro.name,os.path.basename(distro.kernel))
        initrd_path = os.path.join("/images",distro.name,os.path.basename(distro.initrd))
        kickstart_path = profile.kickstart
        fd = self.open_file(filename,"w+")
        if not is_ia64:
            # pxelinux tree
            self.tee(fd,"default linux\n")
            self.tee(fd,"prompt 0\n")
            self.tee(fd,"timeout 1\n")
            self.tee(fd,"label linux\n")
            self.tee(fd,"\tkernel %s\n" % kernel_path)
        else:
            # elilo thrown in root
            self.tee(fd,"image=%s\n" % kernel_path)
            self.tee(fd,"\tlabel=netinstall\n")
            self.tee(fd,"\tinitrd=%s\n" % initrd_path)
            self.tee(fd,"\tread-only\n")
            self.tee(fd,"\troot=/dev/ram\n")

        # now build the kernel command line
        kopts = self.blend_options(True,(
           self.settings.kernel_options,
           profile.kernel_options,
           distro.kernel_options,
           system.kernel_options
        ))

        # the kernel options line is common to elilo and pxelinux
        append_line = "%s" % kopts

        # if not ia64, include initrd on this line
        # for ia64, it's already done
        if not is_ia64:
            append_line = "%s initrd=%s" % (append_line,initrd_path)

        # kickstart path (if kickstart is used)
        if kickstart_path is not None and kickstart_path != "":
            # if kickstart path is on disk, we've already copied it into
            # the HTTP mirror, so make it something anaconda can get at.
            if kickstart_path.startswith("/") or kickstart_path.find("/cobbler/kickstarts/") != -1:
                pxe_fn = self.get_pxe_filename(system.name)
                kickstart_path = "http://%s/cobbler/kickstarts_sys/%s/ks.cfg" % (self.settings.server, pxe_fn)
            append_line = "%s ks=%s" % (append_line, kickstart_path)

        # now to add the append line to the file
        if not is_ia64:
            # pxelinux.cfg syntax
            self.tee(fd, "\tappend %s" % append_line)
        else:
            # elilo.conf syntax
            self.tee(fd, "\tappend=\"%s\"" % append_line)

        self.close_file(fd)

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

    def write_distro_file(self,filename,distro):
        """
        Create distro information for virt install

        NOTE: relevant to http only
        """
        fd = self.open_file(filename,"w+")
        # resolve to current values
        distro.kernel = utils.find_kernel(distro.kernel)
        distro.initrd = utils.find_initrd(distro.initrd)
        self.tee(fd,yaml.dump(distro.to_datastruct()))
        self.close_file(fd)

    def write_profile_file(self,filename,profile):
        """
        Create profile information for virt install

        NOTE: relevant to http only
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
        Create system information for virt install

        NOTE: relevant to http only
        """
        fd = self.open_file(filename,"w+")
        self.tee(fd,yaml.dump(system.to_datastruct()))
        self.close_file(fd)

    def tee(self,fd,text):
        """
        For dryrun support:  send data to screen and potentially to disk
        """
        if self.dryrun:
            print text
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
       print "%s -> %s" % (src,dst)
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
       print "%s -> %s" % (src,dst)
       if self.dryrun:
           return True
       try:
           return shutil.copy(src,dst)
       except IOError, ioe:
           raise cexceptions.CobblerException("need_perms2",src,dst)

    def rmfile(self,path):
       """
       For dryrun support.  potentially unlink a file.
       """
       if self.dryrun:
           return True
       try:
           os.unlink(path)
           return True
       except OSError, ioe:
           if not ioe.errno == errno.ENOENT: # doesn't exist
               traceback.print_exc()
               raise cexceptions.CobblerException("no_delete",path)
           return True

    def rmtree(self,path):
       """
       For dryrun support:  potentially delete a tree.
       """
       print "del %s" % (path)
       if self.dryrun:
           return True
       try:
           return shutil.rmtree(path)
       except OSError, ioe:
           if not ioe.errno == errno.ENOENT: # doesn't exist
               raise cexceptions.CobblerException("no_delete",path)
           return True

    def mkdir(self,path,mode=0777):
       """
       For dryrun support:  potentially make a directory.
       """
       if self.dryrun:
           print "mkdir %s" % (path)
           return True
       try:
           return os.makedirs(path,mode)
       except OSError, oe:
           if not oe.errno == 17: # already exists (no constant for 17?)
               traceback.print_exc()
               raise cexceptions.CobblerException("no_create", path)

    def service(self, name, action):
        """
        Call /sbin/service NAME ACTION, unless its a dryrun
        """

        cmd = "/sbin/service %s %s" % (name, action)
        if self.dryrun:
            print cmd
            return 0
        else:
            return sub_process.call(cmd, shell=True)

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

