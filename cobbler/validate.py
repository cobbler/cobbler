"""
Copyright 2014. Jorgen Maas <jorgen.maas@gmail.com>

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

import os.path

from cobbler import codes
from cobbler.cexceptions import CX


def kickstart_file_path(kickstart):
    """
    Validate the kickstart file path.

    @param: str kickstart absolute path to a local kickstart file
    @returns: kickstart or CX
    """
    if kickstart == "<<inherit>>" or kickstart == "":
        return kickstart

    if not isinstance(kickstart, basestring):
        raise CX("Invalid input, kickstart must be a string")

    if kickstart.find("..") != -1:
        raise CX("Invalid kickstart template file location %s, must be absolute path" % kickstart)

    if not kickstart.startswith(codes.KICKSTART_TEMPLATE_BASE_DIR):
        raise CX("Invalid kickstart template file location %s, it is not inside %s" % (kickstart, codes.KICKSTART_TEMPLATE_BASE_DIR))

    if not os.path.isfile(kickstart):
        raise CX("Invalid kickstart template file location %s, file not found" % kickstart)

    return kickstart


# EOF
