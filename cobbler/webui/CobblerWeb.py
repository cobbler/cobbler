# Web Interface for Cobbler - Model
#
# Copyright 2007 Albert P. Tobey <tobert@gmail.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import exceptions
import xmlrpclib
from Cheetah.Template import Template
import os
import traceback
import string
from cobbler.utils import *
import logging
import sys

logger = logging.getLogger("cobbler.webui")
logger.setLevel(logging.DEBUG)
ch = logging.FileHandler("/var/log/cobbler/webui.log")
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

def log_exc():
   (t, v, tb) = sys.exc_info()
   logger.info("Exception occured: %s" % t )
   logger.info("Exception value: %s" % v)
   logger.info("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))



class CobblerWeb(object):
    """
    The Cobbler web interface uses a MVC-style pattern.  This is the model.
    The view uses Cheetah templates.  The controller is a small shim to make
    it all run either under cgi-bin or CherryPy.  Supporting other Python
    frameworks should be trivial.
    """
    def __init__(self, server=None, base_url='/', username=None, password=None):
        self.server = server
        self.base_url = base_url
        self.remote = None
        self.token = None

        if username is None or password is None:
            raise CobblerWebAuthException( "Must provide username and password for Cobbler r/w XMLRPC Interface!" )

        self.username = username
        self.password = password

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server.  Right now, the
        r/w server is required.   In the future, it may be possible to instantiate
        a r/o webui that doesn't need to login.
        """
        if self.remote is None:
            self.remote = xmlrpclib.Server(self.server, allow_none=True)
        if self.token is None:
            self.token = self.remote.login( self.username, self.password )
        return self.remote

    def __render(self, template, data):
        """
        Call the templating engine (Cheetah), wrapping up the location
        of files while we're at it.
        """
        try:
            data['base_url'] = self.base_url
            #filepath = "%s/%s" % (os.path.dirname(__file__), template)
            filepath = os.path.join("/usr/share/cobbler/webui_templates/",template)
            tmpl = Template( file=filepath, searchList=data )
            return str(tmpl)
        except:
            log_exc()
            return self.error_page("Error while rendering page.  See /var/log/cobbler/webui.log")

    def modes(self):
        """
        Returns a list of methods in this object that can be run as web
        modes.   In the background, it is using function attributes similarly 
        to how CherryPy does.
        """
        retval = list()
        for m in dir(self):
            func = getattr( self, m )
            if hasattr(func, 'exposed') and getattr(func,'exposed'):
                retval.append(m) 
        return retval

    # ------------------------------------------------------------------------ #
    # Index
    # ------------------------------------------------------------------------ #

    def index(self):
        return self.__render( 'index.tmpl', dict() )

    # ------------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------------ #

    # FIXME: does it make sense to be able to edit settings?  Probably not,
    # as you could disable a lot of functionality if you aren't careful
    # including your ability to fix it back.

    def settings_view(self):
        self.__xmlrpc_setup()
        return self.__render( 'item.tmpl', {
            'item_data': self.remote.get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #

    def distro_list(self):
        self.__xmlrpc_setup()
        distros = self.remote.get_distros()
        if len(distros) > 0:
            return self.__render( 'distro_list.tmpl', {
                'distros': distros
            })
        else:
            return self.__render('empty.tmpl', {})  
  
    def distro_edit(self, name=None):
        self.__xmlrpc_setup()
         
        input_distro = None
        if name is not None:
            input_distro = self.remote.get_distro(name, True)

        return self.__render( 'distro_edit.tmpl', {
            'edit' : True,
            'distro': input_distro,
        } )

    # FIXME: implement handling of delete1, delete2 + renames
    def distro_save(self,name=None,new_or_edit=None,kernel=None,initrd=None,kopts=None,ksmeta=None,arch=None,breed=None,**args):
        self.__xmlrpc_setup()
        
        # pre-command paramter checking
        if name is None:
            return self.error_page("name is required")
        if kernel is None or not str(kernel).startswith("/"):
            return self.error_page("kernel must be specified as an absolute path")
        if initrd is None or not str(initrd).startswith("/"):
            return self.error_page("initrd must be specified as an absolute path")
 
        # grab a reference to the object
        if new_or_edit == "edit":
            try:
                distro = self.remote.get_distro_handle( name, self.token)
            except:
                return self.error_page("Failed to lookup distro: %s" % name)
        else:
            distro = self.remote.new_distro(self.token)

        try:
            self.remote.modify_distro(distro, 'name', name, self.token)
            self.remote.modify_distro(distro, 'kernel', kernel, self.token)
            self.remote.modify_distro(distro, 'initrd', initrd, self.token)
            if kopts:
                self.remote.modify_distro(distro, 'kopts', kopts, self.token)
            if ksmeta:
                self.remote.modify_distro(distro, 'ksmeta', ksmeta, self.token)
            if arch:
                self.remote.modify_distro(distro, 'arch', arch, self.token)
            if breed:
                self.remote.modify_distro(distro, 'breed', breed, self.token)
            self.remote.save_distro(distro, self.token)
        except Exception, e:
            log_exc()
            return self.error_page("Error while saving distro: %s" % str(e))

        return self.distro_edit(name=name)

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around

    def system_list(self):
        self.__xmlrpc_setup()
        systems = self.remote.get_systems()
        if len(systems) > 0:
            return self.__render( 'system_list.tmpl', {
                'systems': systems
            } )
        else:
            return self.__render('empty.tmpl',{})

    # FIXME: implement handling of delete1, delete2 + renames
    def system_save(self, name=None, profile=None, new_or_edit=None, mac=None, ip=None, hostname=None, 
                    kopts=None, ksmeta=None, netboot='n', dhcp_tag=None, **args):

        self.__xmlrpc_setup()

        # parameter checking
        if name is None:
            return self.error_page("System name parameter is REQUIRED.")
        if mac is None and ip is None and hostname is None and not is_mac(name):
            return self.error_page("System must have at least one of MAC/IP/hostname.")
        if hostname and not ip:
            ip = resolve_ip( hostname )
        if mac and not is_mac( mac ):
            return self.error_page("The provided MAC address appears to be invalid.")
        if ip and not is_ip( ip ):
            return self.error_page("The provided IP address appears to be invalid.")

        # grab a reference to the object
        if new_or_edit == "edit":
            try:
                system = self.remote.get_system_handle( name, self.token )
            except:
                return self.error_page("Failed to lookup system: %s" % name)
        else:
            system = self.remote.new_system( self.token )

        # go!
        try:
            self.remote.modify_system(system, 'name', name, self.token )
            self.remote.modify_system(system, 'profile', profile, self.token)
            if mac:
               self.remote.modify_system(system, 'mac', mac, self.token)
            if ip:
               self.remote.modify_system(system, 'ip', ip, self.token)
            if hostname:
               self.remote.modify_system(system, 'hostname', hostname, self.token)
            if kopts:
               self.remote.modify_system(system, 'kopts', kopts, self.token)
            if ksmeta:
               self.remote.modify_system(system, 'ksmeta', ksmeta, self.token)
            if netboot:
               self.remote.modify_system(system, 'netboot-enabled', netboot, self.token)
            if dhcp_tag:
               self.remote.modify_system(system, 'dhcp-tag', dhcp_tag, self.token)
            self.remote.save_system( system, self.token)
        except Exception, e:
            # FIXME: get the exact error message and display to the user.
            log_exc()
            return self.error_page("Error while saving system: %s" % str(e))
        return self.system_edit( name=name)

    def system_edit(self, name=None):

        self.__xmlrpc_setup()

        input_system = None
        if name is not None:
            input_system = self.remote.get_system(name,True)

        return self.__render( 'system_edit.tmpl', {
            'edit' : True,
            'system': input_system,
            'profiles': self.remote.get_profiles()
        } )

    # ------------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------------ #
    def profile_list(self):
        self.__xmlrpc_setup()
        profiles = self.remote.get_profiles()
        if len(profiles) > 0:
            return self.__render( 'profile_list.tmpl', {
                'profiles': profiles
            } )
        else:
            return self.__render('empty.tmpl', {})

    # FIXME: implement handling of delete1, delete2 + renames
    def profile_edit(self, name=None):

        self.__xmlrpc_setup()

        input_profile = None
        if name is not None:
             input_profile = self.remote.get_profile(name,True)

        return self.__render( 'profile_edit.tmpl', {
            'edit' : True,
            'profile': input_profile,
            'distros': self.remote.get_distros(),
            'ksfiles': self.remote.get_kickstart_templates(self.token) 
        } )

    def profile_save(self,new_or_edit=None, name=None,distro=None,kickstart=None,kopts=None,
                     ksmeta=None,virtfilesize=None,virtram=None,virttype=None,
                     virtpath=None,repos=None,dhcptag=None,**args):

        self.__xmlrpc_setup()

        # pre-command parameter checking 
        if name is None:
            return self.error_page("name is required")
        if distro is None:
            return self.error_page("distro is required")
        
        # grab a reference to the object
        if new_or_edit == "edit":
            try:
                profile = self.remote.get_profile_handle( name, self.token )
            except:
                return self.error_page("Failed to lookup profile: %s" % name)
        else:
            profile = self.remote.new_profile(self.token)

        try:
            self.remote.modify_profile(profile, 'name', name, self.token)
            self.remote.modify_profile(profile,  'distro', distro, self.token)
            if kickstart:
                self.remote.modify_profile(profile, 'kickstart', kickstart, self.token)
            if kopts:
                self.remote.modify_profile(profile, 'kopts', kopts, self.token)
            if ksmeta:
                self.remote.modify_profile(profile, 'ksmeta', ksmeta, self.token)
            if virtfilesize:
                self.remote.modify_profile(profile, 'virt-file-size', virtfilesize, self.token)
            if virtram:
                self.remote.modify_profile(profile, 'virt-ram', virtram, self.token)
            if virttype:
                self.remote.modify_profile(profile, 'virt-type', virttype, self.token)
            if virtpath:
                self.remote.modify_profile(profile, 'virt-path', virtpath, self.token)
            if repos:
                self.remote.modify_profile(profile, 'repos', repos, self.token)
            if dhcptag:
                self.remote.modify_profile(profile, 'dhcp-tag', dhcptag, self.token)
            self.remote.save_profile(profile,self.token)
        except Exception, e:
            log_exc()
            return self.error_page("Error while saving profile: %s" % str(e))

        return self.profile_edit(name=name)

    # ------------------------------------------------------------------------ #
    # Repos
    # ------------------------------------------------------------------------ #

    def repo_list(self):
        self.__xmlrpc_setup()
        repos = self.remote.get_repos()
        if len(repos) > 0:
            return self.__render( 'repo_list.tmpl', {
                'repos': repos
            })
        else:
            return self.__render('empty.tmpl', {})

    def repo_edit(self, name=None):
        self.__xmlrpc_setup()

        input_repo = None
        if name is not None:
            input_repo = self.remote.get_repo(name, True)

        return self.__render( 'repo_edit.tmpl', {
            'repo': input_repo,
        } )

    def repo_save(self,name=None,new_or_edit=None,mirror=None,keepupdated=None,localfilename=None,rpmlist=None,createrepoflags=None,**args):
        self.__xmlrpc_setup()

        # pre-command parameter checking
        if name is None:
            return self.error_page("name is required")
        if mirror is None:
            return self.error_page("mirror is required")

        # grab a reference to the object
        if new_or_edit == "edit":
            try:
                repo = self.remote.get_repo_handle( name, self.token)
            except:
                return self.error_page("Failed to lookup repo: %s" % name)
        else:
            repo = self.remote.new_repo(self.token)

        try:
            self.remote.modify_repo(repo, 'name', name, self.token)
            self.remote.modify_repo(repo, 'mirror', mirror, self.token)
            if keepupdated:
                self.remote.modify_repo(repo, 'keep-updated', keepupdated, self.token)
            if localfilename:
                self.remote.modify_repo(repo, 'local-filename', localfilename, self.token)
            if rpmlist:
                self.remote.modify_repo(repo, 'rpm-list', rpmlist, self.token)
            if createrepoflags:
                self.remote.modify_distro(repo, 'createrepo-flags', createrepoflags, self.token)
            self.remote.save_repo(repo, self.token)
        except Exception, e:
            log_exc()
            return self.error_page("Error while saving repo: %s" % str(e))

        return self.repo_edit(name=name)



    # ------------------------------------------------------------------------ #
    # Kickstart files
    # ------------------------------------------------------------------------ #

    def ksfile_list(self):
        self.__xmlrpc_setup()
        return self.__render( 'ksfile_list.tmpl', {
            'ksfiles': self.remote.get_kickstart_templates(self.token)
        } )

    def ksfile_edit(self, name=None):
        self.__xmlrpc_setup()
        return self.__render( 'ksfile_edit.tmpl', {
            'ksfile': name,
            'ksdata': self.remote.read_or_write_kickstart_template(self,name,True,"",self.token)

        } )

    def ksfile_save(self, name=None, data=None):
        self.__xmlrpc_setup()
        try:
            self.remote.read_or_write_kickstart_template(self,name,False,data,self.token)
        except Exception, e:
            return self.error_page("error with kickstart: %s" % str(e))
        return self.ksfile_edit(name=ksfile)

    # ------------------------------------------------------------------------ #
    # Miscellaneous
    # ------------------------------------------------------------------------ #

    def error_page(self, message):
        return self.__render( 'error_page.tmpl', {
            'message': message
        } )

    # make CherryPy and related frameworks able to use this module easily
    # by borrowing the 'exposed' function attritbute standard and using
    # it for the modes() method

    modes.exposed = False
    error_page.exposed = False
    index.exposed = True

    distro_edit.exposed = True
    distro_list.exposed = True
    distro_save.exposed = True

    profile_edit.exposed = True
    profile_list.exposed = True
    profile_save.exposed = True

    system_edit.exposed = True
    system_list.exposed = True
    system_save.exposed = True

    repo_edit.exposed = True
    repo_list.exposed = True
    repo_save.exposed = True

    settings_view.exposed = True
    ksfile_edit.exposed = True
    ksfile_save.exposed = True
    ksfile_list.exposed = True

class CobblerWebAuthException(exceptions.Exception):
    pass


