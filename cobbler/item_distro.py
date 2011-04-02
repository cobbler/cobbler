"""
A cobbler distribution.  A distribution is a kernel, and initrd, and potentially
some kernel options.

Copyright 2006-2009, Red Hat, Inc
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


import utils
import item
import weakref
import os
import codes
import time
from cexceptions import *

from utils import _
import codes

# the fields has controls what data elements are part of each object.  To add a new field, just add a new
# entry to the list following some conventions to be described later.  You must also add a method called
# set_$fieldname.  Do not write a method called get_$fieldname, that will not be called.
#
# name | default | subobject default | display name | editable? | tooltip | values ? | type
#
# name -- what the filed should be called.   For the command line, underscores will be replaced with
#         a hyphen programatically, so use underscores to seperate things that are seperate words
#
# default value -- when a new object is created, what is the default value for this field?
#
# subobject default -- this applies ONLY to subprofiles, and is most always set to <<inherit>>.  If this
#                      is not item_profile.py it does not matter.  
#
# display name -- how the field shows up in the web application and the "cobbler report" command
#
# editable -- should the field be editable in the CLI and web app?  Almost always yes unless
#                it is an internalism.  Fields that are not editable are "hidden"
#
# tooltip -- the caption to be shown in the web app or in "commandname --help" in the CLI
#
# values -- for fields that have a limited set of valid options and those options are always fixed
#           (such as architecture type), the list of valid options goes in this field.  This should
#           almost always be a constant from codes.py
#
# type -- the type of the field.  Used to determine which HTML form widget is used in the web interface
#
# you will also notice some names start with "*" ... this denotes that the fields belong to
# interfaces, and only item_system.py should have these.   Each system may have multiple interfaces.
#
# the order in which the fields are listed (for all non-hidden fields) are the order they will
# appear in the web application (top to bottom).   The command line sorts fields alphabetically.
#
# field_info.py also contains a set of "Groups" that describe what other fields are associated with 
# what other fields.  This affects color coding and other display hints.  If you add a field
# please edit field_info.py carefully to match.
#
# additional:  see field_info.py for some display hints.  By default in the web app all fields
# are text fields unless field_info.py lists the field in one of those hashes.
#
# hidden fields should not be added without just cause, explanations about these are:
#
#   ctime, mtime -- times the object was modified, used internally by cobbler for API purposes
#   uid -- also used for some external API purposes
#   source_repos -- an artifiact of import, this is too complicated to explain on IRC so we just hide it 
#                   for RHEL split repos, this is a list of each of them in the install tree, used to generate
#                   repo lines in the kickstart to allow installation of x>=RHEL5.  Otherwise unimportant.
#   depth -- used for "cobbler list" to print the tree, makes it easier to load objects from disk also
#   tree_build_time -- loaded from import, this is not useful to many folks so we just hide it.  Avail over API.
#
# so to add new fields
#   (A) understand the above
#   (B) add a field below
#   (C) add a set_fieldname method
#   (D) you do not need to modify the CLI or webapp
#
# in general the set_field_name method should raise exceptions on invalid fields, always.   There are adtl
# validation fields in is_valid to check to see that two seperate fields do not conflict, but in general
# design issues that require this should be avoided forever more, and there are few exceptions.  Cobbler
# must operate as normal with the default value for all fields and not choke on the default values.

FIELDS = [
   [ "name","",0,"Name",True,"Ex: Fedora-11-i386",0,"str"],
   ["ctime",0,0,"",False,"",0,"float"],
   ["mtime",0,0,"",False,"",0,"float"],
   [ "uid","",0,"",False,"",0,"str"],
   [ "owners","SETTINGS:default_ownership",0,"Owners",True,"Owners list for authz_ownership (space delimited)",0,"list"],
   [ "kernel",None,0,"Kernel",True,"Absolute path to kernel on filesystem",0,"str"],
   [ "initrd",None,0,"Initrd",True,"Absolute path to kernel on filesystem",0,"str"],
   [ "kernel_options",{},0,"Kernel Options",True,"Ex: selinux=permissive",0,"dict"],
   [ "kernel_options_post",{},0,"Kernel Options (Post Install)",True,"Ex: clocksource=pit noapic",0,"dict"],
   [ "ks_meta",{},0,"Kickstart Metadata",True,"Ex: dog=fang agent=86", 0,"dict"],
   [ "arch",'i386',0,"Architecture",True,"", ['i386','x86_64','ia64','ppc','s390'],"str"],
   [ "breed",'redhat',0,"Breed",True,"What is the type of distribution?",codes.VALID_OS_BREEDS,"str"],
   [ "os_version","generic26",0,"OS Version",True,"Needed for some virtualization optimizations",codes.get_all_os_versions(),"str"],
   [ "source_repos",[],0,"Source Repos", False,"",0,"list"],
   [ "depth",0,0,"Depth",False,"",0,"int"],
   [ "comment","",0,"Comment",True,"Free form text description",0,"str"],
   [ "tree_build_time",0,0,"Tree Build Time",False,"",0,"str"],
   [ "mgmt_classes",[],0,"Management Classes",True,"Management classes for external config management",0,"list"],
   [ "fetchable_files",{},0,"Fetchable Files",True,"Templates for tftp or wget",0,"list"],
   [ "template_files",{},0,"Template Files",True,"File mappings for built-in config management",0,"list"],
   [ "redhat_management_key","<<inherit>>",0,"Red Hat Management Key",True,"Registration key for RHN, Spacewalk, or Satellite",0,"str"],
   [ "redhat_management_server", "<<inherit>>",0,"Red Hat Management Server",True,"Address of Spacewalk or Satellite Server",0,"str"]
]

class Distro(item.Item):

    TYPE_NAME = _("distro")
    COLLECTION_TYPE = "distro"

    def __init__(self, *args, **kwargs):
        item.Item.__init__(self, *args, **kwargs)
        self.ks_meta = {}
        self.source_repos = []

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Distro(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_fields(self):
        return FIELDS

    def get_parent(self):
        """
        Return object next highest up the tree.
        NOTE: conceptually there is no need for subdistros
        """
        return None

    def set_kernel(self,kernel):
        """
        Specifies a kernel.  The kernel parameter is a full path, a filename
        in the configured kernel directory (set in /etc/cobbler.conf) or a
        directory path that would contain a selectable kernel.  Kernel
        naming conventions are checked, see docs in the utils module
        for find_kernel.
        """
        if kernel is None or kernel == "":
            raise CX("kernel not specified")
        if utils.find_kernel(kernel):
            self.kernel = kernel
            return True
        raise CX("kernel not found: %s" % kernel)

    def set_tree_build_time(self, datestamp):
        """
        Sets the import time of the distro, for use by action_import.py.
        If not imported, this field is not meaningful.
        """
        self.tree_build_time = float(datestamp)
        return True

    def set_breed(self, breed):
        return utils.set_breed(self,breed)

    def set_os_version(self, os_version):
        return utils.set_os_version(self,os_version)

    def set_initrd(self,initrd):
        """
	Specifies an initrd image.  Path search works as in set_kernel.
	File must be named appropriately.
	"""
        if initrd is None or initrd == "":
            raise CX("initrd not specified")
        if utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        raise CX(_("initrd not found"))

    def set_redhat_management_key(self,key):
        return utils.set_redhat_management_key(self,key)

    def set_redhat_management_server(self,server):
        return utils.set_redhat_management_server(self,server)
 
    def set_source_repos(self, repos):
        """
        A list of http:// URLs on the cobbler server that point to
        yum configuration files that can be used to
        install core packages.  Use by cobbler import only.
        """
        self.source_repos = repos

    def set_arch(self,arch):
        """
        The field is mainly relevant to PXE provisioning.

        Should someone have Itanium machines on a network, having
        syslinux (pxelinux.0) be the only option in the config file causes
        problems.

        Using an alternative distro type allows for dhcpd.conf templating
        to "do the right thing" with those systems -- this also relates to
        bootloader configuration files which have different syntax for different
        distro types (because of the bootloaders).

        This field is named "arch" because mainly on Linux, we only care about
        the architecture, though if (in the future) new provisioning types
        are added, an arch value might be something like "bsd_x86".

        Update: (7/2008) this is now used to build fake PXE trees for s390x also
        """
        return utils.set_arch(self,arch)

    def check_if_valid(self):
        if self.name is None:
            raise CX("name is required")
        if self.kernel is None:
            raise CX("Error with distro %s - kernel is required" % (self.name))
        if self.initrd is None:
            raise CX("Error with distro %s - initrd is required" % (self.name))

        if utils.file_is_remote(self.kernel):
            if not utils.remote_file_exists(self.kernel):
                raise CX("Error with distro %s - kernel not found" % (self.name))
        elif not os.path.exists(self.kernel):
            raise CX("Error with distro %s - kernel not found" % (self.name))

        if utils.file_is_remote(self.initrd):
            if not utils.remote_file_exists(self.initrd):
                raise CX("Error with distro %s - initrd path not found" % 
                        (self.name))
        elif not os.path.exists(self.initrd):
            raise CX("Error with distro %s - initrd path not found" % (self.name))

