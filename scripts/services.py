"""
mod_python gateway to cgi-like cobbler web functions

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
from cobbler.services import CobblerSvc

#=======================================

def handler(req):

    """
    Right now, index serves everything.

    Hitting this URL means we've already cleared authn/authz
    but we still need to use the token for all remote requests.
    """

    my_uri = req.uri

    # apache.log_error("cannot load /var/lib/cobbler/web.ss")
    req.add_common_vars()
 
    # process form and qs data, if any
    fs = util.FieldStorage(req)
    form = {}
    for x in fs.keys():
        form[x] = str(fs.get(x,'default'))

    form["REMOTE_ADDR"] = req.subprocess_env.get("REMOTE_ADDR",None)
    form["REMOTE_MAC"]  = req.subprocess_env.get("HTTP_X_RHN_PROVISIONING_MAC_0",None)
    
    # instantiate a CobblerWeb object
    cw = CobblerSvc(
         apache   = apache,
         server   = "http://127.0.0.1/cobbler_api"
    )

    # check for a valid path/mode
    # handle invalid paths gracefully
    mode = form.get('op','index')

    func = getattr( cw, mode )
    content = func( **form )

    # apache.log_error("%s:%s ... %s" % (my_user, my_uri, str(form)))
    req.content_type = "text/plain;charset=utf-8"
    content = unicode(content)
    req.write(content.encode('utf-8'))
    
    return apache.OK

