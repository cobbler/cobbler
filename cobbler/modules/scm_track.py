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


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/change/*"


def run(api, args, logger):

    settings = api.settings()
    scm_track_enabled = str(settings.scm_track_enabled).lower()
    mode = str(settings.scm_track_mode).lower()
    author = str(settings.scm_track_author)
    push_script = str(settings.scm_push_script)

    if scm_track_enabled not in ["y", "yes", "1", "true"]:
        # feature disabled
        return 0

    if mode == "git":
        old_dir = os.getcwd()
        os.chdir("/var/lib/cobbler")
        if os.getcwd() != "/var/lib/cobbler":
            raise "danger will robinson"

        if not os.path.exists("/var/lib/cobbler/.git"):
            utils.subprocess_call(logger, "git init", shell=True)

        # FIXME: if we know the remote user of an XMLRPC call
        # use them as the author
        utils.subprocess_call(logger, "git add --all config", shell=True)
        utils.subprocess_call(logger, "git add --all autoinstall_templates", shell=True)
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
            raise "danger will robinson"

        if not os.path.exists("/var/lib/cobbler/.hg"):
            utils.subprocess_call(logger, "hg init", shell=True)

        # FIXME: if we know the remote user of an XMLRPC call
        # use them as the user
        utils.subprocess_call(logger, "hg add config", shell=True)
        utils.subprocess_call(logger, "hg add autoinstall_templates", shell=True)
        utils.subprocess_call(logger, "hg add snippets", shell=True)
        utils.subprocess_call(logger, "hg commit -m 'API update' --user '{0}'".format(author), shell=True)

        if push_script:
            utils.subprocess_call(logger, push_script, shell=True)

        os.chdir(old_dir)
        return 0

    else:
        raise CX("currently unsupported SCM type: %s" % mode)
