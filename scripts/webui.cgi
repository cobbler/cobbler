#!/usr/bin/env python
#
# Web Interface for Cobbler - CGI Controller
#
# Copyright 2007 Albert P. Tobey <tobert@gmail.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import cgi
import cgitb
import Cookie
import os
import sys
import ConfigParser
from cobbler.webui.CobblerWeb import CobblerWeb

def map_modes():
    path = os.environ.get( 'PATH_INFO', 'index' )

    if path.startswith('/'):
        path = path[1:]
    if path.endswith('/'):
        path = path[:-1]

    if path is '':
        path = 'index'

    return path

def base_url():
    return os.environ.get('SCRIPT_NAME', '')

def configure():
    # FIXME: read a config file ...
    config = {
        'token':             None,
        'server':            None,
        'base_url':          None,
        'username':          None,
        'password':          None,
        'cgitb_enabled':     1     
    }

    # defaults
    if config['server'] is None:
       config['server'] = "http://127.0.0.1/cobbler_api_rw"

    if config['base_url'] is None:
        config['base_url'] = base_url()

    if ( os.access('/etc/cobbler/auth.conf', os.R_OK) ):
        config_parser = ConfigParser.ConfigParser()
        auth_conf = open("/etc/cobbler/auth.conf")
        config_parser.readfp(auth_conf)
        auth_conf.close()
        for auth in config_parser.items("xmlrpc_service_users"):
            sys.stderr.write( str(auth) )
            if auth[1].lower() != "disabled":
                config['username'] = auth[0]
                config['password'] = auth[1]

    return config

def main():
    content = "Something went wrong and I couldn't generate any content for you!"
    cw_conf = configure()
    path    = map_modes()
    form    = cgi.parse()

    # make cgitb enablement configurable
    if cw_conf['cgitb_enabled'] == 1:
        cgitb.enable()
    cw_conf.pop('cgitb_enabled')

    # exchnage single-element arrays in the 'form' dictionary for just that item
    # so there isn't a ton of 'foo[0]' craziness where 'foo' should suffice
    # - may be bad for form elements that are sometimes lists and sometimes
    # single items
    for key,val in form.items():
        if isinstance(val, list):
            if len(val) == 1:
                form[key] = val[0]

    # instantiate a CobblerWeb object
    cw = CobblerWeb( **cw_conf )

    # check for a valid path/mode
    if path in cw.modes():
        func = getattr( cw, path )
        content = func( **form )
            
    # handle invalid paths gracefully
    else:
        func = getattr( cw, 'error_page' )
        content = func( "Invalid Mode: \"%s\"" % path )

    # deliver content
    print "Content-type: text/html"
    print
    print content

main()

