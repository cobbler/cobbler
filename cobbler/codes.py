
"""
various codes and constants used by Cobbler


Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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


# OS variants table.  This is a variance of the data from 
# ls /usr/lib/python2.X/site-packages/virtinst/FullVirtGuest.py
# but replicated here as we can't assume cobbler is installed on a system with libvirt.
# in many cases it will not be (i.e. old EL4 server, etc) and we need this info to
# know how to validate --os-variant and --os-version. 
#
# The keys of this hash correspond with the --breed flag in Cobbler.
# --breed has physical provisioning semantics as well as virt semantics.
#
# presense of something in this table does /not/ mean it's supported.
# for instance, currently, "redhat", "debian", and "suse" do something interesting.
# the rest are undefined (for now), this will evolve.

VALID_OS_BREEDS = [
    "redhat", "debian", "ubuntu", "suse", "generic", "windows", "unix", "other"
]

VALID_OS_VERSIONS = {
    "redhat"  : [ "rhel2.1", "rhel3", "rhel4", "rhel5", "fedora5", "fedora6", "fedora7", "fedora8", "fedora9", "fedora10", "generic24", "generic26", "other" ],
    "suse"    : [ "sles10", "generic24", "generic26", "other" ],
    "debian"  : [ "etch", "lenny", "generic24", "generic26", "other" ],
    "ubuntu"  : [ "dapper", "hardy", "intrepid", "jaunty" ],
    "generic" : [ "generic24", "generic26", "other" ],
    "windows" : [ "winxp", "win2k", "win2k3", "vista", "other" ],
    "unix"    : [ "solaris9", "solaris10", "freebsd6", "openbsd4", "other" ],
    "other"   : [ "msdos", "netware4", "netware5", "netware6", "generic", "other" ]
}

VALID_REPO_BREEDS = [
    "rsync", "rhn", "yum", "apt"
]

