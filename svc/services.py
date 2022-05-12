"""
This module is a mod_wsgi application used to serve up the Cobbler
service URLs.

Copyright 2010, Red Hat, Inc and Others

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
# Only add standard python modules here. When running under a virtualenv other modules are not
# available at this point.

from builtins import str
import os
import urllib.request
import urllib.parse
import urllib.error
import xmlrpc.server

import yaml


def application(environ, start_response):

    if 'VIRTUALENV' in environ and environ['VIRTUALENV'] != "":
        # VIRTUALENV Support
        # see http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
        import site
        import distutils.sysconfig
        site.addsitedir(distutils.sysconfig.get_python_lib(prefix=environ['VIRTUALENV']))
        # Now all modules are available even under a virtualenv

    from cobbler.services import CobblerSvc

    my_uri = urllib.parse.unquote(environ['REQUEST_URI'])

    form = {}

    # canonicalizes uri, mod_python does this, mod_wsgi does not
    my_uri = os.path.realpath(my_uri)

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

    form["query_string"] = urllib.parse.parse_qs(environ['QUERY_STRING'])

    # This MAC header is set by anaconda during a kickstart booted with the
    # kssendmac kernel option. The field will appear here as something
    # like: eth0 XX:XX:XX:XX:XX:XX
    mac_counter = 0
    remote_macs = []
    mac_header = "HTTP_X_RHN_PROVISIONING_MAC_%d" % mac_counter
    while environ.get(mac_header, None):
        remote_macs.append(environ[mac_header])
        mac_counter = mac_counter + 1
        mac_header = "HTTP_X_RHN_PROVISIONING_MAC_%d" % mac_counter

    form["REMOTE_MACS"] = remote_macs

    # REMOTE_ADDR isn't a required wsgi attribute so it may be naive to assume
    # it's always present in this context.
    form["REMOTE_ADDR"] = environ.get("REMOTE_ADDR", None)

    # Read config for the XMLRPC port to connect to:
    with open("/etc/cobbler/settings.yaml") as main_settingsfile:
        ydata = yaml.safe_load(main_settingsfile)
    remote_port = ydata.get("xmlrpc_port", 25151)

    # instantiate a CobblerWeb object
    cw = CobblerSvc(server="http://127.0.0.1:%s" % remote_port)

    # check for a valid path/mode
    # handle invalid paths gracefully
    mode = form.get('op', 'index')

    # TODO: We could do proper exception handling here and return
    # corresponding HTTP status codes:

    status = "200 OK"
    # Execute corresponding operation on the CobblerSvc object:
    func = getattr(cw, mode)
    try:
        content = func(**form)

        if content.find("# *** ERROR ***") != -1:
            status = '500 SERVER ERROR'
            print("possible cheetah template error")

        # TODO: Not sure these strings are the right ones to look for...
        elif content.find("# profile not found") != -1 or \
                content.find("# system not found") != -1 or \
                content.find("# object not found") != -1:
            print(("content not found: %s" % my_uri))
            status = "404 NOT FOUND"
    except xmlrpc.server.Fault as err:
        status = "500 SERVER ERROR"
        content = err.faultString

    content = content.encode('utf-8')

    # req.content_type = "text/plain;charset=utf-8"
    response_headers = [('Content-type', 'text/plain;charset=utf-8'),
                        ('Content-Length', str(len(content)))]
    start_response(status, response_headers)

    return [content]
