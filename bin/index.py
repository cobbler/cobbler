"""
mod_python gateway to all interesting cobbler web functions

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from mod_python import apache
from mod_python import Session
from mod_python import util

import xmlrpclib
import cgi
import os
from cobbler.webui import CobblerWeb
import cobbler.utils as utils
import yaml # PyYAML

XMLRPC_SERVER = "http://127.0.0.1:25151" # FIXME: pull port from settings

#=======================================

class ServerProxy(xmlrpclib.ServerProxy):

    """
    Establishes a connection from the mod_python
    web interface to cobblerd, which incidentally 
    is also being proxied by Apache.
    """

    def __init__(self, url=None):
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

xmlrpc_server = ServerProxy(XMLRPC_SERVER)

#=======================================

def __get_user(req):
    """
    What user are we logged in as?
    """
    req.add_common_vars()
    env_vars = req.subprocess_env.copy()
    return env_vars["REMOTE_USER"]

def __get_session(req):
    """
    Get/Create the Apache Session Object
    FIXME: any reason to not use MemorySession?
    """
    if not hasattr(req,"session"):
        req.session = Session.MemorySession(req)
    return req.session

#======================================================

def handler(req):

    """
    Right now, index serves everything.

    Hitting this URL means we've already cleared authn/authz
    but we still need to use the token for all remote requests.
    """

    my_user = __get_user(req)
    my_uri = req.uri
    sess  = __get_session(req)

    if not sess.has_key('cobbler_token'):
       # using Kerberos instead of Python Auth handler? 
       # We need to get our own token for use with authn_passthru
       # which should also be configured in /etc/cobbler/modules.conf
       # if another auth mode is configured in modules.conf this will
       # most certaintly fail.
       try:
           if not os.path.exists("/var/lib/cobbler/web.ss"):
               apache.log_error("cannot load /var/lib/cobbler/web.ss")
               return apache.HTTP_UNAUTHORIZED
           fd = open("/var/lib/cobbler/web.ss")
           data = fd.read()
           my_pw = data
           fd.close()
           token = xmlrpc_server.login(my_user,my_pw)
       except Exception, e:
           apache.log_error(str(e))
           return apache.HTTP_UNAUTHORIZED
       sess['cobbler_token'] = token
    else:
       token = sess['cobbler_token']

    # needed?
    # usage later
    req.add_common_vars()
 
    # process form and qs data, if any
    fs = util.FieldStorage(req)
    form = {}
    for x in fs.keys():
        form[x] = str(fs.get(x,'default'))

    fd = open("/etc/cobbler/settings")
    data = fd.read()
    fd.close()
    ydata = yaml.safe_load(data)
    remote_port = ydata.get("xmlrpc_port", 25151)

    mode = form.get('mode','index')

    # instantiate a CobblerWeb object
    cw = CobblerWeb.CobblerWeb(
         apache   = apache,
         token    = token, 
         base_url = "/cobbler/web/",
         mode     = mode,
         server   = "http://127.0.0.1:%s" % remote_port
    )

    # check for a valid path/mode
    # handle invalid paths gracefully
    if mode in cw.modes():
        func = getattr( cw, mode )
        content = func( **form )
    else:
        func = getattr( cw, 'error_page' )
        content = func( "Invalid Mode: \"%s\"" % mode )

    if content.startswith("# REDIRECT "):
        util.redirect(req, location=content[11:], permanent=False)
    else:
        # apache.log_error("%s:%s ... %s" % (my_user, my_uri, str(form)))
        req.content_type = "text/html;charset=utf-8"
        req.write(unicode(content).encode('utf-8'))
    
    if not content.startswith("# ERROR") and content.find("<!-- ERROR -->") == -1:
       return apache.OK
    else:
       # catch Cheetah errors and web errors
       return apache.HTTP_INTERNAL_SERVER_ERROR
 
#======================================================

def authenhandler(req):

    """
    Validates that username/password are a valid combination, but does
    not check access levels.
    """

    my_pw = req.get_basic_auth_pw()
    my_user = req.user
    my_uri = req.uri

    try:
        token = xmlrpc_server.login(my_user,my_pw)
    except Exception, e:
        apache.log_error(str(e))
        return apache.HTTP_UNAUTHORIZED

    try:
        ok = xmlrpc_server.check_access(token,my_uri)
    except Exception, e:
        apache.log_error(str(e))
        return apache.HTTP_FORBIDDEN
        

    sess=__get_session(req)
    sess['cobbler_token'] = token
    sess.save()

    return apache.OK

#======================================================

def accesshandler(req):
    
    """
    Not using this
    """

    return apache.OK

#======================================================

def authenzhandler(req):

    """
    Not using this
    """

    return apache.OK

