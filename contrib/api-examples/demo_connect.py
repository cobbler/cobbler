#!/usr/bin/python3

"""
Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

from xmlrpc.client import ServerProxy
import optparse

if __name__ == "__main__":
    p = optparse.OptionParser()
    p.add_option("-u","--user",dest="user",default="test")
    p.add_option("-p","--pass",dest="password",default="test")

    # NOTE: if you've changed your xmlrpc_rw port or
    # disabled xmlrpc_rw this test probably won't work

    sp = ServerProxy("http://127.0.0.1:25151")
    (options, args) = p.parse_args()
    print("- trying to login with user=%s" % options.user)
    token = sp.login(options.user,options.password)
    print("- token: %s" % token)
    print("- authenticated ok, now seeing if user is authorized")
    check = sp.check_access(token,"imaginary_method_name")
    print("- access ok? %s" % check)
