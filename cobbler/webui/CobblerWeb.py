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
import Cookie
import time

# set up logging

logger = logging.getLogger("cobbler.webui")
logger.setLevel(logging.DEBUG)
ch = logging.FileHandler("/var/log/cobbler/webui.log")
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

def log_exc():
   """
   Log active traceback to logfile.
   """
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
    def __init__(self, server=None, base_url='/', username=None, password=None, token=None):
        self.server = server
        self.base_url = base_url
        self.remote = None
        self.token = token
        self.username = username
        self.password = password
        self.logout = None
        self.__cookies = Cookie.SimpleCookie(Cookie.SimpleCookie(os.environ.get("HTTP_COOKIE","")))

    def __xmlrpc_setup(self,is_login=False):
        """
        Sets up the connection to the Cobbler XMLRPC server.  Right now, the
        r/w server is required.   In the future, it may be possible to instantiate
        a r/o webui that doesn't need to login.
        """
    
        # changed to always create a new connection object
        self.remote = xmlrpclib.Server(self.server, allow_none=True)

        # if we do not have a token in memory, is it in a cookie?
        if self.token is None:
            self.token = self.__get_cookie_token()

        # else if we do have a token, try to use it...
        if self.token is not None:
            # validate that our token is still good
            try:
                self.remote.token_check(self.token)
                return True
            except Exception, e:
                # FIXME: check exception type to see that it is login related
                logger.info("token timeout for: %s" % self.username)
                log_exc()
                self.token = None
                # this should put us back to the login screen
                self.__cookie_logout()
        
        # if we (still) don't have a token, login for the first time
        if self.token is None and is_login:
            try:
                self.token = self.remote.login( self.username, self.password )
            except Exception, e:
                logger.info("login failed for: %s" % self.username)
                log_exc()
                return False
            self.__cookie_login(self.token) # save what we've got
            self.password = None # don't need it anymore, get rid of it
            return True
        
        # login failed
        return False


    def __render(self, template, data):
        """
        Call the templating engine (Cheetah), wrapping up the location
        of files while we're at it.
        """

        data['base_url'] = self.base_url

        # used by master.tmpl to determine whether or not to show login/logout links
        if self.token is not None:
            data['logged_in'] = 1
        elif self.username and self.password:
            data['logged_in'] = 'configured'
        else:
            data['logged_in'] = None

        filepath = os.path.join("/usr/share/cobbler/webui_templates/",template)
        tmpl = Template( file=filepath, searchList=data )
        return str(tmpl)

    def cookies(self):
        """
        Returns a Cookie.SimpleCookie object with all of CobblerWeb's cookies.
        Mmmmm cookies!
        """
        return self.__cookies

    def __cookie_logout(self,):
        self.__cookies["cobbler_xmlrpc_token"] = "null"
        # self.__cookies["cobbler_xmlrpc_token"]['expires'] = time.time() - 9999 
        return self.cookies

    def __cookie_login(self,token):
        self.__cookies["cobbler_xmlrpc_token"] = token
        # self.__cookies["cobbler_xmlrpc_token"]['expires'] = time.time() + 29*60
        return self.cookies 
         
    def __get_cookie_token(self):
        if self.__cookies.has_key("cobbler_xmlrpc_token"):
            value = self.__cookies["cobbler_xmlrpc_token"]
            logger.debug("loading token from cookie: %s" % value.value)
            return value.value
        return None

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
    # Authentication
    # ------------------------------------------------------------------------ #

    def login(self, message=None):
        return self.__render( 'login.tmpl', {'message': message} )

    def login_submit(self, username=None, password=None, submit=None):
        if username is None:
            return self.error_page( "No username supplied." )
        if password is None:
            return self.error_page( "No password supplied." )

        self.username = username
        self.password = password

        if not self.__xmlrpc_setup(is_login=True):
            return self.login(message="")

        return self.index()

    def logout_submit(self):
        self.token = None
        self.__cookie_logout()
        return self.login()

    # ------------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------------ #

    # FIXME: does it make sense to be able to edit settings?  Probably not,
    # as you could disable a lot of functionality if you aren't careful
    # including your ability to fix it back.

    def settings_view(self):
        if not self.__xmlrpc_setup():
            return self.login(message="")

        return self.__render( 'item.tmpl', {
            'item_data': self.remote.get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #

    def distro_list(self):
        if not self.__xmlrpc_setup():
            return self.login(message="")
        distros = self.remote.get_distros()
        if len(distros) > 0:
            return self.__render( 'distro_list.tmpl', {
                'distros': distros
            })
        else:
            return self.__render('empty.tmpl', {})  
  
    def distro_edit(self, name=None):

        if not self.__xmlrpc_setup():
            return self.login(message="")
         
        input_distro = None
        if name is not None:
            input_distro = self.remote.get_distro(name, True)

        return self.__render( 'distro_edit.tmpl', {
            'edit' : True,
            'distro': input_distro,
        } )

    # FIXME: deletes and renames
    def distro_save(self,name=None,oldname=None,new_or_edit=None,editmode='edit',kernel=None,
                    initrd=None,kopts=None,ksmeta=None,arch=None,breed=None,
                    delete1=None,delete2=None,**args):

        if not self.__xmlrpc_setup():
            return self.login(message="")

        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:     
                self.remote.distro_remove(name,self.token)   
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.distro_list()

        # pre-command paramter checking
        if name is None:
            return self.error_page("name is required")
        if kernel is None or not str(kernel).startswith("/"):
            return self.error_page("kernel must be specified as an absolute path")
        if initrd is None or not str(initrd).startswith("/"):
            return self.error_page("initrd must be specified as an absolute path")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed.")
 
        # grab a reference to the object
        if new_or_edit == "edit" and editmode == "edit":
            try:
                distro = self.remote.get_distro_handle( name, self.token)
            except:
                log_exc()
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

        if editmode == "rename" and name != oldname:
            try:
                self.remote.distro_remove(oldname, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful. Object %s was copied instead, and the old copy (%s) still remains. Reason: %s" % (name, oldname, str(e)))


        return self.distro_list()

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around

    def system_list(self):

        if not self.__xmlrpc_setup():
            return self.login(message="")

        systems = self.remote.get_systems()
        if len(systems) > 0:
            return self.__render( 'system_list.tmpl', {
                'systems': systems
            } )
        else:
            return self.__render('empty.tmpl',{})

    # FIXME: implement handling of delete1, delete2 + renames
    def system_save(self,name=None,oldname=None,editmode="edit",profile=None,
                    new_or_edit=None, mac=None, ip=None, hostname=None, 
                    kopts=None, ksmeta=None, netboot='n', dhcp_tag=None, 
                    delete1=None, delete2=None, **args):

        if not self.__xmlrpc_setup():
            return self.login(message="")

        # parameter checking
        if name is None:
            return self.error_page("System name parameter is REQUIRED.")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed.")

        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:
                self.remote.system_remove(name,self.token)
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.system_list()

        # more parameter checking
        if mac is None and ip is None and hostname is None and not is_mac(name) and not is_ip(name):
            return self.error_page("System must have at least one of MAC/IP/hostname.")
        if hostname and not ip:
            ip = resolve_ip( hostname )
        if mac and not is_mac( mac ):
            return self.error_page("The provided MAC address appears to be invalid.")
        if ip and not is_ip( ip ):
            return self.error_page("The provided IP address appears to be invalid.")

        # grab a reference to the object
        if new_or_edit == "edit" and editmode == "edit":
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

        if editmode == "rename" and name != oldname:
            try:
                self.remote.system_remove(oldname, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful. Object %s was copied instead, and the old copy (%s) still remains. Reason: %s" % (name, oldname, str(e)))
        
        return self.system_list()


    def system_edit(self, name=None):

        if not self.__xmlrpc_setup():
            return self.login(message="")

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
        if not self.__xmlrpc_setup():
            return self.login(message="")
        profiles = self.remote.get_profiles()
        if len(profiles) > 0:
            return self.__render( 'profile_list.tmpl', {
                'profiles': profiles
            } )
        else:
            return self.__render('empty.tmpl', {})

    # FIXME: implement handling of delete1, delete2 + renames
    def profile_edit(self, name=None):

        if not self.__xmlrpc_setup():
            return self.login(message="")

        input_profile = None
        if name is not None:
             input_profile = self.remote.get_profile(name,True)

        return self.__render( 'profile_edit.tmpl', {
            'edit' : True,
            'profile': input_profile,
            'distros': self.remote.get_distros(),
            'ksfiles': self.remote.get_kickstart_templates(self.token) 
        } )

    def profile_save(self,new_or_edit=None,editmode='edit',name=None,oldname=None,
                     distro=None,kickstart=None,kopts=None,
                     ksmeta=None,virtfilesize=None,virtram=None,virttype=None,
                     virtpath=None,repos=None,dhcptag=None,delete1=None,delete2=None,**args):

        if not self.__xmlrpc_setup():
            return self.login(message="")

        # pre-command parameter checking 
        if name is None:
            return self.error_page("name is required")
        if distro is None:
            return self.error_page("distro is required")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed")
    
        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:
                self.remote.profile_remove(name,self.token)
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.profile_list()

        # grab a reference to the object
        if new_or_edit == "edit" and editmode == "edit":
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

        if editmode == "rename" and name != oldname:
            try:
                self.remote.profile_remove(oldname, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful. Object %s was copied instead, and the old copy (%s) still remains. Reason: %s" % (name, oldname, str(e)))


        return self.profile_list()

    # ------------------------------------------------------------------------ #
    # Repos
    # ------------------------------------------------------------------------ #

    def repo_list(self):
        if not self.__xmlrpc_setup():
            return self.login(message="")
        repos = self.remote.get_repos()
        if len(repos) > 0:
            return self.__render( 'repo_list.tmpl', {
                'repos': repos
            })
        else:
            return self.__render('empty.tmpl', {})

    def repo_edit(self, name=None):
        if not self.__xmlrpc_setup():
            return self.login(message="")

        input_repo = None
        if name is not None:
            input_repo = self.remote.get_repo(name, True)

        return self.__render( 'repo_edit.tmpl', {
            'repo': input_repo,
        } )

    def repo_save(self,name=None,oldname=None,new_or_edit=None,editmode="edit",
                  mirror=None,keepupdated=None,localfilename=None,
                  rpmlist=None,createrepoflags=None,delete1=None,delete2=None,**args):
        if not self.__xmlrpc_setup():
            return self.login(message="")

        # pre-command parameter checking
        if name is None:
            return self.error_page("name is required")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed.")


        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:
                self.remote.repo_remove(name,self.token)
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.repo_list()

        # more parameter checking
        if mirror is None:
            return self.error_page("mirror is required")

        # grab a reference to the object
        if new_or_edit == "edit" and editmode == "edit":
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

        if editmode == "rename" and name != oldname:
            try:
                self.remote.repo_remove(oldname, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful. Object %s was copied instead, and the old copy (%s) still remains. Reason: %s" % (name, oldname, str(e)))


        return self.repo_list()



    # ------------------------------------------------------------------------ #
    # Kickstart files
    # ------------------------------------------------------------------------ #

    def ksfile_list(self):
        if not self.__xmlrpc_setup():
            return self.login(message="")
        return self.__render( 'ksfile_list.tmpl', {
            'ksfiles': self.remote.get_kickstart_templates(self.token)
        } )

    def ksfile_edit(self, name=None):
        if not self.__xmlrpc_setup():
            return self.login(message="")
        return self.__render( 'ksfile_edit.tmpl', {
            'ksfile': name,
            'ksdata': self.remote.read_or_write_kickstart_template(self,name,True,"",self.token)

        } )

    def ksfile_save(self, name=None, data=None):
        if not self.__xmlrpc_setup():
            return self.login(message="")
        try:
            self.remote.read_or_write_kickstart_template(self,name,False,data,self.token)
        except Exception, e:
            return self.error_page("error with kickstart: %s" % str(e))
        return self.ksfile_edit(name=ksfile)

    # ------------------------------------------------------------------------ #
    # Miscellaneous
    # ------------------------------------------------------------------------ #
 
    def sync(self):
        if not self.__xmlrpc_setup():
            return self.login(message="")

        try:
            rc = self.remote.sync(self.token)
            if not rc:
                return self.error_page("Sync failed.  Try debugging locally.")
        except Exception, e:
            log_exc()
            return self.error_page("Sync encountered an exception: %s" % str(e))

        return self.__render('message.tmpl', {
            'message1' : "Sync complete.",
            'message2' : "Cobbler config has been applied to filesystem."
        }) 

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

    login.exposed = True
    login_submit.exposed = True
    logout_submit.exposed = True
    cookies.exposed = False

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

    sync.exposed = True

class CobblerWebAuthException(exceptions.Exception):
    pass


