"""
Authentication module that defers to Apache and trusts
what Apache trusts.

Copyright 2008-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

from cobbler import utils


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """
    return "authn"


def authenticate(api_handle, username, password) -> bool:
    """
    Validate a username/password combo. Uses cobbler_auth_helper

    :param api_handle: This parameter is not used currently.
    :param username: This parameter is not used currently.
    :param password: This should be the internal Cobbler secret.
    :return: True if the password is the secret, otherwise false.
    """
    return password == utils.get_shared_secret()
