#
# RPM spec file for all Cobbler packages
#
# Supported/tested build targets:
# - Fedora: 30, 31, Rawhide
# - CentOS + EPEL: 7, 8
# - SLE: 15sp1
# - OpenSuSE: Leap 15.1, Tumbleweed
# - Debian: 10
# - Ubuntu: 18.04
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
#

# Work around quirk in OBS about handling defines...
%if 0%{?el7}
%{!?python3_pkgversion: %global python3_pkgversion 36}
%else
%{!?python3_pkgversion: %global python3_pkgversion 3}
%endif

%if 0%{?suse_version}
%define apache_pkg apache2
%define apache_dir /srv/www
%define apache_etc /etc/apache2
%define apache_user wwwrun
%define apache_group www
%define apache_log /var/log/apache2
%define apache_webconfigdir /etc/apache2/vhosts.d
%define apache_mod_wsgi apache2-mod_wsgi-python%{python3_pkgversion}
%define tftpboot_dir /srv/tftpboot
%define tftpsrv_pkg tftp
%define createrepo_pkg createrepo_c
%define grub2_x64_efi_pkg grub2-x86_64-efi
%define grub2_ia32_efi_pkg grub2-i386-efi
%define system_release_pkg distribution-release
%endif

%if 0%{?debian} || 0%{?ubuntu}
%define apache_pkg apache2
%define apache_dir /var/www
%define apache_etc /etc/apache2
%define apache_user www-data
%define apache_group www-data
%define apache_log /var/log/apache2
%define apache_webconfigdir /etc/apache2/conf-available
%define apache_mod_wsgi libapache2-mod-wsgi-py%{python3_pkgversion}
%define tftpboot_dir /var/lib/tftpboot
%define tftpsrv_pkg tftpd-hpa
%define createrepo_pkg createrepo
%define grub2_x64_efi_pkg grub-efi-amd64
%define grub2_ia32_efi_pkg grub-efi-ia32
%define system_release_pkg base-files
%endif

%if 0%{?fedora} || 0%{?rhel}
%define apache_pkg httpd
%define apache_dir /var/www
%define apache_etc /etc/httpd
%define apache_user apache
%define apache_group apache
%define apache_log /var/log/httpd
%define apache_webconfigdir /etc/httpd/conf.d
%define apache_mod_wsgi python%{python3_pkgversion}-mod_wsgi
%define tftpboot_dir /var/lib/tftpboot
%define tftpsrv_pkg tftp-server
%define createrepo_pkg createrepo_c
%define grub2_x64_efi_pkg grub2-efi-x64
%define grub2_ia32_efi_pkg grub2-efi-ia32
%define system_release_pkg system-release
%endif

# Python module package names that differ between SUSE and everybody else... :(
%if 0%{?suse_version}
%define py3_module_cheetah python%{python3_pkgversion}-Cheetah3
%define py3_module_django python%{python3_pkgversion}-Django
%define py3_module_dns python%{python3_pkgversion}-dnspython
%define py3_module_pyyaml python%{python3_pkgversion}-PyYAML
%define py3_module_sphinx python%{python3_pkgversion}-Sphinx
%else
%define py3_module_cheetah python%{python3_pkgversion}-cheetah
%define py3_module_django python%{python3_pkgversion}-django
%define py3_module_dns python%{python3_pkgversion}-dns
%define py3_module_pyyaml python%{python3_pkgversion}-yaml
%define py3_module_sphinx python%{python3_pkgversion}-sphinx
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

%if %{_vendor} == "debbuild"
%global devsuffix dev
%else
%global devsuffix devel
%endif

%global __requires_exclude_from ^%{python3_sitelib}/modules/serializer_mongodb.py*$

Name:           cobbler
Version:        3.1.2
Release:        1%{?dist}
Summary:        Boot server configurator
URL:            https://cobbler.github.io/

%if %{_vendor} == "debbuild"
Packager:       Cobbler Developers <cobbler@lists.fedorahosted.org>
Group:          admin
%else
Group:          Development/System
%endif

License:        GPL-2.0-or-later
Source0:        https://github.com/cobbler/cobbler/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  git-core
BuildRequires:  %{system_release_pkg}
BuildRequires:  python%{python3_pkgversion}-%{devsuffix}
%if 0%{?suse_version}
BuildRequires:  python-rpm-macros
%endif
%if %{_vendor} == "debbuild"
BuildRequires:  python3-deb-macros
%endif
BuildRequires:  %{py3_module_coverage}
BuildRequires:  python%{python3_pkgversion}-distro
BuildRequires:  python%{python3_pkgversion}-future
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-netaddr
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
%if %{_vendor} == "debbuild"
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
Requires:       rsync
Requires:       xorriso
%{?python_enable_dependency_generator}
%if ! (%{defined python_enable_dependency_generator} || %{defined python_disable_dependency_generator})
Requires:       %{py3_module_cheetah}
Requires:       %{py3_module_dns}
Requires:       python%{python3_pkgversion}-future
Requires:       python%{python3_pkgversion}-ldap3
Requires:       %{apache_mod_wsgi}
Requires:       python%{python3_pkgversion}-netaddr
Requires:       %{py3_module_pyyaml}
Requires:       python%{python3_pkgversion}-requests
Requires:       python%{python3_pkgversion}-simplejson
Requires:       python%{python3_pkgversion}-tornado
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
%endif
# https://github.com/cobbler/cobbler/issues/1685
%if %{_vendor} == "debbuild"
Requires:       init-system-helpers
%else
Requires:       /sbin/service
%endif
# No point in having this split out...
Obsoletes:      cobbler-nsupdate < 3.0.99
Provides:       cobbler-nsupdate = %{version}-%{release}

