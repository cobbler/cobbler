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
from cobbler.utils import *

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

    def __xmlrpc(self):
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
        data['base_url'] = self.base_url
        #filepath = "%s/%s" % (os.path.dirname(__file__), template)
        filepath = os.path.join("/usr/share/cobbler/webui_templates/",template)
        tmpl = Template( file=filepath, searchList=data )
        return str(tmpl)

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
        return self.__render( 'item.tmpl', {
            'item_data': self.__xmlrpc().get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #
    def distro_view(self, distribution):
        # get_distro_for_koan() flattens out the inherited options
        #distro = self.__xmlrpc().get_distro_for_koan(distribution)
        return  self.__render( 'item.tmpl', {
            'item_data': self.__xmlrpc().get_distro(distribution),
            'caption':   "Distribution \"%s\" Details" % distribution
        } )

    def distro_list(self):
        return self.__render( 'distro_list.tmpl', {
            'distros': self.__xmlrpc().get_distros()
        } )

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around
    def system_list(self):
        return self.__render( 'system_list.tmpl', {
            'systems': self.__xmlrpc().get_systems()
        } )

    def system_add(self):
        return self.__render( 'system_edit.tmpl', {
            'system': None,
            'profiles': self.__xmlrpc().get_profiles()
        } )

    def system_view(self, name):
        return self.__render( 'item.tmpl', {
            'item_data': self.__xmlrpc().get_system(name),
            'caption':   "Profile %s Settings" % name
        } )

    def system_save(self, name=None, profile=None, new_or_edit=None, mac=None, ip=None, hostname=None, kopts=None, ksmeta=None, netboot='n', **args):
        # parameter checking
        if name is None:
            return self.error_page("System name parameter is REQUIRED.")

        if mac is None and ip is None and hostname is None:
            return self.error_page("System must have at least one of MAC/IP/hostname.")

        # resolve_ip, is_mac, and is_ip are from cobbler.utils
        if hostname and not ip:
            ip = resolve_ip( hostname )

        if mac and not is_mac( mac ):
            return self.error_page("The provided MAC address appears to be invalid.")

        if ip and not is_ip( ip ):
            return self.error_page("The provided IP address appears to be invalid.")

        # set up XMLRPC - token is in self.token
        self.__xmlrpc()

        if new_or_edit == "edit":
            system = self.remote.get_system_handle( name, self.token )
        else:
            system = self.remote.new_system( self.token )
            self.remote.modify_system( system, 'name', name, self.token )

        if profile:
            self.remote.modify_system(system, 'profile',  profile,  self.token)
        if mac:
            self.remote.modify_system(system, 'mac',      mac,      self.token)
        if ip:
            self.remote.modify_system(system, 'ip',       ip,       self.token)
        if hostname:
            self.remote.modify_system(system, 'hostname', hostname, self.token)
        if kopts:
            self.remote.modify_system(system, 'kopts',    kopts,    self.token)
        if ksmeta:
            self.remote.modify_system(system, 'ksmeta',   ksmeta,   self.token)

        self.remote.save_system( system, self.token )

        return self.system_view( name=name )

    def system_edit(self, name):
        return self.__render( 'system_edit.tmpl', {
            'system': self.__xmlrpc().get_system(name),
            'profiles': self.__xmlrpc().get_profiles()
        } )

    # ------------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------------ #
    def profile_list(self):
        return self.__render( 'profile_list.tmpl', {
            'profiles': self.__xmlrpc().get_profiles()
        } )

    def profile_add(self):
        return self.__render( 'profile_add.tmpl', {
            'distros': self.__xmlrpc().get_distros(),
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
        ksfiles = list()
        for profile in self.__xmlrpc().get_profiles():
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
    distro_view.exposed = True
    index.exposed = True
    profile_add.exposed = True
    profile_list.exposed = True
    profile_save.exposed = True
    settings_view.exposed = True
    system_add.exposed = True
    system_edit.exposed = True
    system_list.exposed = True
    system_save.exposed = True
    system_view.exposed = True
    ksfile_view.exposed = True
    ksfile_list.exposed = True

class CobblerWebAuthException(exceptions.Exception):
    pass
