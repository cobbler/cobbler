#
# spec file for package cobbler
#
# Copyright (c) 2006 Michael DeHaan <mdehaan@redhat.com>
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.
#
# Supported/tested build targets:
# - Fedora: 30, 31, Rawhide
# - CentOS + EPEL: 7, 8
# - SLE: 15sp1
# - openSUSE: Leap 15.1, Tumbleweed
# - Debian: 10
# - Ubuntu: 18.04
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
#

# Force bash instead of Debian dash
%global _buildshell /bin/bash

# Stop mangling shebangs. It breaks CI.
%undefine __brp_mangle_shebangs

# Work around quirk in OBS about handling defines...
%if 0%{?el7}
%{!?python3_pkgversion: %global python3_pkgversion 36}
%else
%{!?python3_pkgversion: %global python3_pkgversion 3}
%endif

#ToDo: These users/groups differ on every arch. Hopefully not forever...
# Users/Groups
%define apache_user chaos
%define apache_group chaos

# Directories
%define apache_dir /var/www
%define apache_log /var/log/apache2
%define tftpboot_dir /var/lib/tftpboot

# Packages
%define apache_pkg apache2
%define createrepo_pkg createrepo_c
#ToDo: These packages differ on every arch. Hopefully not forever...
%define grub2_x64_efi_pkg chaos
%define grub2_ia32_efi_pkg chaos
%define system_release_pkg chaos

# py3 modules
%define py3_module_cheetah python%{python3_pkgversion}-cheetah
%define py3_module_dns python%{python3_pkgversion}-dns
%define py3_module_pyyaml python%{python3_pkgversion}-yaml
%define py3_module_sphinx python%{python3_pkgversion}-sphinx
%define py3_module_file python%{python3_pkgversion}-magic

# SUSE
%if 0%{?suse_version}
%define apache_user wwwrun
%define apache_group www

%define apache_dir /srv/www
%define apache_webconfigdir /etc/apache2/vhosts.d
%define apache_mod_wsgi apache2-mod_wsgi-python%{python3_pkgversion}
%define tftpboot_dir /srv/tftpboot

%define tftpsrv_pkg tftp
%define grub2_x64_efi_pkg grub2-x86_64-efi
%define grub2_ia32_efi_pkg grub2-i386-efi
%define system_release_pkg distribution-release

#ToDo: Remove this, once it got more stable in Tumbleweed
%undefine python_enable_dependency_generator
%undefine python_disable_dependency_generator

# Python module package names that differ between SUSE and everybody else.
%define py3_module_cheetah python%{python3_pkgversion}-Cheetah3
%define py3_module_dns python%{python3_pkgversion}-dnspython
%define py3_module_pyyaml python%{python3_pkgversion}-PyYAML
%define py3_module_sphinx python%{python3_pkgversion}-Sphinx
# endif SUSE
%endif

# UBUNTU
%if 0%{?debian} || 0%{?ubuntu}
%define apache_user www-data
%define apache_group www-data

%define apache_webconfigdir /etc/apache2/conf-available
%define apache_mod_wsgi libapache2-mod-wsgi-py%{python3_pkgversion}

%define tftpsrv_pkg tftpd-hpa
%define createrepo_pkg createrepo
%define grub2_x64_efi_pkg grub-efi-amd64
%define grub2_ia32_efi_pkg grub-efi-ia32
%define system_release_pkg base-files

# Debian 11 moved to the C implementation of createrepo
%if 0%{?debian} == 11
%define createrepo_pkg createrepo-c
%endif

#endif UBUNTU
%endif

#FEDORA
%if 0%{?fedora} || 0%{?rhel}
%define apache_user apache
%define apache_group apache

%define apache_log /var/log/httpd
%define apache_webconfigdir /etc/httpd/conf.d

%define apache_pkg httpd
%define apache_mod_wsgi python%{python3_pkgversion}-mod_wsgi
%define tftpsrv_pkg tftp-server
%define grub2_x64_efi_pkg grub2-efi-x64
%define grub2_ia32_efi_pkg grub2-efi-ia32
%define system_release_pkg system-release
%if 0%{?fedora}
%define py3_module_file python%{python3_pkgversion}-file-magic
%endif
#endif FEDORA
%endif

# Deal with python3-coverage package quirk
%if 0%{?rhel} == 8
# In RHEL 8, python3-coverage doesn't exist, but it's accessible by common virtual provides
%define py3_module_coverage python3dist(coverage)
%else
%define py3_module_coverage python%{python3_pkgversion}-coverage
%endif

