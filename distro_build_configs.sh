#!/bin/bash

export DATAPATH="/usr/share/cobbler"
export DOCPATH="/usr/share/man"
export ETCPATH="/etc/cobbler"
export LIBPATH="/var/lib/cobbler"
export LOGPATH="/var/log"
export COMPLETION_PATH="/usr/share/bash-completion/completions"
export STATEPATH="/tmp/cobbler_settings/devinstall"

export HTTPD_SERVICE="apache2.service"
export WEBROOT="/srv/www";
export WEBCONFIG="/etc/apache2/vhosts.d";
export WEBROOTCONFIG="/etc/apache2";
export TFTPROOT="/srv/tftpboot"
export ZONEFILES="/var/lib/named"
export DEFAULTPATH="etc/sysconfig"
export SHIM_FOLDER="/usr/share/efi/*/"
export SHIM_FILE="shim\.efi"
export IPXE_FOLDER="/usr/share/ipxe/"
export PXELINUX_FOLDER="/usr/share/syslinux"
export MEMDISK_FOLDER="/usr/share/syslinux"
export SYSLINUX_DIR="/usr/share/syslinux"
export GRUB_MOD_FOLDER="/usr/share/grub2"

# First parameter is DISTRO if provided
[ $# -ge 2 ] && DISTRO="$1"

if [ "$DISTRO" = "" ] && [ -r /etc/os-release ];then
    source /etc/os-release
    case $ID in
	sle*|*suse*)
	    DISTRO="SUSE"
	    ;;
	fedora*|ol*|centos*|rhel*|rocky*)
	    DISTRO="FEDORA"
	    ;;
	ubuntu*|debian*)
	    DISTRO="UBUNTU"
	    ;;
    esac
fi

if [ "$DISTRO" = "SUSE" ];then
    export APACHE_USER="wwwrun"
    export APACHE_GROUP="www"
elif [ "$DISTRO" = "UBUNTU" ];then
    export APACHE_USER="www-data"
    export HTTP_USER=$APACHE_USER # overrule setup.py
    export APACHE_GROUP="www-data"
    export WEBROOT="/var/www"
    export WEBCONFIG="/etc/apache2/conf-available"
    export ZONEFILES="/etc/bind/db."
    export DEFAULTPATH="etc/default"
    export SHIM_FOLDER="/usr/lib/shim/"
    export SHIM_FILE="shim.*\.efi\.signed"
    export IPXE_FOLDER="/usr/lib/ipxe/"
    export PXELINUX_FOLDER="/usr/lib/PXELINUX/"
    export MEMDISK_FOLDER="/usr/lib/syslinux/"
    export SYSLINUX_DIR="/usr/lib/syslinux/modules/bios/"
    export GRUB_MOD_FOLDER="/usr/lib/grub"
elif [ "$DISTRO" = "FEDORA" ];then
    export APACHE_USER="apache"
    export HTTP_USER=$APACHE_USER # overrule setup.py
    export APACHE_GROUP="apache"
    export HTTPD_SERVICE="httpd.service"
    export WEBROOT="/var/www"
    export WEBCONFIG="/etc/httpd/conf.d"
    export WEBROOTCONFIG="/etc/httpd"
    export TFTPROOT="/var/lib/tftpboot"
    export ZONEFILES="/var/named"
    export SHIM_FOLDER="/boot/efi/EFI/*/"
    export SHIM_FILE="shim[a-zA-Z0-9]*\.efi"
    export GRUB_MOD_FOLDER="/usr/lib/grub"
else
    echo "ERROR, unknown distro $DISTRO"
    # ToDo: Should we loudly warn here?
fi
