#!/usr/bin/python3

import xmlrpc.client
server = xmlrpc.client.Server("http://127.0.0.1/cobbler_api")
print(server.get_distros())
print(server.get_profiles())
print(server.get_systems())
print(server.get_images())
print(server.get_repos())