%description
Cobbler is a network install server.  Cobbler supports PXE, ISO
virtualized installs, and re-installing existing Linux machines.
The last two modes use a helper tool, 'koan', that integrates with
cobbler.  There is also a web interface 'cobbler-web'.  Cobbler's
advanced features include importing distributions from DVDs and rsync
mirrors, kickstart templating, integrated yum mirroring, and built-in
DHCP/DNS Management.  Cobbler has a XMLRPC API for integration with
other applications.


%package web
Summary:        Web interface for Cobbler
Requires:       cobbler = %{version}-%{release}
%if ! (%{defined python_enable_dependency_generator} || %{defined python_disable_dependency_generator})
Requires:       %{py3_module_django}
Requires:       %{apache_mod_wsgi}
%endif
%if 0%{?fedora} || 0%{?rhel}
Requires:       mod_ssl
%endif
Requires(post): openssl

%description web
Web interface for Cobbler that allows visiting
http://server/cobbler_web to configure the install server.


%prep
%setup

%if 0%{?suse_version}
# Set tftpboot location correctly for SUSE distributions
sed -e "s|/var/lib/tftpboot|%{tftpboot_dir}|g" -i cobbler/settings.py config/cobbler/settings
%endif

%build
%py3_build

%install
# bypass install errors ( don't chown in install step)
%py3_install ||:

# cobbler
rm %{buildroot}%{_sysconfdir}/cobbler/cobbler.conf

mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
mv %{buildroot}%{_sysconfdir}/cobbler/cobblerd_rotate %{buildroot}%{_sysconfdir}/logrotate.d/cobblerd

# Create data directories in tftpboot_dir
mkdir -p %{buildroot}%{tftpboot_dir}/boot
mkdir %{buildroot}%{tftpboot_dir}/etc
mkdir %{buildroot}%{tftpboot_dir}/grub
mkdir %{buildroot}%{tftpboot_dir}/images
mkdir %{buildroot}%{tftpboot_dir}/images2
mkdir %{buildroot}%{tftpboot_dir}/ppc
mkdir %{buildroot}%{tftpboot_dir}/pxelinux.cfg
mkdir %{buildroot}%{tftpboot_dir}/s390x

# systemd
mkdir -p %{buildroot}%{_unitdir}
mv %{buildroot}%{_sysconfdir}/cobbler/cobblerd.service %{buildroot}%{_unitdir}
%if 0%{?suse_version}
ln -sf service %{buildroot}%{_sbindir}/rccobblerd
%endif

# cobbler-web
rm %{buildroot}%{_sysconfdir}/cobbler/cobbler_web.conf


%pre
%if %{_vendor} == "debbuild"
if [ "$1" = "upgrade" ]; then
%else
if [ $1 -ge 2 ]; then
%endif
    # package upgrade: backup configuration
    DATE=$(date "+%Y%m%d-%H%M%S")
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

%if %{_vendor} == "debbuild"
%post
%{py3_bytecompile_post %{name}}
%{systemd_post cobblerd.service}

%preun
%{py3_bytecompile_preun %{name}}
%{systemd_preun cobblerd.service}

%postun
%{systemd_postun_with_restart cobblerd.service}

%else
%post
%systemd_post cobblerd.service

%preun
%systemd_preun cobblerd.service

%postun
%systemd_postun_with_restart cobblerd.service
%endif

%post web
# Change the SECRET_KEY option in the Django settings.py file
# required for security reasons, should be unique on all systems
# Choose from letters and numbers only, so no special chars like ampersand (&).
RAND_SECRET=$(head /dev/urandom | tr -dc 'A-Za-z0-9!' | head -c 50 ; echo '')
sed -i -e "s/SECRET_KEY = ''/SECRET_KEY = \'$RAND_SECRET\'/" %{_datadir}/cobbler/web/settings.py


%files
%license COPYING
%doc AUTHORS.in README.md
%doc docs/developer-guide.rst docs/quickstart-guide.rst docs/installation-guide.rst
%if %{_vendor} == "debbuild"
%config(noreplace) %{_sysconfdir}/cobbler/*
%else
%config(noreplace) %{_sysconfdir}/cobbler
%endif
%config(noreplace) %{_sysconfdir}/logrotate.d/cobblerd
%config(noreplace) %{apache_webconfigdir}/cobbler.conf
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd
%{_sbindir}/tftpd.py
%{_sbindir}/fence_ipmitool
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
%exclude %{_sharedstatedir}/cobbler/webui_sessions
%{_localstatedir}/log/cobbler

%files web
%license COPYING
%doc AUTHORS.in README.md
%config(noreplace) %{apache_webconfigdir}/cobbler_web.conf
%attr(-,%{apache_user},%{apache_group}) %{_datadir}/cobbler/web
%dir %attr(700,%{apache_user},root) %{_sharedstatedir}/cobbler/webui_sessions
%attr(-,%{apache_user},%{apache_group}) %{apache_dir}/cobbler_webui_content/


%changelog
* Thu Dec 19 2019 Neal Gompa <ngompa13@gmail.com>
- Initial rewrite of packaging
