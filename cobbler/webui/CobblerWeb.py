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
            logger.error("An error has occurred.") # FIXME: remove
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

    def settings_view(self):
        self.__xmlrpc_setup()
        return self.__render( 'item.tmpl', {
            'item_data': self.remote.get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #

    #def distro_view(self, distribution):
    #    self.__xmlrpc_setup()
    #    return  self.__render( 'item.tmpl', {
    #        'item_data': self.remote.get_distro(distribution,True),
    #        'caption':   "Distribution \"%s\" Details" % distribution
    #    } )

    def distro_list(self):
        self.__xmlrpc_setup()
        return self.__render( 'distro_list.tmpl', {
            'distros': self.remote.get_distros()
        } )

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around
    def system_list(self):
        self.__xmlrpc_setup()
        return self.__render( 'system_list.tmpl', {
            'systems': self.remote.get_systems()
        } )

    def system_add(self):
        self.__xmlrpc_setup()
        return self.__render( 'system_edit.tmpl', {
            'system': None,
            'profiles': self.remote.get_profiles()
        } )

    # FIXME: this should use the same template as system_edit
    #def system_view(self, name):
    #    self.__xmlrpc_setup()
    #    return self.__render( 'item.tmpl', {
    #        'item_data': self.remote.get_system(name,True),
    #        'caption':   "Profile %s Settings" % name
    #    } )

    def system_save(self, name=None, profile=None, new_or_edit=None, mac=None, ip=None, hostname=None, kopts=None, ksmeta=None, netboot='n', dhcp_tag=None, **args):
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
        return self.system_edit( name=name )

    def system_edit(self, name):
        self.__xmlrpc_setup()
        return self.__render( 'system_edit.tmpl', {
            'system': self.remote.get_system(name,True),
            'profiles': self.remote.get_profiles()
        } )

    # ------------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------------ #
    def profile_list(self):
        self.__xmlrpc_setup()
        return self.__render( 'profile_list.tmpl', {
            'profiles': self.remote.get_profiles()
        } )

    def profile_add(self):
        self.__xmlrpc_setup()
        return self.__render( 'profile_edit.tmpl', {
            'distros': self.remote.get_distros(),
            'ksfiles': self.__ksfiles()
        } )

    def profile_edit(self, name):
        self.__xmlrpc_setup()
        return self.__render( 'profile_edit.tmpl', {
            'profile': self.remote.get_profile(name,True),
            'distros': self.remote.get_distros(),
            'ksfiles': self.__ksfiles()
        } )


    def profile_save(self):
        pass

    # ------------------------------------------------------------------------ #
    # Kickstart files
    # ------------------------------------------------------------------------ #
    def ksfile_list(self):
        return self.__render( 'ksfile_list.tmpl', {
            'ksfiles': self.__ksfiles()
        } )

    def ksfile_view(self, ksfile):
        return self.__render( 'ksfile_view.tmpl', {
            'ksdata': self.__ksfile_data( ksfile ),
            'ksfile': ksfile
        } )

    def __ksfiles(self):
        self.__xmlrpc_setup()
        ksfiles = []
        for profile in self.remote.get_profiles():
            ksfile = profile['kickstart']
            if not ksfile in ksfiles:
                ksfiles.append( ksfile )
        return ksfiles

    def __ksfile_data(self, ksfile):
        pass

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
    distro_list.exposed = True
    #distro_view.exposed = True
    index.exposed = True
    profile_edit.exposed = True
    profile_list.exposed = True
    profile_save.exposed = True
    #settings_view.exposed = True
    system_add.exposed = True
    system_edit.exposed = True
    system_list.exposed = True
    system_save.exposed = True
    #system_view.exposed = True
    ksfile_view.exposed = True
    ksfile_list.exposed = True

class CobblerWebAuthException(exceptions.Exception):
    pass
