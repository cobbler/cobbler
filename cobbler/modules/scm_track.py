"""
(C) 2009, Red Hat Inc.
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


import os

import cobbler.utils as utils

from cobbler.cexceptions import CX


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type
    :return: Always: ``/var/lib/cobbler/triggers/change/*``
    """

    return "/var/lib/cobbler/triggers/change/*"


def run(api, args):
    """
    Runs the trigger, meaning in this case track any changed which happen to a config or data file.

    :param api: The api instance of the Cobbler server. Used to look up if scm_track_enabled is true.
    :param args: The parameter is currently unused for this trigger.
    :return: 0 on success, otherwise an exception is risen.
    """
    settings = api.settings()

    if not settings.scm_track_enabled:
        # feature disabled
        return 0

    mode = str(settings.scm_track_mode).lower()
    author = str(settings.scm_track_author)
    push_script = str(settings.scm_push_script)

    if mode == "git":
        old_dir = os.getcwd()
        os.chdir("/var/lib/cobbler")
        if os.getcwd() != "/var/lib/cobbler":
            raise CX("danger will robinson")

        if not os.path.exists("/var/lib/cobbler/.git"):
            utils.subprocess_call(["git", "init"], shell=False)

        # FIXME: If we know the remote user of an XMLRPC call use them as the author
        utils.subprocess_call(["git", "add", "--all", "collections"], shell=False)
        utils.subprocess_call(["git", "add", "--all", "templates"], shell=False)
        utils.subprocess_call(["git", "add", "--all", "snippets"], shell=False)
        utils.subprocess_call(["git", "commit", "-m", "API", "update", "--author", author], shell=False)

        if push_script:
            utils.subprocess_call([push_script], shell=False)

        os.chdir(old_dir)
        return 0

    elif mode == "hg":
        # use mercurial
        old_dir = os.getcwd()
        os.chdir("/var/lib/cobbler")
        if os.getcwd() != "/var/lib/cobbler":
            raise CX("danger will robinson")

        if not os.path.exists("/var/lib/cobbler/.hg"):
            utils.subprocess_call(["hg", "init"], shell=False)

        # FIXME: If we know the remote user of an XMLRPC call use them as the user
        utils.subprocess_call(["hg", "add collections"], shell=False)
        utils.subprocess_call(["hg", "add templates"], shell=False)
        utils.subprocess_call(["hg", "add snippets"], shell=False)
        utils.subprocess_call(["hg", "commit", "-m", "API", "update", "--user", author], shell=False)

        if push_script:
            utils.subprocess_call([push_script], shell=False)

        os.chdir(old_dir)
        return 0

    else:
        raise CX("currently unsupported SCM type: %s" % mode)
