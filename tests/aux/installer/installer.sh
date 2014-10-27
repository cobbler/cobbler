#!/bin/bash

# Automates Cobbler installation from source code
#
# * scope: add yum repositories, install required dependencies, install proftpd
#   FTP server, install ISC DHCP server, install fence-agents, install Cobbler
# * supports CentOS/RHEL Server 6.5/7 distributions, x86_64/ppc64 architectures.
#   ppc64 architecture is only supported in RHEL.
# * pre-requisites:
#  * have list of yum repositories which have all required rpm packages.
#   * CentOS 6.5/7 x86_64: os (eg http://mirror.centos.org/centos/<centos_version>/os/x86_64/Packages/)
#     and updates (eg http://mirror.centos.org/centos/<centos_version>/updates/x86_64/Packages/)
#   * RHEL Server 6.5/7 x86_64/ppc64: os and updates
#  * if target system is behind a firewall, add firewall exceptions from target
#    system to following systems:
#   * ftp.proftpd.org: port 21
#   * git.fedorahosted.org: port 80
#   * github.com: port 80
#   * mirror.centos.org: port 80 (if architecture is ppc64)
#   * python-distribute.org: port 80
#   * raw.github.com: port 443
#   * <yum repositories>: port 21 (ftp) or port 80 (http)
#  * have a clean minimum installation of one of the supported Linux distributions in the
#    target system
#  * have root access to target system
# * how to run:
#  * copy installer directory to target system
#  * run installer script in the target system as root user
#
# @IMPROVEMENT: improve error handling
# @IMPROVEMENT: support other Linux distributions. Consider using a configuration
# management tool instead of a shell script.

# Command example:
# ./installer.sh --ip "9.111.111.111" --repositories "centos6-os;Cent OS 6 - base;http://mirror.centos.org/centos/6.5/os/x86_64/Packages/,centos6-updates;Cent OS 6 - updates;http://mirror.centos.org/centos/6.5/updates/x86_64/Packages/" --subnets "9.111.112.0;255.255.255.0,9.111.113.0;255.255.255.0"

# directory where conf files and other scripts (like init.d) are
datadir="./data"

# Validate an IP address
#
# @param ip IP address
# @return 0 if IP is valid, 1 otherwise
function validate_ip_address()
{
    local  ip=$1
    local  stat=1

    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        OIFS=$IFS
        IFS='.'
        ip=($ip)
        IFS=$OIFS
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
            && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        stat=$?
    fi
    return $stat
}

# Get a remote file using wget (Linux command line tool)
#
# @param url file's remote URL
# @param dest_path destination path
function get_remote_file_wget()
{

local url="$1"
local dest_path="$2"

wget --no-check-certificate -P $dest_path $url

}

# Clone a git repository
#
# @param server git server IP/hostname
# @param project repository directory
# @param repository repository name
function clone_repo ()
{

local server="$1"
local project="$2"
local repository="$3"

/usr/bin/expect << EOD
    spawn git clone https://$server/$project/$repository.git
    expect "yes/no" { send "yes\r" ; exp_continue }
    expect "Resolving deltas: 100% * done"
    sleep 1
    exit
EOD

}

# Disable Linux firewall
#
# @param redhat_version Red Hat distribution's major version
function disable_firewall ()
{

    local redhat_version="$1"

    if [ $redhat_version == "6" ]; then
        iptables --flush
        service iptables stop
        chkconfig iptables off
    else
        systemctl disable firewalld
        systemctl stop firewalld
    fi

}

