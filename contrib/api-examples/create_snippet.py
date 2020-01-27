#!/usr/bin/python3

from xmlrpc.client import ServerProxy
import optparse

p = optparse.OptionParser()
p.add_option("-u","--user",dest="user",default="test")
p.add_option("-p","--pass",dest="password",default="test")

sp =  ServerProxy("http://127.0.0.1/cobbler_api")
(options, args) = p.parse_args()
token = sp.login(options.user,options.password)

sp.write_autoinstall_snippet("some-snippet","some content\n",token)
