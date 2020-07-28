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


from builtins import str
import os

import cobbler.utils as utils

from cobbler.cexceptions import CX


def register():
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type
    :return: Always: ``/var/lib/cobbler/triggers/change/*``
    :rtype: str
    """

    return "/var/lib/cobbler/triggers/change/*"


def run(api, args, logger):
    """
    Runs the trigger, meaning in this case track any changed which happen to a config or data file.

    :param api: The api instance of the Cobbler server. Used to look up if scm_track_enabled is true.
    :param args: The parameter is currently unused for this trigger.
    :param logger: The logger to audit the action with.
    :return: 0 on success, otherwise an exception is risen.
    """
    settings = api.settings()
    scm_track_enabled = str(settings.scm_track_enabled).lower()

    if scm_track_enabled not in ["y", "yes", "1", "true"]:
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
            utils.subprocess_call(logger, "git init", shell=True)

        # FIXME: If we know the remote user of an XMLRPC call use them as the author
        utils.subprocess_call(logger, "git add --all collections", shell=True)
        utils.subprocess_call(logger, "git add --all templates", shell=True)
        utils.subprocess_call(logger, "git add --all snippets", shell=True)
        utils.subprocess_call(logger, "git commit -m 'API update' --author '{0}'".format(author), shell=True)

        if push_script:
            utils.subprocess_call(logger, push_script, shell=True)

        os.chdir(old_dir)
        return 0

    elif mode == "hg":
        # use mercurial
        old_dir = os.getcwd()
        os.chdir("/var/lib/cobbler")
        if os.getcwd() != "/var/lib/cobbler":
            raise CX("danger will robinson")

        if not os.path.exists("/var/lib/cobbler/.hg"):
            utils.subprocess_call(logger, "hg init", shell=True)

        # FIXME: If we know the remote user of an XMLRPC call use them as the user
        utils.subprocess_call(logger, "hg add collections", shell=True)
        utils.subprocess_call(logger, "hg add templates", shell=True)
        utils.subprocess_call(logger, "hg add snippets", shell=True)
        utils.subprocess_call(logger, "hg commit -m 'API update' --user '{0}'".format(author), shell=True)

        if push_script:
            utils.subprocess_call(logger, push_script, shell=True)

        os.chdir(old_dir)
        return 0

    else:
        raise CX("currently unsupported SCM type: %s" % mode)