# If they aren't provided by a system installed macro, define them
%{!?__python3: %global __python3 /usr/bin/python3}

# To ensure correct byte compilation
%global __python %{__python3}

%if "%{_vendor}" == "debbuild"
%global devsuffix dev
%else
%global devsuffix devel
%endif

Name:           cobbler
Version:        3.4.0
Release:        1%{?dist}
Summary:        Boot server configurator
URL:            https://cobbler.github.io/

%if "%{_vendor}" == "debbuild"
Packager:       Cobbler Developers <cobbler@lists.fedorahosted.org>
Group:          admin
%endif
%if 0%{?suse_version}
Group:          Productivity/Networking/Boot/Servers
%else
Group:          Development/System
%endif

License:        GPL-2.0-or-later
Source:         %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  git-core
BuildRequires:  %{system_release_pkg}
BuildRequires:  python%{python3_pkgversion}-%{devsuffix}
%if 0%{?suse_version}
BuildRequires:  python-rpm-macros
%endif
%if "%{_vendor}" == "debbuild"
BuildRequires:  python3-deb-macros
BuildRequires:  apache2-deb-macros

%endif
BuildRequires:  %{py3_module_coverage}
BuildRequires:  python%{python3_pkgversion}-distro
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-netaddr
BuildRequires:  python%{python3_pkgversion}-schema
BuildRequires:  %{py3_module_cheetah}
BuildRequires:  %{py3_module_sphinx}
%if 0%{?suse_version}
# Make post-build-checks happy by including these in the buildroot
BuildRequires:  bash-completion
BuildRequires:  %{apache_pkg}
BuildRequires:  %{tftpsrv_pkg}
%endif

%if 0%{?rhel}
# We need these to build this properly, and OBS doesn't pull them in by default for EPEL
BuildRequires:  epel-rpm-macros
%endif
%if 0%{?rhel} && 0%{?rhel} < 9
BuildRequires:  systemd
%endif
%if 0%{?fedora} >= 30 || 0%{?rhel} >= 9 || 0%{?suse_version}
BuildRequires:  systemd-rpm-macros
%endif
%if "%{_vendor}" == "debbuild"
BuildRequires:  systemd-deb-macros
Requires:       systemd-sysv
Requires(post): python3-minimal
Requires(preun): python3-minimal
%endif
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd


Requires:       %{apache_pkg}
Requires:       %{tftpsrv_pkg}
Requires:       %{createrepo_pkg}
Requires:       fence-agents
Requires:       rsync
Requires:       xorriso
%{?python_enable_dependency_generator}
%if ! (%{defined python_enable_dependency_generator} || %{defined python_disable_dependency_generator})
Requires:       %{py3_module_cheetah}
Requires:       %{py3_module_dns}
Requires:       %{apache_mod_wsgi}
Requires:       python%{python3_pkgversion}-netaddr
Requires:       %{py3_module_pyyaml}
Requires:       python%{python3_pkgversion}-requests
Requires:       python%{python3_pkgversion}-distro
Requires:       python%{python3_pkgversion}-schema
Requires:       %{py3_module_file}
%if 0%{?suse_version}
Recommends:     python%{python3_pkgversion}-ldap
%else
Requires:       python%{python3_pkgversion}-ldap
%endif
%endif


%if 0%{?fedora} || 0%{?rhel}
Requires:       dnf-plugins-core
%endif
%if ! (0%{?rhel} && 0%{?rhel} < 8)
# Not everyone wants bash-completion...?
Recommends:     bash-completion
# syslinux is only available on x86
Recommends:     syslinux
# grub2 efi stuff is only available on x86
Recommends:     %{grub2_x64_efi_pkg}
Recommends:     %{grub2_ia32_efi_pkg}
Recommends:     logrotate
Recommends:     python%{python3_pkgversion}-librepo
%endif
# https://github.com/cobbler/cobbler/issues/1685
%if "%{_vendor}" == "debbuild"
Requires:       init-system-helpers
%else
Requires:       /sbin/service
%endif
# No point in having this split out...
Obsoletes:      cobbler-nsupdate < 3.0.99
Provides:       cobbler-nsupdate = %{version}-%{release}

%description
Cobbler is a network install server. Cobbler supports PXE, ISO virtualized installs, and re-installing existing Linux
machines. The last two modes use a helper tool, 'koan', that integrates with cobbler. Cobbler's advanced features
include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and
built-in DHCP/DNS Management. Cobbler has a XML-RPC API for integration with other applications.

%package tests
Summary:        Unit tests for cobbler
Requires:       cobbler = %{version}-%{release}

