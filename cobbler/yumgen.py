"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc and Others
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

import pathlib

from cobbler import templar
from cobbler import utils


class YumGen:

    def __init__(self, api):
        """
        Constructor

        :param api: The main API instance which is used by the current running server.
        """
        self.api = api
        self.settings = api.settings()
        self.templar = templar.Templar(self.api)

    def get_yum_config(self, obj, is_profile: bool) -> str:
        """
        Return one large yum repo config blob suitable for use by any target system that requests it.

        :param obj: The object to generate the yumconfig for.
        :param is_profile: If the requested object is a profile. (Parameter not used currently)
        :return: The generated yumconfig or the errors.
        """

        totalbuf = ""

        blended = utils.blender(self.api, False, obj)

        input_files = []

        # Tack on all the install source repos IF there is more than one. This is basically to support things like
        # RHEL5 split trees if there is only one, then there is no need to do this.

        included = {}
        for r in blended["source_repos"]:
            filename = pathlib.Path(self.settings.webdir).joinpath("/", "/".join(r[0].split("/")[4:]))
            if filename not in included:
                input_files.append(filename)
            included[filename] = 1

        for repo in blended["repos"]:
            path = pathlib.Path(self.settings.webdir).joinpath("repo_mirror", repo, "config.repo")
            if path not in included:
                input_files.append(path)
            included[path] = 1

        for infile in input_files:
            try:
                infile_h = open(infile)
            except:
                # File does not exist and the user needs to run reposync before we will use this, Cobbler check will
                # mention this problem
                totalbuf += "\n# error: could not read repo source: %s\n\n" % infile
                continue

            infile_data = infile_h.read()
            infile_h.close()
            outfile = None  # disk output only
            totalbuf += self.templar.render(infile_data, blended, outfile)
            totalbuf += "\n\n"

        return totalbuf
