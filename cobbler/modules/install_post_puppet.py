"""
This module signs newly installed client puppet certificates if the
puppet master server is running on the same machine as the cobbler
server.

Based on:
http://www.ithiriel.com/content/2010/03/29/writing-install-triggers-cobbler
"""
import distutils.sysconfig
import sys
import utils

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"

def run(api, args, logger):
    objtype = args[0] # "system" or "profile"
    name    = args[1] # name of system or profile
    ip      = args[2] # ip or "?"

    if objtype != "system":
        return 0

    settings = api.settings()

    if not str(settings.puppet_auto_setup).lower() in [ "1", "yes", "y", "true"]:
        return 0

    if not str(settings.sign_puppet_certs_automatically).lower() in [ "1", "yes", "y", "true"]:
        return 0

    system = api.find_system(name)
    system = utils.blender(api, False, system)
    hostname = system[ "hostname" ]
    puppetca_path = settings.puppetca_path
    cmd = [puppetca_path, '--sign', hostname]

    rc = 0

    try:
        rc = utils.subprocess_call(logger, cmd, shell=False)
    except:
        if logger is not None:
            logger.warning("failed to execute %s", puppetca_path)

    if rc != 0:
        if logger is not None:
            logger.warning("signing of puppet cert for %s failed", name)

    return 0