%description tests
Unit test files from the Cobbler project


%prep
%setup

%if 0%{?suse_version}
# Set tftpboot location correctly for SUSE distributions
sed -e "s|/var/lib/tftpboot|%{tftpboot_dir}|g" -i config/cobbler/settings.yaml
%endif

%build
. distro_build_configs.sh

# Check distro specific variables for consistency
[ "${DOCPATH}" != %{_mandir} ] && echo "ERROR: DOCPATH: ${DOCPATH} does not match %{_mandir}"

# [ "${ETCPATH}" != "/etc/cobbler" ]
# [ "${LIBPATH}" != "/var/lib/cobbler" ]
[ "${LOGPATH}" != %{_localstatedir}/log ] && echo "ERROR: LOGPATH: ${LOGPATH} does not match %{_localstatedir}/log"
[ "${COMPLETION_PATH}" != %{_datadir}/bash-completion/completions ] && \
    echo "ERROR: COMPLETION: ${COMPLETION_PATH} does not match %{_datadir}/bash-completion/completions"

[ "${WEBROOT}" != %{apache_dir} ] && echo "ERROR: WEBROOT: ${WEBROOT} does not match %{apache_dir}"
[ "${WEBCONFIG}" != %{apache_webconfigdir} ] && echo "ERROR: WEBCONFIG: ${WEBCONFIG} does not match %{apache_webconfigdir}"
[ "${TFTPROOT}" != %{tftpboot_dir} ] && echo "ERROR: TFTPROOT: ${TFTPROOT} does not match %{tftpboot_dir}"

%py3_build

%install
. distro_build_configs.sh
%py3_install

# cobbler
rm %{buildroot}%{_sysconfdir}/cobbler/cobbler.conf

mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
mv %{buildroot}%{_sysconfdir}/cobbler/cobblerd_rotate %{buildroot}%{_sysconfdir}/logrotate.d/cobblerd

# systemd
mkdir -p %{buildroot}%{_unitdir}
mv %{buildroot}%{_sysconfdir}/cobbler/cobblerd.service %{buildroot}%{_unitdir}
%if 0%{?suse_version}
mkdir -p %{buildroot}%{_sbindir}
ln -sf service %{buildroot}%{_sbindir}/rccobblerd
%endif


%pre
%if "%{_vendor}" == "debbuild"
if [ "$1" = "upgrade" ]; then
%else
if [ $1 -ge 2 ]; then
%endif
    # package upgrade: backup configuration
    DATE=$(date "+%%Y%%m%%d-%%H%%M%%S")
    if [ ! -d "%{_sharedstatedir}/cobbler/backup/upgrade-${DATE}" ]; then
        mkdir -p "%{_sharedstatedir}/cobbler/backup/upgrade-${DATE}"
    fi
    for i in "config" "snippets" "templates" "triggers" "scripts"; do
        if [ -d "%{_sharedstatedir}/cobbler/${i}" ]; then
            cp -r "%{_sharedstatedir}/cobbler/${i}" "%{_sharedstatedir}/cobbler/backup/upgrade-${DATE}"
        fi
    done
    if [ -d %{_sysconfdir}/cobbler ]; then
        cp -r %{_sysconfdir}/cobbler "%{_sharedstatedir}/cobbler/backup/upgrade-${DATE}"
    fi
fi

%if "%{_vendor}" == "debbuild"
%post
%{py3_bytecompile_post %{name}}
%{systemd_post cobblerd.service}
%{apache2_module_post proxy_http}
# Fixup permission for world readable settings files
chmod 640 %{_sysconfdir}/cobbler/settings.yaml
chmod 600 %{_sysconfdir}/cobbler/mongodb.conf
chmod 640 %{_sysconfdir}/cobbler/users.conf
chmod 640 %{_sysconfdir}/cobbler/users.digest
chgrp %{apache_group} %{_sysconfdir}/cobbler/settings.yaml

%preun
%{py3_bytecompile_preun %{name}}
%{systemd_preun cobblerd.service}

%postun
%{systemd_postun_with_restart cobblerd.service}

%else
%post
%systemd_post cobblerd.service
# Fixup permission for world readable settings files
chmod 640 %{_sysconfdir}/cobbler/settings.yaml
chmod 600 %{_sysconfdir}/cobbler/mongodb.conf
chmod 640 %{_sysconfdir}/cobbler/users.conf
chmod 640 %{_sysconfdir}/cobbler/users.digest
chgrp %{apache_group} %{_sysconfdir}/cobbler/settings.yaml

%preun
%systemd_preun cobblerd.service

