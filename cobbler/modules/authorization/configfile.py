"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources.
For instance, when using authz_ldap, you want to use authn_configfile,
not authz_allowall, which will most likely NOT do what you want.

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""


from configparser import SafeConfigParser

import os
from typing import Dict

CONFIG_FILE = '/etc/cobbler/users.conf'


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authz".
    """
    return "authz"


def __parse_config() -> Dict[str, dict]:
    """
    Parse the the users.conf file.

    :return: The data of the config file.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    config = SafeConfigParser()
    config.read(CONFIG_FILE)
    alldata = {}
    groups = config.sections()
    for g in groups:
        alldata[str(g)] = {}
        opts = config.options(g)
        for o in opts:
            alldata[g][o] = 1
    return alldata


def authorize(api_handle, user: str, resource: str, arg1=None, arg2=None) -> int:
    """
    Validate a user against a resource. All users in the file are permitted by this module.

    :param api_handle: This parameter is not used currently.
    :param user: The user to authorize.
    :param resource: This parameter is not used currently.
    :param arg1: This parameter is not used currently.
    :param arg2: This parameter is not used currently.
    :return: "0" if no authorized, "1" if authorized.
    """
    # FIXME: this must be modified to use the new ACL engine

    data = __parse_config()
    for g in data:
        if user.lower() in data[g]:
            return 1
    return 0
