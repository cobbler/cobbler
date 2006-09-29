"""
Messages used by cobbler.
This module encapsulates strings so they can
be reused and potentially translated.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

_msg_table = {
  "system"          : "System",
  "profile"         : "Profile",
  "distribution"    : "Distribution",
  "bad_server"      : "The 'server' field in /var/lib/cobbler/settings must be set to something other than localhost, or kickstarting features will not work",
  "parse_error"     : "cobbler could not read %s, replacing...",
  "no_ssh"          : "cobbler can't read ~/.ssh/id_dsa.pub",
  "exc_koan_path"   : "koan_path in /var/lib/cobbler/settings is invalid",
  "no_create"       : "cobbler could not create: %s",
  "no_delete"       : "cobbler could not delete: %s",
  "no_args"         : "this command requires arguments.",
  "missing_options" : "cannot perform this action, more arguments are required",
  "enchant_args"    : "usage: cobbler enchant --name=<string> --profile=<string> --password=<string>\n",
  "enchant_failed"  : "enchant failed (%s)",
  "unknown_cmd"     : "cobbler doesn't understand '%s'",
  "bad_arg"         : "cobbler was expecting an equal sign in argument '%s'",
  "reject_arg"      : "the value of parameter '%s' isn't valid",
  "weird_arg"       : "this command doesn't take a parameter named '%s'",
  "bad_sys_name"    : "system name must be a MAC, IP, or resolveable host",
  "usage"           : "for help, see 'man cobbler'",
  "need_to_fix"     : "the following potential problems were detected:",
  "need_perms"      : "cobbler could not access %s",
  "need_perms2"     : "cobbler could not copy %s to %s",
  "no_dhcpd"        : "cobbler couldn't find dhcpd, try 'yum install dhcpd'",
  "no_bootloader"   : "missing 1 or more bootloader files listed in /var/lib/cobbler/settings",
  "no_tftpd"        : "cobbler couldn't find tftpd, try 'yum install tftpd'",
  "no_dir"          : "cobbler couldn't find %s, please create it",
  "chg_attrib"      : "need to change field '%s' value to '%s' in file '%s'",
  "no_exist"        : "file %s does not exist",
  "no_line"         : "file '%s' should have a line '%s' somewhere",
  "no_next_server"  : "file '%s' should have a next-server line",
  "no_dir2"         : "can't find %s for %s as referenced in /var/lib/cobbler/settings",
  "bad_param"       : "at least one parameter is missing for this function",
  "empty_list"      : "There are no configured %s records.",
  "err_resolv"      : "The system name (%s) did not resolve",
  "err_kickstart"   : "The kickstart (%s) for item (%s) is not valid",
  "err_kickstart2"  : "Error while mirroring kickstart file (%s) to (%s)",
  "orphan_profile"  : "Removing this system would break profile '%s'",
  "orphan_profile2" : "system (%s) references a non-existant profile (%s)",
  "orphan_distro2"  : "profile (%s) references a non-existant distro (%s)",
  "orphan_system"   : "Removing this profile would break system '%s'",
  "delete_nothing"  : "can't delete something that doesn't exist",
  "no_distro"       : "distro does not exist",
  "no_profile"      : "profile does not exist",
  "no_kickstart"    : "kickstart must be an absolute path, or an http://, ftp:// or nfs:// URL",
  "no_kernel"       : "cannot find kernel file",
  "sync_kernel"     : "the kernel (%s) for distro (%s) cannot be found and must be fixed",
  "sync_initrd"     : "the initrd (%s) for distro (%s) cannot be found and must be fixed",
  "sync_mirror_ks"  : "mirroring local kickstarts...",
  "sync_buildtree"  : "building trees",
  "sync_processing" : "processing: %s",
  "writing"         : "writing file: %s",
  "mkdir"           : "creating: %s",
  "dryrun"          : "dry run | %s",
  "copying"         : "copying file: %s to %s",
  "removing"        : "removing: %s",
  "no_initrd"       : "cannot find initrd",
  "exc_xen_name"    : "invalid Xen name",
  "exc_xen_file"    : "invalid Xen file size",
  "exc_xen_ram"     : "invalid Xen RAM size",
  "exc_xen_mac"     : "invalid Xen mac address",
  "exc_xen_para"    : "invalid Xen paravirtualization setting",
  "exc_profile"     : "invalid profile name",
  "exc_profile2"    : "profile name not set",
  "exc_pxe_arch"    : "valid PXE architectures: standard or ia64",
  "exc_no_template" : "can't read /etc/cobbler/dhcp.template",
  "exc_dhcp_nomac"  : "when cobbler is managing dhcpd.conf, all system names must be MAC addresses.  Aborting.", 
  "check_ok"        : """
No setup problems found.

Manual editing of /var/lib/cobbler/settings and dhcpd.conf is suggested to tailor them to your specific configuration.  Furthermore, it's important to know that cobbler can't completely understnad what you intend to do with dhcpd.conf, but it looks like there is at least some PXE related information in it.  We'll leave this up to you.

Good luck.
""",
  "help"           : "see 'man cobbler'"
}

def lookup(key):
   """
   Return the lookup of a string key.
   """
   if _msg_table.has_key(key):
       return _msg_table[key]
   return key
