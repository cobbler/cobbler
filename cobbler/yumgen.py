"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import pathlib
from typing import TYPE_CHECKING, List

from cobbler import templar, utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.base_item import BaseItem


class YumGen:
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor

        :param api: The main API instance which is used by the current running server.
        """
        self.api = api
        self.settings = api.settings()
        self.templar = templar.Templar(self.api)

    def get_yum_config(self, obj: "BaseItem", is_profile: bool) -> str:
        """
        Return one large yum repo config blob suitable for use by any target system that requests it.

        :param obj: The object to generate the yumconfig for.
        :param is_profile: If the requested object is a profile. (Parameter not used currently)
        :return: The generated yumconfig or the errors.
        """

        totalbuf = ""

        blended = utils.blender(self.api, False, obj)  # type: ignore

        input_files: List[pathlib.Path] = []

        # Tack on all the install source repos IF there is more than one. This is basically to support things like
        # RHEL5 split trees if there is only one, then there is no need to do this.

        included = {}
        for repo in blended["source_repos"]:
            filename = pathlib.Path(self.settings.webdir).joinpath(
                "/".join(repo[0].split("/")[4:])
            )
            if filename not in included:
                input_files.append(filename)
            included[filename] = 1

        for repo in blended["repos"]:
            path = pathlib.Path(self.settings.webdir).joinpath(
                "repo_mirror", repo, "config.repo"
            )
            if path not in included:
                input_files.append(path)
            included[path] = 1

        for infile in input_files:
            try:
                with open(infile, encoding="UTF-8") as infile_h:
                    infile_data = infile_h.read()
            except Exception:
                # File does not exist and the user needs to run reposync before we will use this, Cobbler check will
                # mention this problem
                totalbuf += f"\n# error: could not read repo source: {infile}\n\n"
                continue

            outfile = None  # disk output only
            totalbuf += self.templar.render(infile_data, blended, outfile)
            totalbuf += "\n\n"

        return totalbuf
