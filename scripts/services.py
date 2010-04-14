"""
Cobbler uses Cheetah templates for lots of stuff, but there's
some additional magic around that to deal with snippets/etc.
(And it's not spelled wrong!)

Copyright 2010, Red Hat, Inc

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""
import yaml

from cobbler.services import CobblerSvc

def application(environ, start_response):
    print environ

    my_uri = environ['REQUEST_URI']
    print("Checkout my URI: %s" % my_uri)
    
 #   req.add_common_vars()

 #   # process form and qs data, if any
 #   fs = util.FieldStorage(req)
    form = {}
 #   for x in fs.keys():
 #       form[x] = str(fs.get(x,'default'))
 #   
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
          else:
             form[field] = t
          label = not label

    print(form)

 #   # TESTING..
 #   form.update(req.subprocess_env)

    # This MAC header is set by anaconda during a kickstart booted with the 
    # kssendmac kernel option. The field will appear here as something 
    # like: eth0 XX:XX:XX:XX:XX:XX
    form["REMOTE_MAC"]  = form.get("HTTP_X_RHN_PROVISIONING_MAC_0", None)
    print("REMOTE_MAC = %s" % form["REMOTE_MAC"])

    # Read config for the XMLRPC port to connect to:
    fd = open("/etc/cobbler/settings")
    data = fd.read()
    fd.close()
    ydata = yaml.load(data)
    remote_port = ydata.get("xmlrpc_port",25151)

    # instantiate a CobblerWeb object
    cw = CobblerSvc(server = "http://127.0.0.1:%s" % remote_port)

    # check for a valid path/mode
    # handle invalid paths gracefully
    mode = form.get('op','index')

    # TODO: We could do proper exception handling here and return
    # corresponding HTTP status codes:

    # Execute corresponding operation on the CobblerSvc object:
    func = getattr( cw, mode )
    content = func( **form )
    print("content = %s" % content)

    content = unicode(content).encode('utf-8')
    status = '200 OK'
    
    if content.find("# *** ERROR ***") != -1:
        status = '500 SERVER ERROR'
        print("possible cheetah template error")

    # TODO: Not sure these strings are the right ones to look for...
    elif content.find("# profile not found") != -1 or \
            content.find("# system not found") != -1 or \
            content.find("# object not found") != -1:
        print("content not found: %s" % my_uri)
        status = "404 NOT FOUND"

 #   req.content_type = "text/plain;charset=utf-8"
    response_headers = [('Content-type', 'text/plain;charset=utf-8'),
                        ('Content-Length', str(len(content)))]
    start_response(status, response_headers)

    return [content]
