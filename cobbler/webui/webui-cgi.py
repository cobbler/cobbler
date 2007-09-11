#!/usr/bin/env python

import cgi
import cgitb
import wsgiref
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

    cw = CobblerWeb( server="http://localhost:25151", base_url=base_url() )

    if path in cw.modes():
        func = getattr( cw, path )
        print func( **form )

main()
