#!/usr/bin/env python

import xmlrpclib
from Cheetah.Template import Template
import os

class CobblerWeb(object):
    def __init__(self, server=None, base_url='/'):
        self.server = server
        self.base_url = base_url

    def xmlrpc(self):
        return xmlrpclib.ServerProxy(self.server, allow_none=True)

    def __render(self, template, data):
        data['base_url'] = self.base_url
        #filepath = "%s/%s" % (os.path.dirname(__file__), template)
        filepath = os.path.join("/usr/share/cobbler/webui_templates/",template)
        tmpl = Template( file=filepath, searchList=data )
        return str(tmpl)

    def modes(self):
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
            'item_data': self.xmlrpc().get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #
    def distro_view(self, distribution):
        # get_distro_for_koan() flattens out the inherited options
        #distro = self.xmlrpc().get_distro_for_koan(distribution)
        return  self.__render( 'item.tmpl', {
            'item_data': self.xmlrpc().get_distro(distribution),
            'caption':   "Distribution \"%s\" Details" % distribution
        } )

    def distro_list(self):
        return self.__render( 'distro_list.tmpl', {
            'distros': self.xmlrpc().get_distros()
        } )

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around
    def system_list(self):
        return self.__render( 'system_list.tmpl', {
            'systems': self.xmlrpc().get_systems()
        } )

    def system_add(self):
        return self.__render( 'system_edit.tmpl', {
            'profiles': self.xmlrpc().get_profiles()
        } )

    def system_view(self, name):
        return self.__render( 'item.tmpl', {
            'item_data': self.xmlrpc().get_profile(name),
            'caption':   "Profile %s Settings" % name
        } )

    def system_save(self, name, profile, submit, new_or_edit, mac=None, ip=None, hostname=None, kopts=None, ksmeta=None, netboot='n'):
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

        if new_or_edit == "edit":
            system = self.xmlrpc().get_system(name)
        else:
            # FIXME: convert to r/w xmlrpc
            system = None
            #system = self.api.new_system()
            system.set_name( name )
            self.api.systems().add( system )

        system.set_profile( profile )

        return self.__render( 'item.tmpl', {
            'item_data': system,
            'caption':   "Profile %s Settings" % name
        } )

    def system_edit(self, name):
        return self.__render( 'system_edit.tmpl', {
            'system': self.xmlrpc().get_system(name),
            'profiles': self.xmlrpc().get_profiles()
        } )

    # ------------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------------ #
    def profile_list(self):
        return self.__render( 'profile_list.tmpl', {
            'profiles': self.xmlrpc().get_profiles()
        } )

    def profile_add(self):
        return self.__render( 'profile_add.tmpl', {
            'distros': self.xmlrpc().get_distros(),
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
        for profile in self.xmlrpc().get_profiles():
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

