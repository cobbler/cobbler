"""
Virtualization installation functions.

Copyright 2007-2008 Red Hat, Inc and Others.
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

module for creating fullvirt guests via KVM/kqemu/qemu
requires python-virtinst-0.200.
"""

import virtinstall
import utils

def start_install(*args, **kwargs):
    cmd = virtinstall.build_commandline("qemu:///system", *args, **kwargs)
    utils.subprocess_call(cmd)
