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

# TO DO:
# connect backend authn via cobbler XMLRPC (non-RW) API
# connect backend authz via cobbler XMLRPC (RW) API
# serve up Web UI through this interface, via tokens in headers
# make REST interface for read/write commands (also?)

from mod_python import apache

def __get_user(req):
    req.add_common_vars()
    env_vars = req.subprocess_env.copy()
    return env_vars["REMOTE_USER"]

def index(req):
    user = __get_user(req)
    path = req.uri
    return "Hello, %s, %s" % (user, path)

def hello(req):
    user = __get_user(req)
    path = req.uri
    return "We are in hello(%s)" % path

def authenhandler(req):

    pw = req.get_basic_auth_pw()
    user = req.user

    # FIXME: poll cobbler_api (not rw) here to check
    # check_authn(user,pass) -> T/F

    apache.log_error("authenticate handler called")

    if user == "admin" and pw == "cobbler":
        return apache.OK
    else:
        return apache.HTTP_UNAUTHORIZED

def accesshandler(req):
    uri = req.uri

    apache.log_error("accesshandler uri: %s" % (uri))

    # FIXME: poll cobbler_api (not rw) here to check
    # check_access(user,uri) -> T/F

    if uri.find("hello") != -1:
        return apache.HTTP_FORBIDDEN
    return apache.OK

def authenzhandler(req):

    # we really don't need this because of the accesshandler.
    # add in later if we find we /DO/ need it
    return apache.OK


