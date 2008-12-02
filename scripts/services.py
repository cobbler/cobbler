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
import cobbler.yaml as yaml
import cobbler.utils as utils

#=======================================

def handler(req):

    """
    Right now, index serves everything.

    Hitting this URL means we've already cleared authn/authz
    but we still need to use the token for all remote requests.
    """

    my_uri = req.uri
    
    req.add_common_vars()
 
    # process form and qs data, if any
    fs = util.FieldStorage(req)
    form = {}
    for x in fs.keys():
        form[x] = str(fs.get(x,'default'))
    
    if my_uri.find("?") == -1:
       # support fake query strings
       # something log /cobbler/web/op/ks/server/foo
       # which is needed because of xend parser errors
       # not tolerating ";" and also libvirt on 5.1 not
       # tolerating "&amp;" (nor "&").

       tokens = my_uri.split("/")
       tokens = tokens[3:]
       label = True
       field = ""
       for t in tokens:
          if label:
             field = t
             apache.log_error("field %s" % field)
          else:
             form[field] = t
             apache.log_error("adding %s to %s" % (field,t))
          label = not label

    # TESTING..
    form.update(req.subprocess_env)

    #form["REMOTE_ADDR"] = req.headers_in.get("REMOTE_ADDR",None)
    #form["REMOTE_MAC"]  = req.subprocess_env.get("HTTP_X_RHN_PROVISIONING_MAC_0",None)
    form["REMOTE_MAC"]  = form.get("HTTP_X_RHN_PROVISIONING_MAC_0",None)

    fd = open("/etc/cobbler/settings")
    data = fd.read()
    fd.close()
    ydata = yaml.load(data).next()
    remote_port = ydata.get("xmlrpc_port",25151)

    # instantiate a CobblerWeb object
    cw = CobblerSvc(
         apache   = apache,
         server   = "http://127.0.0.1:%s" % remote_port
    )

    # check for a valid path/mode
    # handle invalid paths gracefully
    mode = form.get('op','index')

    func = getattr( cw, mode )
    content = func( **form )

    # apache.log_error("%s:%s ... %s" % (my_user, my_uri, str(form)))
    req.content_type = "text/plain;charset=utf-8"
    content = unicode(content).encode('utf-8')
    
    if content.find("# *** ERROR ***") != -1:
        req.write(content)
        apache.log_error("possible cheetah template error")
        return apache.HTTP_ERROR
    elif content.find("# profile not found") != -1 or content.find("# system not found") != -1 or content.find("# object not found") != -1:
        req.content_type = "text/html;charset=utf-8"
        req.write(" ")
        apache.log_error("content not found")
        return apache.HTTP_NOT_FOUND
    else:
        req.write(content)
        return apache.OK

