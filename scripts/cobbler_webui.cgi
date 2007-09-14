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
import os
import sys
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

def main():

    cgitb.enable()

    print "Content-type: text/html"
    print

    path = map_modes()
    form = cgi.parse()

    # ditch single-element arrays in the 'form' dictionary
    # - may be bad for form elements that are sometimes lists and sometimes
    # single items
    for key,val in form.items():
        if isinstance(val, list):
            if len(val) == 1:
                form[key] = val[0]

    cw = CobblerWeb( server="http://localhost/cobbler_api_rw", base_url=base_url(), username='testuser', password='llamas2007' )

    if path in cw.modes():
        func = getattr( cw, path )
        print func( **form )

main()
