# Web Interface for Cobbler
#
# Copyright 2007 Albert P. Tobey <tobert@gmail.com>
# additions: Michael DeHaan <mdehaan@redhat.com>
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
import math
from cobbler.utils import *
import sys

def log_exc(apache):
    """
    Log active traceback to logfile.
    """
    (t, v, tb) = sys.exc_info()
    apache.log_error("Exception occured: %s" % t )
    apache.log_error("Exception value: %s" % v)
    apache.log_error("Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tb))))

class CobblerWeb(object):
    """
    The Cobbler web interface uses a MVC-style pattern.  This is the model.
    The view uses Cheetah templates.  The controller is a small shim to make
    it all run either under cgi-bin or CherryPy.  Supporting other Python
    frameworks should be trivial.
    """
    def __init__(self, server=None, base_url='/', mode=None, username=None, password=None, token=None, apache=None):
        self.server = server
        self.base_url = base_url
        self.mode = mode
        self.remote = None
        self.token = token
        self.username = username
        self.password = password
        self.logout = None
        self.apache = apache

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server.  Right now, the
        r/w server is required.   In the future, it may be possible to instantiate
        a r/o webui that doesn't need to login.
        """
    
        # changed to always create a new connection object
        self.remote = xmlrpclib.Server(self.server, allow_none=True)

        # else if we do have a token, try to use it...
        if self.token is not None:
            # validate that our token is still good
            try:
                self.remote.token_check(self.token)
                self.username = self.remote.get_user_from_token(self.token)
                # ensure config is up2date
                self.remote.update(self.token)
                return True
            except Exception, e:
                if str(e).find("invalid token") != -1:
                    self.apache.log_error("cobbler token timeout for: %s" % self.username)
                    log_exc(self.apache)
                    self.token = None
                else:
                    raise e
        
        # if we (still) don't have a token, login for the first time
        elif self.password and self.username:
            try:
                self.token = self.remote.login( self.username, self.password )
            except Exception, e:
                self.apache.log_error("cobbler login failed for: %s" % self.username)
                log_exc(self.apache)
                return False
            self.password = None # don't need it anymore, get rid of it
            # ensure configuration is up2date
            self.remote.update(self.token)
            return True
        
        # login failed
        return False

    def __render(self, template, data):
        """
        Call the templating engine (Cheetah), wrapping up the location
        of files while we're at it.
        """
        data['base_url'] = self.base_url
        data['mode'] = self.mode
        filepath = os.path.join("/usr/share/cobbler/webui_templates/",template)
        tmpl = Template( file=filepath, searchList=[data] )
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

    def index(self,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        vdata =self.remote.extended_version()
        return self.__render( 'index.tmpl', {
            'version': vdata["version"],
        })

    def menu(self,**args):
        return self.__render( 'blank.tmpl', {} )
   
    # ------------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------------ #

    # FIXME: does it make sense to be able to edit settings?  Probably not,
    # as you could disable a lot of functionality if you aren't careful
    # including your ability to fix it back.

    def settings_view(self,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        return self.__render( 'item.tmpl', {
            'item_data': self.remote.get_settings(),
            'caption':   "Cobbler Settings"
        } )

    # ------------------------------------------------------------------------ #
    # Distributions
    # ------------------------------------------------------------------------ #

    def distro_menu(self,**spam):
        return self.__render('blank.tmpl',{ 'more_blank' : 1})

    def __search_execute(self,what,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        criteria={}
        if key1 is not None and key1 != "":
            criteria[key1] = value1.replace('"','')
        if key2 is not None and key2 != "":
            criteria[key2] = value2.replace('"','')
        if key3 is not None and key3 != "":
            criteria[key3] = value3.replace('"','')

        params = {}
        params['page'] = -1

        results = []
        if what == "distro":
            results = params['distros'] = self.remote.find_distro(criteria,True)
        elif what == "profile":
            results = params['profiles'] = self.remote.find_profile(criteria,True)
        elif what == "system":
            results = params['systems'] = self.remote.find_system(criteria,True)
        elif what == "image":
            results = params['images'] = self.remote.find_image(criteria,True)
        elif what == "repo":
            results = params['repos'] = self.remote.find_repo(criteria,True)
        else:
            raise "internal error, unknown search type"


        if len(results) > 0:
            return self.__render( "%s_list.tmpl" % what, params)
        else:
            return self.__render('empty.tmpl', { 'search' : 1 })  
   
    def distro_search_execute(self,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None,**rest):
        return self.__search_execute("distro",key1,value1,key2,value2,key3,value3)
    def profile_search_execute(self,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None,**rest):
        return self.__search_execute("profile",key1,value1,key2,value2,key3,value3)
    def system_search_execute(self,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None,**rest):
        return self.__search_execute("system",key1,value1,key2,value2,key3,value3)
    def image_search_execute(self,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None,**rest):
        return self.__search_execute("image",key1,value1,key2,value2,key3,value3)
    def repo_search_execute(self,key1=None,value1=None,key2=None,value2=None,key3=None,value3=None,**rest):
        return self.__search_execute("repo",key1,value1,key2,value2,key3,value3)
 
    def __search(self, what):
        caption = ""
        dest = ""
        if what   == "distro":
           caption = "Search distros"
           dest    = "distro_search_execute"
        elif what == "profile":
           caption = "Search profiles"
           dest    = "profile_search_execute"
        elif what == "system":
           caption = "Search systems"
           dest    = "system_search_execute"
        elif what == "repo":
           caption = "Search repos"
           dest    = "repo_search_execute"
        elif what == "image":
           caption = "Search image"
           dest    = "image_search_execute"
        else:
           raise "internal error, unknown object type in search"

        return self.__render('search.tmpl', {
                'what'             : what,
                'caption'          : caption,
                'submit_dest'      : dest
        })

    def distro_search(self,**spam):
        return self.__search('distro')
 
    def distro_list(self,page=None,limit=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        (page, results_per_page, pages) = self.__compute_pagination(page,limit,"distro")
        distros = self.remote.get_distros(page,results_per_page)

        if len(distros) > 0:
            return self.__render( 'distro_list.tmpl', {
                'distros'          : distros,
                'pages'            : pages,
                'page'             : page,
                'results_per_page' : results_per_page
            })
        else:
            return self.__render('empty.tmpl', {})  
  
    def distro_edit(self, name=None,**spam):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        
        input_distro = None
        if name is not None:
            input_distro = self.remote.get_distro(name, True)
            can_edit = self.remote.check_access_no_fail(self.token,"modify_distro",name)
        else:
            can_edit = self.remote.check_access_no_fail(self.token,"new_distro",None)
        
            if not can_edit:
                return self.__render('message.tmpl', {
                    'message1' : "Access denied.",
                    'message2' : "You do not have permission to create new objects."
                })

 
        return self.__render( 'distro_edit.tmpl', {
            'user' : self.username,
            'edit' : True,
            'editable' : can_edit,
            'distro': input_distro,
        } )


    def distro_save(self,name=None,comment=None,oldname=None,new_or_edit=None,editmode='edit',kernel=None,
                    initrd=None,kopts=None,koptspost=None,ksmeta=None,owners=None,arch=None,breed=None,redhatmanagementkey=None,
                    redhatmanagementserver=None,mgmt_classes=None,osversion=None,delete1=False,delete2=False,recursive=False,**args):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        
        # pre-command paramter checking
        # HTML forms do not transmit disabled fields
        if name is None and oldname is not None:
            name = oldname

        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:    
                if recursive: 
                    self.remote.remove_distro(name,self.token,True)
                else:
                    self.remote.remove_distro(name,self.token,False)
                       
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.distro_list()

        if name is None:
            return self.error_page("name is required")
        if kernel is None or not str(kernel).startswith("/"):
            return self.error_page("kernel must be specified as an absolute path")
        if initrd is None or not str(initrd).startswith("/"):
            return self.error_page("initrd must be specified as an absolute path")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed.")
 
        # grab a reference to the object
        if new_or_edit == "edit" and editmode in [ "edit", "rename" ]:
            try:
                if editmode == "edit":
                    distro = self.remote.get_distro_handle( name, self.token)
                else:
                    distro = self.remote.get_distro_handle( oldname, self.token)

            except:
                log_exc(self.apache)
                return self.error_page("Failed to lookup distro: %s" % name)
        else:
            distro = self.remote.new_distro(self.token)

        try:
            if editmode != "rename" and name:
                self.remote.modify_distro(distro, 'name', name, self.token)
            self.remote.modify_distro(distro, 'kernel', kernel, self.token)
            self.remote.modify_distro(distro, 'initrd', initrd, self.token)
            if kopts is not None:
                self.remote.modify_distro(distro, 'kopts', kopts, self.token)
            if koptspost is not None:
                self.remote.modify_distro(distro, 'kopts-post', koptspost, self.token)
            self.remote.modify_distro(distro, 'ksmeta', ksmeta, self.token)
            self.remote.modify_distro(distro, 'owners', owners, self.token)
            self.remote.modify_distro(distro, 'arch', arch, self.token)
            self.remote.modify_distro(distro, 'breed', breed, self.token)
            self.remote.modify_distro(distro, 'os-version', osversion, self.token)
            self.remote.modify_distro(distro, 'comment', comment, self.token)
            self.remote.modify_distro(distro, 'redhat_management_key', redhatmanagementkey, self.token)
            self.remote.modify_distro(distro, 'redhat_management_server', redhatmanagementserver, self.token)
            self.remote.modify_distro(distro, 'mgmt_classes', mgmt_classes, self.token)

            # now time to save, do we want to run duplication checks?
            self.remote.save_distro(distro, self.token, editmode)
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving distro: %s" % str(e))

        if editmode == "rename" and name != oldname:
            try:
                self.remote.rename_distro(distro, name, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful.")


        return self.distro_list()

    # ------------------------------------------------------------------------ #
    # Systems
    # ------------------------------------------------------------------------ #
    # if the system list is huge, this will probably need to use an
    # iterator so the list doesn't get copied around

    def __compute_pagination(self,page,results_per_page,collection_type):

        default_page = 0
        default_results_per_page = 50
        total_size = self.remote.get_size(collection_type)

        try:
            page = int(page)
        except:
            page = default_page
        try:
            results_per_page = int(results_per_page)
        except:
            results_per_page = default_results_per_page 

        if page < 0:
           page = default_page
        if results_per_page <= 0:
           results_per_page = default_results_per_page

        pages = total_size / results_per_page
        return (page, results_per_page, pages)
    
    def system_menu(self,**spam):
        return self.__render('blank.tmpl',{ 'more_blank' : 1})
        

    def system_list(self,page=None,limit=None,**spam):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        (page, results_per_page, pages) = self.__compute_pagination(page,limit,"system")
        systems = self.remote.get_systems(page,results_per_page)

        if len(systems) > 0:
            return self.__render( 'system_list.tmpl', {
                'systems'          : systems,
                'profiles'         : self.remote.get_profiles(),
                'pages'            : pages,
                'page'             : page,
                'results_per_page' : results_per_page
            } )
        else:
            return self.__render('empty.tmpl',{})


    def system_list_action(self,actionname=None,targetlist=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        if actionname is None:
            return self.error_page("Actionname parameter is REQUIRED.")

        if actionname == 'add':
            return self.system_edit_new()

        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")

        # Single item actions
        if actionname == 'copy':
            return self.system_edit_copy(targetlist)
        if actionname == 'edit':
            return self.system_edit(targetlist)

        # Multiple items actions
        systems=[]
        for targetname in targetlist.split():
            systems.append(self.remote.get_system(targetname,self.token))

        return self.__render( 'system_'+actionname+'.tmpl', {
                'systems'    : systems,
                'profiles'   : self.remote.get_profiles(),
                'targetlist' : targetlist,
            } )


    def system_netboot(self,targetlist=None,netboot=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")
        if netboot is None:
            return self.error_page("Netboot parameter is REQUIRED.")
        try:
            systems=[]
            for targetname in targetlist.split():
                systems.append(self.remote.get_system_handle(targetname,self.token))
            for system in systems:
                self.remote.modify_system(system, 'netboot-enabled', netboot, self.token)
                self.remote.save_system(system, self.token)
            return self.system_list()
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving system: %s" % str(e))


    def system_profile(self,targetlist=None,profile=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")
        if profile is None:
            return self.error_page("Profile parameter is REQUIRED.")
        try:
            systems=[]
            for targetname in targetlist.split():
                systems.append(self.remote.get_system_handle(targetname,self.token))
            for system in systems:
                self.remote.modify_system(system, 'profile', profile, self.token)
                self.remote.save_system(system, self.token)
            return self.system_list()
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving system: %s" % str(e))


    def system_power(self,targetlist=None,power=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")
        if power is None:
            return self.error_page("Power parameter is REQUIRED.")
        try:
            systems=[]
            for targetname in targetlist.split():
                systems.append(self.remote.get_system_handle(targetname,self.token))
            for system in systems:
                self.remote.power_system(system, power, self.token)
            return self.system_list()
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while controlling power of system: %s" % str(e))


    def system_rename(self,targetlist=None,name=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")
        try:
            systems=[]
            for targetname in targetlist.split():
                systems.append(self.remote.get_system_handle(targetname,self.token))
            for system in systems:
                self.remote.rename_system(system, name, self.token)
            return self.system_list()
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while renaming system: %s" % str(e))


    def system_delete(self,targetlist=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        if targetlist is None:
            return self.error_page("Targetlist parameter is REQUIRED.")
        try:
            for targetname in targetlist.split():
                self.remote.remove_system(targetname, self.token)
            return self.system_list()
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while deleting system: %s" % str(e))



    def system_edit(self, name=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        if name is None:
            return self.error_page("Name parameter is REQUIRED")
        input_system = self.remote.get_system(name,True)
        can_edit = self.remote.check_access_no_fail(self.token,"modify_system",name)

        return self.__render( 'system_edit.tmpl', {
            'user' : self.username,
            'editmode' : 'edit',
            'editable' : can_edit,
            'system': input_system,
            'profiles': self.remote.get_profiles()
        } )


    def system_edit_new(self,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        can_edit = self.remote.check_access_no_fail(self.token,"new_system",None)
        if not can_edit:
            return self.__render('message.tmpl', {
                'message1' : "Access denied.",
                'message2' : "You do not have permission to create new objects."        
            })

        return self.__render( 'system_edit.tmpl', {
            'user' : self.username,
            'editmode' : 'new',
            'editable' : True,
            'system': None,
            'profiles': self.remote.get_profiles()
        } )


    def system_edit_copy(self, name=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        if name is None:
            return self.error_page("Name parameter is REQUIRED")
            
        can_edit = self.remote.check_access_no_fail(self.token,"new_system",None)
        if not can_edit:
            return self.__render('message.tmpl', {
                'message1' : "Access denied.",
                'message2' : "You do not have permission to create new objects."        
            })
            
        input_system = self.remote.get_system(name,True)

        return self.__render( 'system_edit.tmpl', {
            'user' : self.username,
            'editmode' : 'copy',
            'editable' : True,
            'system': input_system,
            'profiles': self.remote.get_profiles()
        } )


    def system_save(self,name=None,comment=None,editmode="edit",profile=None,
                    kopts=None, koptspost=None, ksmeta=None, owners=None, server_override=None, netboot='n', 
                    virtpath=None,virtram=None,virttype=None,virtcpus=None,virtfilesize=None,
                    name_servers=None,name_servers_search=None,
                    power_type=None, power_user=None, power_pass=None, power_id=None, power_address=None,
                    gateway=None,hostname=None,redhatmanagementkey=None,redhatmanagementserver=None,mgmt_classes=None,delete1=None, delete2=None, **args):


        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        # parameter checking
        if name is None:
            return self.error_page("System name parameter is REQUIRED.")

        # grab a reference to the object
        if editmode == "edit":
            try:
                system = self.remote.get_system_handle( name, self.token )
            except:
                return self.error_page("Failed to lookup system: %s" % name)
        else:
            try:
                system = self.remote.get_system_handle( name, self.token )
            except:
                system = None
            if system is not None:
                return self.error_page("Failed to create new system: %s already exists." % name)
            system = self.remote.new_system( self.token )

        # go!
        try:
            if editmode != "edit":
                self.remote.modify_system(system, 'name', name, self.token )
            self.remote.modify_system(system, 'profile', profile, self.token)
            self.remote.modify_system(system, 'kopts', kopts, self.token)
            self.remote.modify_system(system, 'kopts-post', koptspost, self.token)
            self.remote.modify_system(system, 'ksmeta', ksmeta, self.token)
            self.remote.modify_system(system, 'owners', owners, self.token)
            self.remote.modify_system(system, 'netboot-enabled', netboot, self.token)
            self.remote.modify_system(system, 'server', server_override, self.token)

            self.remote.modify_system(system, 'virt-file-size', virtfilesize, self.token)
            self.remote.modify_system(system, 'virt-cpus', virtcpus, self.token)
            self.remote.modify_system(system, 'virt-ram', virtram, self.token)
            self.remote.modify_system(system, 'virt-type', virttype, self.token)
            self.remote.modify_system(system, 'virt-path', virtpath, self.token)

            self.remote.modify_system(system, 'comment', comment, self.token)

            self.remote.modify_system(system, 'power_type', power_type, self.token)
            self.remote.modify_system(system, 'power_user', power_user, self.token)
            self.remote.modify_system(system, 'power_pass', power_pass, self.token)
            self.remote.modify_system(system, 'power_id', power_id, self.token)
            self.remote.modify_system(system, 'power_address', power_address, self.token)
            self.remote.modify_system(system, 'name_servers', name_servers, self.token)
            self.remote.modify_system(system, 'name_servers_search', name_servers_search, self.token)
            self.remote.modify_system(system, 'gateway', gateway, self.token)
            self.remote.modify_system(system, 'hostname', hostname, self.token)
            self.remote.modify_system(system, 'redhat_management_key', redhatmanagementkey, self.token)
            self.remote.modify_system(system, 'redhat_management_server', redhatmanagementserver, self.token)
            self.remote.modify_system(system, 'mgmt_classes', mgmt_classes, self.token)

            interfaces = args.get("interface_list","")
            interfaces = interfaces.split(",")

            for interface in interfaces:
                macaddress     = args.get("macaddress-%s" % interface, "")
                ipaddress      = args.get("ipaddress-%s" % interface, "")
                dnsname        = args.get("dns_name-%s" % interface, "")
                staticroutes   = args.get("static_routes-%s" % interface, "")
                static         = args.get("static-%s" % interface, "")
                virtbridge     = args.get("virtbridge-%s" % interface, "")
                dhcptag        = args.get("dhcptag-%s" % interface, "")
                subnet         = args.get("subnet-%s" % interface, "")
                bonding        = args.get("bonding-%s" % interface, "")
                bondingopts    = args.get("bondingopts-%s" % interface, "")
                bondingmaster  = args.get("bondingmaster-%s" % interface, "")
                present        = args.get("present-%s" % interface, "")
                original       = args.get("original-%s" % interface, "")

                if (present == "0") and (original == "1"):
                    # interfaces already stored and flagged for deletion must be destroyed
                    self.remote.modify_system(system,'delete-interface', interface, self.token) 
                elif (present == "1"):
                    # interfaces new or existing must be edited
                    mods = {}
                    mods["macaddress-%s" % interface] = macaddress
                    mods["ipaddress-%s" % interface] = ipaddress
                    mods["dnsname-%s" % interface]  = dnsname
                    mods["static_routes-%s" % interface] = staticroutes
                    mods["static-%s" % interface]  = static
                    mods["virtbridge-%s" % interface] = virtbridge
                    mods["dhcptag-%s" % interface] = dhcptag
                    mods["subnet-%s" % interface] = subnet
                    mods["present-%s" % interface] = present
                    mods["original-%s" % interface] = original
                    mods["bonding-%s" % interface] = bonding
                    mods["bondingopts-%s" % interface] = bondingopts
                    mods["bondingmaster-%s" % interface] = bondingmaster
                    self.remote.modify_system(system,'modify-interface', mods, self.token)

            self.remote.save_system(system, self.token, editmode)

        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving system: %s" % str(e))

        return self.system_list()

    def system_search(self,**spam):
        return self.__search('system')

    # ------------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------------ #
    
    def profile_search(self,**spam):
        return self.__search('profile')

    def profile_menu(self,**spam):
        return self.__render('blank.tmpl', { 'more_blank' : 1})

    def profile_list(self,page=None,limit=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        (page, results_per_page, pages) = self.__compute_pagination(page,limit,"profile")
        profiles = self.remote.get_profiles(page,results_per_page)

        if len(profiles) > 0:
            return self.__render( 'profile_list.tmpl', {
                'profiles'         : profiles,
                'pages'            : pages,
                'page'             : page,
                'results_per_page' : results_per_page
            } )
        else:
            return self.__render('empty.tmpl', {})

    def subprofile_edit(self, name=None,**spam):
        return self.profile_edit(name,1)

    def profile_edit(self, name=None, subprofile=0, **spam):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        input_profile = None
        if name is not None:
            input_profile = self.remote.get_profile(name,True)
            can_edit = self.remote.check_access_no_fail(self.token,"modify_profile",name)
            repos = self.remote.get_repos_compatible_with_profile(name)
        else:
            repos = self.remote.get_repos()
            can_edit = self.remote.check_access_no_fail(self.token,"new_profile",None)
            if not can_edit:
                return self.__render('message.tmpl', {
                    'message1' : "Access denied.",
                    'message2' : "You do not have permission to create new objects."        
                })



        return self.__render( 'profile_edit.tmpl', {
            'user' : self.username,
            'edit' : True,
            'editable' : can_edit,
            'profile': input_profile,
            'distros': self.remote.get_distros(),
            'profiles': self.remote.get_profiles(),
            'repos':   repos,
            'ksfiles': self.remote.get_kickstart_templates(self.token),
            'subprofile': subprofile
        } )

    def profile_save(self,new_or_edit=None,editmode='edit',name=None,comment=None,oldname=None,
                     distro=None,kickstart=None,kopts=None,koptspost=None,
                     ksmeta=None,owners=None,enablemenu=None,virtfilesize=None,virtram=None,virttype=None,
                     virtpath=None,repos=None,dhcptag=None,delete1=False,delete2=False,
                     parent=None,virtcpus=None,virtbridge=None,subprofile=None,server_override=None,
                     name_servers=None,name_servers_search=None,redhatmanagementserver=None,redhatmanagementkey=None,mgmt_classes=None,recursive=False,**args):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        # pre-command parameter checking 
        if name is None and oldname is not None:
            name = oldname
        if name is None:
            return self.error_page("A name has not been specified.")
        if distro is None and str(subprofile) == "0" :
            return self.error_page("A distribution has not been specified.")
        if parent is None and str(subprofile) == "1" :
            return self.error_page("A parent profile has not been specified.")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed")
    
        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:
                if recursive:
                    self.remote.remove_profile(name,self.token,True) 
                else:
                    self.remote.remove_profile(name,self.token,False) 
                      
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.profile_list()

        # grab a reference to the object
        if new_or_edit == "edit" and editmode in [ "edit", "rename" ] :
            try:
                if editmode == "edit":
                    profile = self.remote.get_profile_handle( name, self.token )
                else:
                    profile = self.remote.get_profile_handle( oldname, self.token )

            except:
                return self.error_page("Failed to lookup profile: %s" % name)
        else:
            if str(subprofile) != "1":
                profile = self.remote.new_profile(self.token)
            else:
                profile = self.remote.new_subprofile(self.token)

        try:
            if editmode != "rename" and name:
                self.remote.modify_profile(profile, 'name', name, self.token)
            if str(subprofile) != "1" and distro:
                self.remote.modify_profile(profile,  'distro', distro, self.token)
            if str(subprofile) == "1" and parent:
                self.remote.modify_profile(profile,  'parent', parent, self.token)
            self.remote.modify_profile(profile, 'kickstart', kickstart, self.token)
            self.remote.modify_profile(profile, 'kopts', kopts, self.token)
            self.remote.modify_profile(profile, 'kopts-post', koptspost, self.token)
            self.remote.modify_profile(profile, 'owners', owners, self.token)
            self.remote.modify_profile(profile, 'enable-menu', enablemenu, self.token)
            self.remote.modify_profile(profile, 'ksmeta', ksmeta, self.token)
            self.remote.modify_profile(profile, 'virt-file-size', virtfilesize, self.token)
            self.remote.modify_profile(profile, 'virt-ram', virtram, self.token)
            self.remote.modify_profile(profile, 'virt-type', virttype, self.token)
            self.remote.modify_profile(profile, 'virt-path', virtpath, self.token)
            self.remote.modify_profile(profile, 'virt-bridge', virtbridge, self.token)
            self.remote.modify_profile(profile, 'virt-cpus', virtcpus, self.token)
            self.remote.modify_profile(profile, 'server', server_override, self.token)
            self.remote.modify_profile(profile, 'comment', comment, self.token)
            self.remote.modify_profile(profile, 'name_servers', name_servers, self.token)
            self.remote.modify_profile(profile, 'name_servers_search', name_servers_search, self.token)
            self.remote.modify_profile(profile, 'redhat_management_key', redhatmanagementkey, self.token)
            self.remote.modify_profile(profile, 'redhat_management_server', redhatmanagementserver, self.token)
            self.remote.modify_profile(profile, 'mgmt_classes', mgmt_classes, self.token)

            if repos is None:
                repos = []
            elif type(repos) == type(str()):
                repos = [ repos ]
            if type(repos) == type([]):
                if '--none--' in repos:
                    repos.remove( '--none--' )
                self.remote.modify_profile(profile, 'repos', repos, self.token)

            self.remote.modify_profile(profile, 'dhcp-tag', dhcptag, self.token)
            self.remote.save_profile(profile,self.token, editmode)
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving profile: %s" % str(e))

        if editmode == "rename" and name != oldname:
            try:
                self.remote.rename_profile(profile, name, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful.")


        return self.profile_list()

    # ------------------------------------------------------------------------ #
    # Repos
    # ------------------------------------------------------------------------ #

    def repo_search(self,**spam):
        return self.__search('repo')

    def repo_menu(self,**spam):
        return self.__render('blank.tmpl', { 'more_blank' : 1})

    def repo_list(self,page=None,limit=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        (page, results_per_page, pages) = self.__compute_pagination(page,limit,"repo")
        repos = self.remote.get_repos(page,results_per_page)

        if len(repos) > 0:
            return self.__render( 'repo_list.tmpl', {
                'repos'            : repos,
                'pages'            : pages,
                'page'             : page,
                'results_per_page' : results_per_page
            })
        else:
            return self.__render('empty.tmpl', {})

    def repo_edit(self, name=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        input_repo = None
        if name is not None:
            input_repo = self.remote.get_repo(name, True)
            can_edit = self.remote.check_access_no_fail(self.token,"modify_repo",name)
        else:
            can_edit = self.remote.check_access_no_fail(self.token,"new_repo",None)
            if not can_edit:
                return self.__render('message.tmpl', {
                    'message1' : "Access denied.",
                    'message2' : "You do not have permission to create new objects."        
                })


        return self.__render( 'repo_edit.tmpl', {
            'user' : self.username,
            'repo': input_repo,
            'editable' : can_edit
        } )

    def repo_save(self,name=None,comment=None,oldname=None,new_or_edit=None,editmode="edit",
                  mirror=None,owners=None,keep_updated=None,mirror_locally=0,priority=99,
                  rpm_list=None,createrepo_flags=None,arch=None,environment=None,yumopts=None,
                  delete1=None,delete2=None,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        # pre-command parameter checking
        if name is None and oldname is not None:
            name = oldname
        if name is None:
            return self.error_page("name is required")
        if (editmode == 'rename' or editmode == 'copy') and name == oldname:
            return self.error_page("The name has not been changed.")

        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:
                self.remote.remove_repo(name,self.token)
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.repo_list()

        # more parameter checking
        if mirror is None:
            return self.error_page("mirror is required")

        # grab a reference to the object
        if new_or_edit == "edit" and editmode in [ "edit", "rename" ]:
            try:
                if editmode == "edit":
                    repo = self.remote.get_repo_handle( name, self.token)
                else:
                    repo = self.remote.get_repo_handle( oldname, self.token)
            except:
                return self.error_page("Failed to lookup repo: %s" % name)
        else:
            repo = self.remote.new_repo(self.token)

        try:
            if editmode != "rename" and name:
                self.remote.modify_repo(repo, 'name', name, self.token)
            self.remote.modify_repo(repo, 'mirror', mirror, self.token)
            self.remote.modify_repo(repo, 'keep-updated', keep_updated, self.token)
            self.remote.modify_repo(repo, 'priority', priority, self.token)
            self.remote.modify_repo(repo, 'mirror-locally', mirror_locally, self.token)

            self.remote.modify_repo(repo, 'rpm-list', rpm_list, self.token)
            self.remote.modify_repo(repo, 'createrepo-flags', createrepo_flags, self.token)
            self.remote.modify_repo(repo, 'arch', arch, self.token)
            self.remote.modify_repo(repo, 'yumopts', yumopts, self.token)
            self.remote.modify_repo(repo, 'environment', environment, self.token)
            self.remote.modify_repo(repo, 'owners', owners, self.token)
            self.remote.modify_repo(repo, 'comment', comment, self.token)


            self.remote.save_repo(repo, self.token, editmode)

        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving repo: %s" % str(e))

        if editmode == "rename" and name != oldname:
            try:
                self.remote.rename_repo(repo, name, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful.")

        return self.repo_list()

    # ------------------------------------------------------------------------ #
    # Images
    # ------------------------------------------------------------------------ #

    def image_search(self,**spam):
        return self.__search('image')

    def image_menu(self,**spam):
        return self.__render('blank.tmpl', { 'more_blank' : 1})

    def image_list(self,page=None,limit=None,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        (page, results_per_page, pages) = self.__compute_pagination(page,limit,"image")
        images = self.remote.get_images(page,results_per_page)

        if len(images) > 0:
            return self.__render( 'image_list.tmpl', {
                'images'           : images,
                'pages'            : pages,
                'page'             : page,
                'results_per_page' : results_per_page
            })
        else:
            return self.__render('empty.tmpl', {})  
  
    def image_edit(self, name=None,**spam):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        
        input_image = None
        if name is not None:
            input_image = self.remote.get_image(name, True)
            can_edit = self.remote.check_access_no_fail(self.token,"modify_image",name)
        else:
            can_edit = self.remote.check_access_no_fail(self.token,"new_image",None)
        
            if not can_edit:
                return self.__render('message.tmpl', {
                    'message1' : "Access denied.",
                    'message2' : "You do not have permission to create new objects."
                })

 
        return self.__render( 'image_edit.tmpl', {
            'user' : self.username,
            'edit' : True,
            'editable' : can_edit,
            'image': input_image,
        } )


    def image_save(self,name=None,comment=None,oldname=None,new_or_edit=None,editmode='edit',field1=None,
                   file=None,arch=None,breed=None,virtram=None,virtfilesize=None,virtpath=None,
                   virttype=None,virtcpus=None,virtbridge=None,imagetype=None,owners=None,
                   osversion=None,delete1=False,delete2=False,recursive=False,networkcount=None,**args):

        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        
        # pre-command paramter checking
        # HTML forms do not transmit disabled fields
        if name is None and oldname is not None:
            name = oldname

        # handle deletes as a special case
        if new_or_edit == 'edit' and delete1 and delete2:
            try:    
                if recursive: 
                    self.remote.remove_image(name,self.token,True)
                else:
                    self.remote.remove_image(name,self.token,False)
                       
            except Exception, e:
                return self.error_page("could not delete %s, %s" % (name,str(e)))
            return self.image_list()

        if name is None:
            return self.error_page("name is required")
 
        # grab a reference to the object
        if new_or_edit == "edit" and editmode in [ "edit", "rename" ]:
            try:
                if editmode == "edit":
                    image = self.remote.get_image_handle( name, self.token)
                else:
                    image = self.remote.get_image_handle( oldname, self.token)

            except:
                log_exc(self.apache)
                return self.error_page("Failed to lookup image: %s" % name)
        else:
            image = self.remote.new_image(self.token)

        try:
            if editmode != "rename" and name:
                self.remote.modify_image(image, 'name', name, self.token)
            self.remote.modify_image(image, 'image-type', imagetype, self.token)
            self.remote.modify_image(image, 'breed',      breed,     self.token)
            self.remote.modify_image(image, 'os-version', osversion, self.token)
            self.remote.modify_image(image, 'arch',       arch,      self.token)
            self.remote.modify_image(image, 'file',       file,      self.token)
            self.remote.modify_image(image, 'owners',     owners,    self.token)
            self.remote.modify_image(image, 'virt-cpus',  virtcpus,  self.token)
            self.remote.modify_image(image, 'network-count',  networkcount,  self.token)                
            self.remote.modify_image(image, 'virt-file-size', virtfilesize, self.token)
            self.remote.modify_image(image, 'virt-path',   virtpath,   self.token)
            self.remote.modify_image(image, 'virt-bridge', virtbridge, self.token)
            self.remote.modify_image(image, 'virt-ram',    virtram,    self.token)
            self.remote.modify_image(image, 'virt-type',   virttype,   self.token)
            self.remote.modify_image(image, 'comment', comment, self.token)

            self.remote.save_image(image, self.token, editmode)
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Error while saving image: %s" % str(e))

        if editmode == "rename" and name != oldname:
            try:
                self.remote.rename_image(image, name, self.token)
            except Exception, e:
                return self.error_page("Rename unsuccessful.")


        return self.image_list()


    # ------------------------------------------------------------------------ #
    # Kickstart files
    # ------------------------------------------------------------------------ #

    def ksfile_menu(self,**spam):
        return self.__render('blank.tmpl', { 'more_blank' : 1})

    def ksfile_list(self,**spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        return self.__render( 'ksfile_list.tmpl', {
            'ksfiles': self.remote.get_kickstart_templates(self.token)
        } )

    def ksfile_new(self, name=None,**spam):


        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        can_edit = self.remote.check_access_no_fail(self.token,"add_kickstart",name)
        return self.__render( 'ksfile_new.tmpl', {
            'editable' : can_edit,
            'ksdata': ''
        } )



    def ksfile_edit(self, name=None,**spam):


        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        can_edit = self.remote.check_access_no_fail(self.token,"modify_kickstart",name)
        return self.__render( 'ksfile_edit.tmpl', {
            'name': name,
            'deleteable' : not self.remote.is_kickstart_in_use(name,self.token),
            'editable' : can_edit,
            'ksdata': self.remote.read_or_write_kickstart_template(name,True,"",self.token)
        } )

    def ksfile_save(self, name=None, ksdata=None, delete1=None, delete2=None, isnew=None, **args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
            

        try:
            if delete1 and delete2:
                self.remote.read_or_write_kickstart_template(name,False,-1,self.token)
            if isnew is not None:
                name = "/var/lib/cobbler/kickstarts/" + name
            if not delete1 and not delete2:
                self.remote.read_or_write_kickstart_template(name,False,ksdata,self.token)
        except Exception, e:
            return self.error_page("An error occurred while trying to save kickstart file %s:<br/><br/>%s" % (name,str(e)))
        return self.ksfile_list()

    # ------------------------------------------------------------------------ #
    # Miscellaneous
    # ------------------------------------------------------------------------ #
 
    def sync(self,**args):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()

        can_edit = self.remote.check_access_no_fail(self.token,"sync",None)
        if not can_edit:
           return self.__render('message.tmpl', {
               'message1' : "Access denied.",
               'message2' : "You do not have permission to create new objects."
           })

        try:
            rc = self.remote.sync(self.token)
            if not rc:
                return self.error_page("Sync failed.  Try debugging locally.")
        except Exception, e:
            log_exc(self.apache)
            return self.error_page("Sync encountered an exception: %s" % str(e))

        return self.__render('message.tmpl', {
            'message1' : "Sync complete.",
            'message2' : "Cobbler config has been applied to filesystem."
        }) 

    def random_mac(self, **spam):
        if not self.__xmlrpc_setup():
            return self.xmlrpc_auth_failure()
        mac = self.remote.get_random_mac()
        return mac

    def error_page(self, message, **spam):

        # hack to remove some junk from remote fault errors so they
        # look as if they were locally generated and not exception-based.
        if message.endswith(">"):
            message = message[:-2]
            message = message.replace(":","",1)

        return self.__render( 'error_page.tmpl', {
            'message': message
        } )

    def xmlrpc_auth_failure(self, **spam):
        return self.__render( 'error_page.tmpl', {
            'message': "XMLRPC Authentication Error.   See Apache logs for details."
        } )

    # make CherryPy and related frameworks able to use this module easily
    # by borrowing the 'exposed' function attritbute standard and using
    # it for the modes() method

    modes.exposed = False
    error_page.exposed = False
    index.exposed = True
    menu.exposed = True

    distro_menu.exposed = True
    distro_edit.exposed = True
    distro_list.exposed = True
    distro_save.exposed = True
    distro_search.exposed = True
    distro_search_execute.exposed = True
 
    profile_menu.exposed = True
    subprofile_edit.exposed = True
    profile_edit.exposed = True
    profile_list.exposed = True
    profile_search.exposed = True
    profile_save.exposed = True
    profile_search_execute.exposed = True

    system_menu.exposed = True
    system_edit.exposed = True
    system_edit_new.exposed = True
    system_edit_copy.exposed = True
    system_list.exposed = True
    system_list_action.exposed = True
    system_netboot.exposed = True
    system_profile.exposed = True
    system_power.exposed = True
    system_rename.exposed = True
    system_delete.exposed = True
    system_save.exposed = True
    system_search.exposed = True
    system_search_execute.exposed = True

    repo_menu.exposed = True
    repo_edit.exposed = True
    repo_list.exposed = True
    repo_save.exposed = True
    repo_search.exposed = True
    repo_search_execute.exposed = True
    
    image_menu.exposed = True
    image_edit.exposed = True
    image_list.exposed = True
    image_save.exposed = True
    image_search.exposed = True
    image_search_execute.exposed = True

    settings_view.exposed = True
    ksfile_edit.exposed = True
    ksfile_new.exposed = True
    ksfile_save.exposed = True
    ksfile_list.exposed = True

    sync.exposed = True
    random_mac.exposed = True

class CobblerWebAuthException(exceptions.Exception):
    pass


