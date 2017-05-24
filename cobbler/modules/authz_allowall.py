"""
Authorization module that allows everything, which is the default
for new cobbler installs.

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


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authz"


def authorize(api_handle, user, resource, arg1=None, arg2=None):
    """
    Validate a user against a resource.
    NOTE: acls are not enforced as there is no group support in this module
    """
    return True
