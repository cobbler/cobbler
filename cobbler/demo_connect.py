#!/usr/bin/python

"""
Copyright 2007, Red Hat, Inc

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from xmlrpclib import ServerProxy
import optparse

if __name__ == "__main__":
    p = optparse.OptionParser()
    p.add_option("-u","--user",dest="user",default="test")
    p.add_option("-p","--pass",dest="password",default="test")

    # NOTE: if you've changed your xmlrpc_rw port or 
    # disabled xmlrpc_rw this test probably won't work

    sp = ServerProxy("http://127.0.0.1:25152")
    (options, args) = p.parse_args()
    print "- trying to login with user=%s" % options.user
    token = sp.login(options.user,options.password)
    print "- token: %s" % token
    print "- authenticated ok, now seeing if user is authorized"
    check = sp.check_access(token,"imaginary_method_name")
    print "- access ok? %s" % check



