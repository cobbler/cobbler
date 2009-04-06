"""
This is the func.virt based deploy code.
Also does power management

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
Scott Henson <shenson@redhat.com>

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

import utils
from cexceptions import *
from utils import _
import random

try:
   import func.overlord.client as func
   from func.CommonErrors import Func_Client_Exception
   FUNC=True
except ImportError:
   FUNC=False

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "deploy"

def __find_host(api, virt_group):
    """
    Find a system in the virtual group specified
    """

    systems = api.find_system(virt_group=virt_group, return_list = True)
    if len(systems) == 0:
        raise CX("No systems were found in virtual group %s" % virt_group)

    # FIXME: this logic is temporary, use something better from utils.py
    return random.choice(systems)


# -------------------------------------------------------

def deploy(api, system, virt_host = None, virt_group=None):
  
    """
    Deploy the current system to the virtual host or virtual group
    """

    if virt_host is None and virt_group is not None:
        virt_host = __find_host(virt_group)

    if virt_host is None and system.virt_group == '':
        virt_host = __find_host(system.virt_group)

    if system.virt_host != '':
        virt_host = system.virt_host

    if virt_host is None:
        raise CX("No host specified for deployment.")

    virt_host = api.find_system(virt_host)
    if virt_host is None:
        raise CX("Unable to find cobbler system record for host (%s)" % virt_host)
    host_hostname = virt_host.hostname
    if host_hostname is None or host_hostname == "":
        raise CX("Hostname for host (%s) is not set" % virt_host)

    if not FUNC:
        raise CX("Func is not installed.  Cannot use this deployment method.")

    try:
        client = func.Client(host_hostname)

        # Func has a virt.install API but the return code information from it is 
        # not super meaningful at this point, so we'll just use the raw command
        # API so we have more to show for it.

        #rc = client.virt.install(api.settings().server, system.hostname, True)[host_hostname]

        me = api.settings().server
        cmd = [ "/usr/bin/koan", "--server", me, "--virt", "--system", system.name]
        cmd = " ".join(cmd)
        (rc, out, err) = client.command.run(cmd)[host_hostname]

        # API really shouldn't "print" but this is tolerable 
        # for now until we make the api.py signature work better
        # ideally koan needs defined error codes and we can say "consult the remote
        # log" or similar.

        print out
        print err

        if rc != 0:
            raise CX("deployment failed: %s" % rc)
            # for virt.install method, result[2] is what we want
            # should we modify things to use that method of deployment
        return virt_host.name

    except Func_Client_Exception, ex:
        raise CX("A Func Exception has occured: %s"%ex)

# -------------------------------------------------------

def delete(system):
    """
    Delete the virt system
    """
    raise CX("Removing a virtual instance is not implemented yet.")

