export DOCPATH="share/man"
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
export DEFAULTPATH="etc/sysconfig"

# First parameter is DISTRO if provided
[ $# -ge 2 ] && DISTRO="$1"

if [ "$DISTRO" = "" ] && [ -r /etc/os-release ];then
    source /etc/os-release
    case $ID in
	sle*|*suse*)
	    DISTRO="SUSE"
	    ;;
	fedora*|centos*)
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
    export APACHE_GROUP="www-data"

    export WEBCONFIG="/etc/apache2/conf-available";
    export DEFAULTPATH="etc/default"
elif [ "$DISTRO" = "FEDORA" ];then
    export APACHE_USER="apache"
    export APACHE_GROUP="apache"

    export HTTPD_SERVICE="httpd.service"
    export WEBROOT="/var/www";
    export WEBCONFIG="/etc/httpd/conf.d";
    export WEBROOTCONFIG="/etc/httpd";
    export TFTPROOT="/var/lib/tftpboot"
else
    echo "ERROR, unknown distro $DISTRO"
    # ToDo: Should we loudly warn here?
fi
