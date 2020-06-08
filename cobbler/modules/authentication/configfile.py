"""
Authentication module that uses /etc/cobbler/auth.conf
Choice of authentication module is in /etc/cobbler/modules.conf

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

import hashlib
import os

from cobbler.module_loader import get_module_name


def hashfun(text):
    """
    Converts a str object to a hash which was configured in modules.conf of the Cobbler settings.

    :param text: The text to hash.
    :type text: str
    :return: The hash of the text. This should output the same hash when entered the same text.
    """
    hashfunction = get_module_name("authentication", "hash_algorithm", "sha3_512")
    if hashfunction == "sha3_224":
        hashalgorithm = hashlib.sha3_224(text.encode('utf-8'))
    elif hashfunction == "sha3_384":
        hashalgorithm = hashlib.sha3_384(text.encode('utf-8'))
    elif hashfunction == "sha3_256":
        hashalgorithm = hashlib.sha3_256(text.encode('utf-8'))
    elif hashfunction == "sha3_512":
        hashalgorithm = hashlib.sha3_512(text.encode('utf-8'))
    elif hashfunction == "blake2b":
        hashalgorithm = hashlib.blake2b(text.encode('utf-8'))
    elif hashfunction == "blake2s":
        hashalgorithm = hashlib.blake2s(text.encode('utf-8'))
    elif hashfunction == "shake_128":
        hashalgorithm = hashlib.shake_128(text.encode('utf-8'))
    elif hashfunction == "shake_256":
        hashalgorithm = hashlib.shake_256(text.encode('utf-8'))
    else:
        errortext = "The hashfunction (Currently: %s) must be one of the defined in /etc/cobbler/modules.conf!" \
                    % hashfunction
        raise ValueError(errortext)
    return hashalgorithm.hexdigest()


def register():
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def __parse_storage():
    """
    Parse the users.digest file and return all users.

    :return: A list of all users. A user is a sublist which has three elements: username, realm and passwordhash.
    :rtype: list
    """
    if not os.path.exists("/etc/cobbler/users.digest"):
        return []
    with open("/etc/cobbler/users.digest", encoding='utf-8') as fd:
        data = fd.read()
    results = []
    lines = data.split("\n")
    for line in lines:
        try:
            line = line.strip()
            tokens = line.split(":")
            results.append([tokens[0], tokens[1], tokens[2]])
        except:
            pass
    return results


def authenticate(api_handle, username, password):
    """
    Validate a username/password combo.

    Thanks to http://trac.edgewall.org/ticket/845 for supplying the algorithm info.

    :param api_handle: Unused in this implementation.
    :param username: The username to log in with. Must be contained in /etc/cobbler/users.digest
    :type username: str
    :param password: The password to log in with. Must be contained hashed in /etc/cobbler/users.digest
    :type password: str
    :return: A boolean which contains the information if the username/password combination is correct.
    :rtype: bool
    """

    userlist = __parse_storage()
    for (user, realm, passwordhash) in userlist:
        if user == username and realm == "Cobbler":
            calculated_passwordhash = hashfun(password)
            print("Passwordhash: %s" % passwordhash)
            print("Calculated Passwordhash: %s" % calculated_passwordhash)
            if calculated_passwordhash == passwordhash:
                return True
    return False
