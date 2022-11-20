"""
Cobbler Trigger Module that puts the content of the Cobbler data directory under version control. Depending on
``scm_track_mode`` in the settings, this can either be git or Mercurial.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2009, Red Hat Inc.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


import os

from cobbler import utils

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
        utils.subprocess_call(
            ["git", "commit", "-m", "API update", "--author", author], shell=False
        )

        if push_script:
            utils.subprocess_call([push_script], shell=False)

        os.chdir(old_dir)
        return 0

    if mode == "hg":
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
        utils.subprocess_call(
            ["hg", "commit", "-m", "API", "update", "--user", author], shell=False
        )

        if push_script:
            utils.subprocess_call([push_script], shell=False)

        os.chdir(old_dir)
        return 0

    raise CX(f"currently unsupported SCM type: {mode}")
