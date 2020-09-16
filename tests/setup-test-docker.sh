#!/bin/bash

# SystemD stuff (needs insserv additionally)
zypper -n install systemd insserv; zypper clean
cd /usr/lib/systemd/system/sysinit.target.wants/
for i in *; do
    [[ ${i} == systemd-tmpfiles-setup.service ]] || rm -f ${i};
done
rm -f /usr/lib/systemd/system/multi-user.target.wants/*
rm -f /etc/systemd/system/*.wants/*
rm -f /usr/lib/systemd/system/local-fs.target.wants/*
rm -f /usr/lib/systemd/system/sockets.target.wants/*udev*
rm -f /usr/lib/systemd/system/sockets.target.wants/*initctl*
rm -f /usr/lib/systemd/system/basic.target.wants/*
rm -f /usr/lib/systemd/system/anaconda.target.wants/*

cd /test_dir

# Packages for running cobbler
zypper -n update
zypper -n in python3 python3-devel python3-pip python3-setuptools python3-wheel python3-distro python3-future python3-coverage apache2 apache2-devel acl apache2-mod_wsgi-python3 ipmitool rsync fence-agents genders xorriso python3-ldap tftp python3-Sphinx hardlink
pip3 install pykickstart
# Packages for building & installing cobbler from source
zypper -n in make gzip sed git hg

# Set tftpboot location correctly for SUSE distributions
sed -e "s|/var/lib/tftpboot|/srv/tftpboot|g" -i cobbler/settings.py config/cobbler/settings

# Install and setup testing framework
pip3 install pytest-django
pip3 install pytest-pythonpath

# set SECRET_KEY for django tests
sed -i s/SECRET_KEY.*/'SECRET_KEY\ =\ "qwertyuiopasdfghl;"'/ cobbler/web/settings.py

# Install and upgrade all dependecys
pip3 install --upgrade pip
pip3 install .[lint,test]

# Install cobbler
make install
cp /etc/cobbler/cobblerd.service /usr/lib/systemd/system/cobblerd.service
cp /etc/cobbler/cobbler.conf /etc/apache2/conf.d/

# Enable the services
systemctl enable cobblerd apache2 tftp
a2enmod version
a2enmod proxy
a2enmod proxy_http
