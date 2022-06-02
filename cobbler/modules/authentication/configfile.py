"""
Authentication module that uses /etc/cobbler/auth.conf
Choice of authentication module is in /etc/cobbler/modules.conf
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


import hashlib
import os
from typing import List

from cobbler.module_loader import get_module_name


def hashfun(text: str) -> str:
    """
    Converts a str object to a hash which was configured in modules.conf of the Cobbler settings.

    :param text: The text to hash.
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


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def __parse_storage() -> List[List[str]]:
    """
    Parse the users.digest file and return all users.

    :return: A list of all users. A user is a sublist which has three elements: username, realm and passwordhash.
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


def authenticate(api_handle, username: str, password: str) -> bool:
    """
    Validate a username/password combo.

    Thanks to http://trac.edgewall.org/ticket/845 for supplying the algorithm info.

    :param api_handle: Unused in this implementation.
    :param username: The username to log in with. Must be contained in /etc/cobbler/users.digest
    :param password: The password to log in with. Must be contained hashed in /etc/cobbler/users.digest
    :return: A boolean which contains the information if the username/password combination is correct.
    """

    userlist = __parse_storage()
    for (user, realm, passwordhash) in userlist:
        if user == username and realm == "Cobbler":
            calculated_passwordhash = hashfun(password)
            if calculated_passwordhash == passwordhash:
                return True
    return False
