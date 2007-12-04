"""
mod_python gateway to all interesting cobbler web and web service
functions.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# still TODO:
# serve up Web UI through this interface, via tokens in headers

from mod_python import apache
from mod_python import Session
import xmlrpclib

XMLRPC_SERVER = "http://127.0.0.1/cobbler_api_rw"

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

def index(req):

    """
    Right now, index serves everything.

    Hitting this URL means we've already cleared authn/authz
    but we still need to use the token for all remote requests.

    FIXME: deal with query strings and defer to CobblerWeb.py
    """

    my_user = __get_user(req)
    my_uri = req.uri

    sess  = __get_session(req)
    token = sess['cobbler_token']

    return "it seems to be all good: %s" % token

#======================================================

def hello(req):

    """
    This is just another example for the publisher handler.
    """

    user = __get_user(req)
    path = req.uri
    return "We are in hello(%s)" % path

#======================================================

def authenhandler(req):

    """
    Validates that username/password are a valid combination, but does
    not check access levels.
    """

    my_pw = req.get_basic_auth_pw()
    my_user = req.user
    my_uri = req.uri

    apache.log_error("authenhandler called: %s" % my_user)
    try:
        token = xmlrpc_server.login(my_user,my_pw)
    except:
        return apache.HTTP_UNAUTHORIZED

    try:
        ok = xmlrpc_server.check_access(token,my_uri)
    except:
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

