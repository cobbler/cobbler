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
zypper -n in python3 python3-devel python3-pip apache2 apache2-devel acl apache2-mod_wsgi-python3 ipmitool rsync fence-agents genders mkisofs python3-ldap tftp
# Packages for building & installing cobbler from source
zypper -n in make gzip

# Install and upgrade all dependecys
pip3 install --upgrade pip
pip3 install -r requirements-test.txt

# Install cobbler
make install
cp /etc/cobbler/cobblerd.service /usr/lib/systemd/system/cobblerd.service
cp /etc/cobbler/cobbler.conf /etc/apache2/conf.d/

# Enable the services
systemctl enable cobblerd apache2 tftp
a2enmod version
a2enmod proxy
a2enmod proxy_http