%postun
%systemd_postun_with_restart cobblerd.service
%endif

%files
%license COPYING
%doc AUTHORS.in README.md
%doc docs/developer-guide.rst docs/quickstart-guide.rst docs/installation-guide.rst
%dir %{_sysconfdir}/cobbler
%config(noreplace) %{_sysconfdir}/cobbler/auth.conf
%dir %{_sysconfdir}/cobbler/boot_loader_conf
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/bootcfg.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/grub.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/grub_menu.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/grub_submenu.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/ipxe.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/ipxe_menu.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/ipxe_submenu.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/pxe.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/pxe_menu.template
%config(noreplace) %{_sysconfdir}/cobbler/boot_loader_conf/pxe_submenu.template
%config(noreplace) %{_sysconfdir}/cobbler/cheetah_macros
%config(noreplace) %{_sysconfdir}/cobbler/dhcp.template
%config(noreplace) %{_sysconfdir}/cobbler/dhcp6.template
%config(noreplace) %{_sysconfdir}/cobbler/dnsmasq.template
%config(noreplace) %{_sysconfdir}/cobbler/genders.template
%config(noreplace) %{_sysconfdir}/cobbler/import_rsync_whitelist
%dir %{_sysconfdir}/cobbler/iso
%config(noreplace) %{_sysconfdir}/cobbler/iso/buildiso.template
%config(noreplace) %{_sysconfdir}/cobbler/logging_config.conf
%attr(600, root, root) %config(noreplace) %{_sysconfdir}/cobbler/mongodb.conf
%config(noreplace) %{_sysconfdir}/cobbler/named.template
%config(noreplace) %{_sysconfdir}/cobbler/ndjbdns.template
%dir %{_sysconfdir}/cobbler/reporting
%config(noreplace) %{_sysconfdir}/cobbler/reporting/build_report_email.template
%config(noreplace) %{_sysconfdir}/cobbler/rsync.exclude
%config(noreplace) %{_sysconfdir}/cobbler/rsync.template
%config(noreplace) %{_sysconfdir}/cobbler/secondary.template
%if "%{_vendor}" == "debbuild"
# Work around broken attr support
# Cf. https://github.com/debbuild/debbuild/issues/160
%attr(640, root, root) %config(noreplace) %{_sysconfdir}/cobbler/settings.yaml
%attr(640, root, root) %config(noreplace) %{_sysconfdir}/cobbler/users.conf
%attr(640, root, root) %config(noreplace) %{_sysconfdir}/cobbler/users.digest
%else
%attr(640, root, %{apache_group}) %config(noreplace) %{_sysconfdir}/cobbler/settings.yaml
%attr(640, root, root) %config(noreplace) %{_sysconfdir}/cobbler/users.conf
%attr(640, root, root) %config(noreplace) %{_sysconfdir}/cobbler/users.digest
%endif
%config(noreplace) %{_sysconfdir}/cobbler/version
%config(noreplace) %{_sysconfdir}/cobbler/zone.template
%dir %{_sysconfdir}/cobbler/zone_templates
%config(noreplace) %{_sysconfdir}/cobbler/zone_templates/foo.example.com
%config(noreplace) %{_sysconfdir}/logrotate.d/cobblerd
%config(noreplace) %{apache_webconfigdir}/cobbler.conf
%dir %{_sysconfdir}/cobbler/windows
%config(noreplace) %{_sysconfdir}/cobbler/windows/answerfile.template
%config(noreplace) %{_sysconfdir}/cobbler/windows/post_inst_cmd.template
%config(noreplace) %{_sysconfdir}/cobbler/windows/startnet.template
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd
%{_bindir}/cobbler-settings
%dir %{_datadir}/cobbler
%{_datadir}/cobbler/bin
%{_mandir}/man1/cobbler.1*
%{_mandir}/man5/cobbler.conf.5*
%{_mandir}/man8/cobblerd.8*
%{_datadir}/bash-completion/completions/cobbler
%{python3_sitelib}/cobbler/
%{python3_sitelib}/cobbler-*
%{_unitdir}/cobblerd.service
%if 0%{?suse_version}
%{_sbindir}/rccobblerd
%endif
%{tftpboot_dir}/*
%{apache_dir}/cobbler
%{_sharedstatedir}/cobbler
%{_localstatedir}/log/cobbler

%files tests
%dir %{_datadir}/cobbler/tests
%{_datadir}/cobbler/tests/*

%changelog
* Thu Dec 19 2019 Neal Gompa <ngompa13@gmail.com>
- Initial rewrite of packaging
