#!/bin/bash

# Dependencies for reposync tests
zypper install --no-recommends -y dnf python3-librepo dnf dnf-plugins-core wget \
       perl-LockFile-Simple perl-Net-INET6Glue perl-LWP-Protocol-https ed
dnf install -y  http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/d/debmirror-2.35-2.fc35.noarch.rpm