# Add yum repositories
#
# @param repositories_in array of yum repositories. Each item in the array
#        is an array with 3 elements: section name, repository name and
#        repository URL
function add_yum_repositories ()
{

    local repositories_in="$1"
    echo $repositories_in

    OIFS="$IFS"
    IFS=','
    read -a repositories <<< "${repositories_in}"
    local num_repositories=${#repositories[@]}
    echo "num of input repositories: $num_repositories"

    # generate yum repository file
    local repos_filepath=/etc/yum.repos.d/cobbler.repo
    rm -f $repos_filepath
    for (( i=0; i<${num_repositories}; i++ ));
    do
        IFS=';'
        read -a repo_array <<< "${repositories[$i]}"
        echo "repository $i: ${repositories[$i]}"
        echo "section name ${repo_array[0]}"
        local section_name="${repo_array[0]}"
        local repo_name="${repo_array[1]}"
        local repo_base_url="${repo_array[2]}"


        cat >> $repos_filepath << EOF
[$section_name]
name=$repo_name
baseurl=$repo_base_url
gpgcheck=0
EOF
    done

    # restore IFS
    IFS="$OIFS"

}

# Install PIP, required to install some Python dependencies not available in
# RPM packages
function install_pip()
{

    pushd "/tmp"
    get_remote_file_wget "https://raw.github.com/pypa/pip/master/contrib/get-pip.py"  "."
    python get-pip.py
    rm -f get-pip.py
    popd
}

# Install ProFTPd FTP server
function install_proftpd ()
{

    local proftpd_version="1.3.5"
    local url="ftp://ftp.proftpd.org/distrib/source/proftpd-$proftpd_version.tar.gz"

    # install build dependencies
    yum -y install gcc

    # installs FTP server
    pushd "/tmp"
    get_remote_file_wget $url "."
    tar xzf proftpd-$proftpd_version.tar.gz
    cd proftpd-$proftpd_version/
    ./configure
    make
    make install
    cd ../
    rm -rf proftpd-$proftpd_version
    rm -f proftpd-$proftpd_version.tar.gz
    popd

}

# Configure ProFTPd FTP server
function configure_proftpd ()
{

    local proftpd_conf="/usr/local/etc/proftpd.conf"

    # create log dir
    mkdir -p /var/log/proftpd

    cp $datadir/init.d/proftpd /etc/init.d/proftpd
    chmod 0744 /etc/init.d/proftpd

    sed -i "s/ServerName.*$/ServerName			Cobbler server" $proftpd_conf
    sed -i "s/^User\s*nobody$/User				ftp/" $proftpd_conf
    sed -i "s/^Group\s*nogroup$/Group				ftp/" $proftpd_conf
    sed -i "s/  User\s+nobody$/  User			ftp/" $proftpd_conf
    sed -i "s/  Group\s+nogroup$/  Group			ftp/" $proftpd_conf

}

# Install DHCP server
function install_dhcp_server ()
{

    yum -y install dhcp

    # DHCP server is not started because default dhcpd conf file does not work
    # wait and start DHCP server after Cobbler generates dhcpd.conf
}

# Install fence agents
#
# @param arch system architecture
# @param redhat_version Red Hat distribution's major version
function install_fence_agents()
{

    local arch="$1"
    local redhat_version="$2"

    # Linux packages dependencies, installed via YUM package manager
    # build dependencies
    local dependencies="autoconf automake gcc git libtool libxslt nss nss-devel python-devel python-setuptools python-suds"
    # runtime dependencies
    dependencies="$dependencies ipmitool telnet"
    if [ $arch == "x86_64" ]; then
        dependencies="$dependencies perl-Net-Telnet"
    fi
    if [ $redhat_version != "6" ]; then
        dependencies="$dependencies python-requests"
    fi
    if [ $redhat_version != "6" ] || [ $arch == "x86_64" ]; then
        dependencies="$dependencies pexpect"
    fi

    yum install -y $dependencies

    # perl-Net-Telnet rpm package is not available for ppc64, download it
    if [ $arch == "ppc64" ]; then
        local src_url="http://mirror.centos.org/centos/6/os/i386/Packages/perl-Net-Telnet-3.03-11.el6.noarch.rpm"
        local dest_dir="/tmp/"
        local dest_path="$dest_dir${src_url##*/}"
        get_remote_file $src_url $dest_dir
        yum -y install $dst_path
        rm -f $dst_path
    fi

    # python dependencies installed via PIP
    dependencies=""
    if [ $redhat_version == "6" ]; then
        # requests rpm package is not available on RHEL 6
        dependencies="$dependencies requests"
        if [ $arch == "ppc64" ]; then
            # pexpect rpm package is not available on RHEL 6 ppc64
            dependencies="$dependencies pexpect"
        fi
    fi
    for package in $dependencies;
    do
        pip install $package
    done

    # fence-agents
    pushd "/tmp/"
    clone_repo "git.fedorahosted.org" "git" "fence-agents"
    cd fence-agents
    ./autogen.sh
    ./configure
    make
    make install
    cd ..
    rm -rf fence-agents
    popd

}

# Install Cobbler dependencies
#
# @param arch system architecture
# @param redhat_version Red Hat distribution's major version
function install_cobbler_dependencies ()
{

    local arch="$1"
    local redhat_version="$2"

    # Linux packages dependencies, installed via YUM package manager
    # build dependencies
    local dependencies="gcc git python-devel python-setuptools"
    # runtime dependencies
    dependencies="$dependencies createrepo httpd mkisofs mod_ssl mod_wsgi pykickstart python-cheetah python-netaddr python-simplejson python-urlgrabber rsync tftp-server"
    if [ $redhat_version == "7" ]; then
        dependencies="$dependencies PyYAML"
    fi
    yum -y install $dependencies

    # python dependencies installed via PIP
    dependencies="django==1.6.7"
    if [ $redhat_version == "6" ]; then
        # PyYAML rpm package is not available on RHEL 6
        dependencies="$dependencies PyYAML"
    fi
    for package in $dependencies;
    do
        pip install $package
    done

}

# Configure Cobbler dependencies
function configure_cobbler_dependencies()
{

    configure_http_server "localhost"
    configure_tftp_server

}

# Install Cobbler
function install_cobbler ()
{

    pushd "/tmp/"
    clone_repo "github.com" "cobbler" "cobbler"
    cd cobbler
    make
    make install
    cd ..
    rm cobbler -rf
    popd

}

# Configure TFTP server
function configure_tftp_server ()
{

    # enable TFTP in xinetd
    sed -i 's/.*disable.*$/        disable = no/' /etc/xinetd.d/tftp

}

# Configure HTTP server
function configure_http_server ()
{

    local hostname=$1
    local http_server_conf_file_path="/etc/httpd/conf/httpd.conf"
    sed -i "s/^#*ServerName.*$/ServerName			$hostname:80/" $http_server_conf_file_path

}

# Configure Cobbler server
function configure_cobbler ()
{

    local server_ip=$1
    local subnets=$2
    local python_version=$3

    # update specific server configuration, eg IP address

    # settings
    local settings="/etc/cobbler/settings"
    sed -i "s/^server.*$/server: ${server_ip}/g" $settings
    sed -i "s/^next_server.*$/next_server: ${server_ip}/g" $settings
    sed -i "s/^manage_dhcp.*$/manage_dhcp: 1/" $settings
    sed -i "s/^pxe_just_once.*$/pxe_just_once: 1/" $settings
    sed -i "s/^anamon_enabled.*$/anamon_enabled: 1/" $settings

    # web UI settings
    sed -i "s/SECRET_KEY.*$/SECRET_KEY = 'ItDoesNotMatterWhatIsPutInHere'/" /usr/lib/python$python_version/site-packages/cobbler/web/settings.py

    # modules
    local modules="/etc/cobbler/modules.conf"
    sed -i '/\[dhcp\]/{n;s/.*/module = manage_isc/}' $modules

    # can only run cobbler commands if cobbler daemon is up
    service httpd start
    service cobblerd start

    # download boot loaders
    cobbler get-loaders

    # dhcp
    configure_dhcp_in_cobbler $subnets
    cobbler sync

    service cobblerd stop
    service httpd stop
}

# Configure DHCP in Cobbler server
function configure_dhcp_in_cobbler ()
{

    # configure dhcp template
    local all_subnets="$1"

    OIFS="$IFS"
    IFS=','

    read -a subnets <<< "${all_subnets}"
    local num_subnets=${#subnets[@]}

    # generate dhcp configuration file template
    IFS=';'
    for (( i=0; i<${num_subnets}; i++ ));
    do
        read -a subnet <<< "${subnets[$i]}"
        local netmask="${subnet[1]}"

        cat >> /etc/cobbler/dhcp.template <<EOF
subnet $subnet netmask $netmask {
}

EOF
    done

    # restore IFS
    IFS="$OIFS"

}

# Start Cobbler and related services
function start_services ()
{

    service proftpd start
    chkconfig --level 23 proftpd on

    service dhcpd start
    chkconfig --level 23 dhcpd on

    service xinetd start
    chkconfig --level 23 xinetd on

    service httpd start
    chkconfig --level 23 httpd on

    service cobblerd start
    chkconfig --level 23 cobblerd on

}

# Print help message
function print_help()
{

    echo 'Usage:' $0 ' --ip "Cobbler Server IP" --repositories "repo_section_name1;repo_name1;repo_url1,repo_section_name2;repo_name2;repo_url2" --subnets "subnet1:netmask1,subnet2:netmask2"'

}

# Main code ===================================================================

# validate Linux OS version
linux_version=`uname -r`
if [[ $linux_version =~ 'el6' ]]; then
    redhat_version="6"
    python_version="2.6"
elif [[ $linux_version =~ 'el7' ]]; then
    redhat_version="7"
    python_version="2.7"
else
    echo "Unsupported Linux operating system version"
    exit 1
fi

# validate architecture
arch_name=`arch`
if [ $arch_name != "x86_64" ] && [ $arch_name != "ppc64" ]; then
    echo "Unsupported system architecture $arch_name"
    exit 1
fi

# parse input parameters
while [[ $# > 0 ]]; do
    key="$1"

    case $key in
        -r|--repositories)
            shift
            $repositories="$1"
            ;;
        -i|--ip)
            shift
            $server_ip="$1"
            ;;
        -s|--subnets)
            shift
            $networks="$1"
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            # unknown option
            print_help
            exit 1
            ;;
    esac
    shift
done

autodetect_ip=false
if [ -z $ip ]; then
    autodetect_ip=true
    server_ip=`ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1 -d'/'`
fi
if ! validate_ip_address "${server_ip}"; then
    if [ "${autodetect_ip}" = true ]; then
        echo "Unable to obtain system IP automatically"
    else
        echo "System IP is invalid"
    fi
    exit 1
fi

if [ -z $networks ]; then
    # automatically add system's subnetwork
    network_cidr=`ip addr | grep ${server_ip} |  awk '{print $2}'`
    if [ -z $network_cidr ]; then
        echo "subnetworks were not provided and IP $server_ip is not configured in system, unable to automatically infer subnetwork data"
        exit 1
    fi
    network=`ipcalc -n $network_cidr | cut -f2 -d "="`
    netmask=`ipcalc -m $network_cidr | cut -f2 -d "="`
    networks="$network;$netmask"
fi

# initial setup
echo "Configure /etc/hosts"
hostname=`hostname`
shortname=`echo $hostname | cut -d. -f1`
echo "$server_ip $shortname $hostname" >> /etc/hosts

echo "Disable SELinux"
setenforce 0
sed -i 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config

echo "Disable firewall"
disable_firewall "${redhat_version}"

if [ ! -z "${repositories}" ] ; then
    echo "Add yum repositories"
    add_yum_repositories "${repositories}"
fi

# install dependencies
echo "Install dependencies used by Cobbler installation"
# expect is needed to automate shell input
# scp in openssh-clients is used to copy remote files
dependencies="expect openssh-clients"
if [ $redhat_version == "7" ]; then
    # wget is used to download PIP installer and is not available on RHEL 7
    # minimal installation
    dependencies="$dependencies wget"
fi
yum -y install $dependencies

echo "Install PIP (Python package manager)"
install_pip

echo "Install FTP server: ProFTPD"
mkdir -p /var/ftp/
install_proftpd
configure_proftpd

echo "Install DHCP server: ISC"
install_dhcp_server

echo "Install fence-agents"
install_fence_agents "${arch_name}" "${redhat_version}"

echo "Install Cobbler core dependencies"
install_cobbler_dependencies "${arch_name}" "${redhat_version}"
configure_cobbler_dependencies

# install cobbler
echo "Install Cobbler server"
install_cobbler
configure_cobbler "${server_ip}" "${networks}" "${python_version}"
start_services

exit 0
