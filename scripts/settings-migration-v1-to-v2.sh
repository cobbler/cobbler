#!/bin/bash

#set -x
path_modules_conf="/etc/cobbler/modules.conf"
default_file=""
flag_regex_conversion=false
flag_static_conversion=false
flag_replace_conversion=false

read -r -d '' default_file <<EOM
# cobbler module configuration file
# =================================

# authentication:
# what users can log into the WebUI and Read-Write XMLRPC?
# choices:
#    authentication.denyall    -- no one (default)
#    authentication.configfile -- use /etc/cobbler/users.digest (for basic setups)
#    authentication.passthru   -- ask Apache to handle it (used for kerberos)
#    authentication.ldap       -- authenticate against LDAP
#    authentication.spacewalk  -- ask Spacewalk/Satellite (experimental)
#    authentication.pam        -- use PAM facilities
#    authentication.testing    -- username/password is always testing/testing (debug)
#    (user supplied)  -- you may write your own module
# WARNING: this is a security setting, do not choose an option blindly.
# for more information:
# https://github.com/cobbler/cobbler/wiki/Cobbler-web-interface
# https://github.com/cobbler/cobbler/wiki/Security-overview
# https://github.com/cobbler/cobbler/wiki/Kerberos
# https://github.com/cobbler/cobbler/wiki/Ldap

[authentication]
module = authentication.configfile

# authorization:
# once a user has been cleared by the WebUI/XMLRPC, what can they do?
# choices:
#    authorization.allowall   -- full access for all authneticated users (default)
#    authorization.ownership  -- use users.conf, but add object ownership semantics
#    (user supplied)  -- you may write your own module
# WARNING: this is a security setting, do not choose an option blindly.
# If you want to further restrict cobbler with ACLs for various groups,
# pick authz_ownership.  authz_allowall does not support ACLs.  configfile
# does but does not support object ownership which is useful as an additional
# layer of control.

# for more information:
# https://github.com/cobbler/cobbler/wiki/Cobbler-web-interface
# https://github.com/cobbler/cobbler/wiki/Security-overview
# https://github.com/cobbler/cobbler/wiki/Web-authorization

[authorization]
module = authorization.allowall

# dns:
# chooses the DNS management engine if manage_dns is enabled
# in /etc/cobbler/settings, which is off by default.
# choices:
#    managers.bind    -- default, uses BIND/named
#    managers.dnsmasq -- uses dnsmasq, also must select dnsmasq for dhcp below
#    managers.ndjbdns -- uses ndjbdns
# NOTE: more configuration is still required in /etc/cobbler
# for more information:
# https://github.com/cobbler/cobbler/wiki/Dns-management

[dns]
module = managers.bind

# dhcp:
# chooses the DHCP management engine if manage_dhcp is enabled
# in /etc/cobbler/settings, which is off by default.
# choices:
#    managers.isc     -- default, uses ISC dhcpd
#    managers.dnsmasq -- uses dnsmasq, also must select dnsmasq for dns above
# NOTE: more configuration is still required in /etc/cobbler
# for more information:
# https://github.com/cobbler/cobbler/wiki/Dhcp-management

[dhcp]
module = managers.isc

# tftpd:
# chooses the TFTP management engine if manage_tftp is enabled
# in /etc/cobbler/settings, which is ON by default.
#
# choices:
#    managers.in_tftpd -- default, uses the system's tftp server
#    managers.tftpd_py -- uses cobbler's tftp server
#

[tftpd]
module = managers.in_tftpd

#--------------------------------------------------
EOM

print_help() {
  echo "$(basename "$0") [-h] [-r] [-s] [-n] [-f absolute_filepath]"
  echo "Script to migrate a Cobbler 3.0.0 or prior \"modules.conf\" to a 3.0.1 \"modules.conf\""
  echo ""
  echo "Usage:"
  echo "   One of the following arguments must be choosen [rsn] additionally you must hand over the absolute path of"
  echo "   the \"modules.conf\""
  echo ""
  echo "Options:"
  echo "  -h  show this help text"
  echo "  -r  Use the regex replace. I recommend this if you have custom modules and also have rearranged them."
  echo "      WARNING: This also alters the documentation in the settings file which is wrong to the current point"
  echo "               in time."
  echo "  -s  Use the static replace. I recomment this if you use the default modules."
  echo "  -n  Make a new start with Cobbler and just replace the whole settings file."
  echo "  -f  Path to the \"modules.conf\""
}

regex_conversion() {
  sed -i -e 's/authn_/authentication\./g' $path_modules_conf
  sed -i -e 's/authz_/authorization\./g' $path_modules_conf
  sed -i -e 's/manage_/managers\./g' $path_modules_conf
}

static_conversion() {
  sed -i -e 's/authn_denyall/authentication.denyall/g' $path_modules_conf
  sed -i -e 's/authn_configfile/authentication.configfile/g' $path_modules_conf
  sed -i -e 's/authn_passthru/authentication.passthru/g' $path_modules_conf
  sed -i -e 's/authn_ldap/authentication.ldap/g' $path_modules_conf
  sed -i -e 's/authn_spacewalk/authentication.spacewalk/g' $path_modules_conf
  sed -i -e 's/authn_pam/authentication.pam/g' $path_modules_conf
  sed -i -e 's/authn_testing/authentication.testing/g' $path_modules_conf
  sed -i -e 's/authz_allowall/authorization.allowall/g' $path_modules_conf
  sed -i -e 's/authz_ownership/authorization.ownership/g' $path_modules_conf
  sed -i -e 's/manage_bind/managers.bind/g' $path_modules_conf
  sed -i -e 's/manage_dnsmasq/managers.dnsmasq/g' $path_modules_conf
  sed -i -e 's/manage_ndjbdns/managers.ndjbdns/g' $path_modules_conf
  sed -i -e 's/manage_isc/managers.isc/g' $path_modules_conf
  sed -i -e 's/manage_dnsmasq/managers.dnsmasq/g' $path_modules_conf
  sed -i -e 's/manage_in_tftpd/managers.in_tftpd/g' $path_modules_conf
  sed -i -e 's/manage_tftpd_py/managers.tftpd_py/g' $path_modules_conf
}

replace_modules_conf() {
  rm $path_modules_conf
  touch $path_modules_conf
  echo "$default_file" >$path_modules_conf
}

run() {
  if $flag_regex_conversion; then
    regex_conversion
  elif $flag_static_conversion; then
    static_conversion
  elif $flag_replace_conversion; then
    replace_modules_conf
  fi
}

wrong_options() {
  echo "Error:"
  echo "You selected the wrong number of flags. Please read the usage!"
  echo ""
  print_help
}

validate_options() {
  if $flag_regex_conversion && $flag_static_conversion && $flag_replace_conversion; then
    print_help
    exit 1
  elif $flag_regex_conversion && $flag_static_conversion; then
    print_help
    exit 1
  elif $flag_regex_conversion && $flag_replace_conversion; then
    print_help
    exit 1
  fi
}

parse_options() {
  while getopts 'hrsnf:' option; do
    case "$option" in
    h)
      print_help
      exit
      ;;
    r)
      flag_regex_conversion=true
      ;;
    s)
      flag_static_conversion=true
      ;;
    n)
      flag_replace_conversion=true
      ;;
    f)
      path_modules_conf=$OPTARG
      ;;
    :)
      printf "Error:"
      printf "Missing argument for -%f\n" "$OPTARG" >&2
      print_help
      exit 1
      ;;
    \?)
      printf "Error:"
      printf "Illegal option: -%s\n" "$OPTARG" >&2
      echo ""
      print_help
      exit 1
      ;;
    esac
  done
  shift $((OPTIND - 1))
}

# Main routine
parse_options "$@"
validate_options
run
