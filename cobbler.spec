#
# RPM spec file for all Cobbler packages
#
# Supported/tested build targets:
# - Fedora: 18, 19, 20
# - RHEL: 7
# - CentOS: 7
# - Scientific Linux: 7
# - OpenSuSE: 12.3, 13.1, 13.2, Factory, Tumbleweed
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
# https://build.opensuse.org/project/subprojects/home:libertas-ict
#

%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?pyver: %global pyver %(%{__python2} -c "import sys ; print sys.version[:3]" || echo 0)}

%global debug_package %{nil}
%define _binaries_in_noarch_packages_terminate_build 0
%define _unpackaged_files_terminate_build 1

%if 0%{?suse_version}
%define apache_dir /srv/www/
%define apache_etc /etc/apache2/
%define apache_user wwwrun
%define apache_group www
%define apache_log /var/log/apache2/
%define tftp_dir /srv/tftpboot/
%endif

%if 0%{?fedora} || 0%{?rhel}
%define apache_dir /var/www/
%define apache_etc /etc/httpd/
%define apache_user apache
%define apache_group apache
%define apache_log /var/log/httpd/
%define tftp_dir /var/lib/tftpboot/
%endif


#
# Package: cobbler
#

Summary: Boot server configurator
Name: cobbler
License: GPLv2+
AutoReq: no
Version: 2.9.0
Release: 1%{?dist}
Source0: https://github.com/cobbler/cobbler/releases/cobbler-%{version}.tar.gz
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: https://cobbler.github.io

BuildRequires: git
BuildRequires: openssl
BuildRequires: python-devel
Requires: python >= 2.7
Requires: python(abi) >= %{pyver}
Requires: createrepo
Requires: python-netaddr
Requires: python-simplejson
Requires: python-urlgrabber
Requires: rsync
Requires: syslinux
Requires: logrotate

%if 0%{?fedora} < 23 || 0%{?rhel} >= 7
Requires: yum-utils
%endif

%if 0%{?fedora} >= 23
Requires: dnf-core-plugins
%endif

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
BuildRequires: redhat-rpm-config
BuildRequires: systemd-units
Requires: genisoimage
Requires: python-cheetah
Requires: PyYAML
Requires: httpd
Requires: mod_wsgi
Requires(post): systemd-sysv
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%endif

%if 0%{?suse_version} >= 1230
BuildRequires: apache2
BuildRequires: python-Cheetah
BuildRequires: distribution-release
BuildRequires: systemd
Requires: python-PyYAML
Requires: python-Cheetah
Requires: apache2
Requires: apache2-mod_wsgi
Requires: cdrkit-cdrtools-compat
%{?systemd_requires}
Requires(pre): systemd
Requires(post): systemd
Requires(preun): systemd
Requires(preun): systemd
%endif


%description
Cobbler is a PXE and ISO based network install server.
Cobbler's advanced features include importing distributions from DVDs
and rsync mirrors, automatic installation file templating, integrated
package mirroring, and built-in DHCP/DNS Management.

Cobbler has a XMLRPC API for integration with other applications.


%prep
%setup -q


%build
%{__python2} setup.py build


%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python2} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX

# cobbler
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobbler.conf
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d
mv $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd_rotate $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/cobblerd

mkdir -p $RPM_BUILD_ROOT%{tftp_dir}/images

rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd
rm $RPM_BUILD_ROOT%{_sysconfdir}/init.d/cobblerd
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mv $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd.service $RPM_BUILD_ROOT%{_unitdir}

# cobbler-web
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobbler_web.conf



%pre
if (( $1 >= 2 )); then
    # package upgrade: backup configuration
    DATE=$(date "+%Y%m%d-%H%M%S")
    if [[ ! -d /var/lib/cobbler/backup/upgrade-${DATE} ]]; then
        mkdir -p /var/lib/cobbler/backup/upgrade-${DATE}
    fi
    for i in "config" "snippets" "templates" "triggers" "scripts"; do
        if [[ -d /var/lib/cobbler/${i} ]]; then
            cp -r /var/lib/cobbler/${i} /var/lib/cobbler/backup/upgrade-${DATE}
        fi
    done
    if [[ -d /etc/cobbler ]]; then
        cp -r /etc/cobbler /var/lib/cobbler/backup/upgrade-${DATE}
    fi
fi


%if 0%{?suse_version} >= 1230
%post
# package install
if (( $1 == 1 )); then
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy > /dev/null 2>&1
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy_http > /dev/null 2>&1
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy_connect > /dev/null 2>&1
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES rewrite > /dev/null 2>&1
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES ssl > /dev/null 2>&1
    sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES wsgi > /dev/null 2>&1
    %service_add_post cobblerd.service
fi
%preun
# last package removal
if (( $1 == 0 )); then
    %service_del_preun cobblerd.service
fi
%postun
# last package removal
if (( $1 == 0 )); then
    %service_del_postun cobblerd.service
fi
%endif


%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
%post
# package install
if (( $1 == 1 )); then
    /usr/bin/systemctl enable cobblerd.service > /dev/null 2>&1
    /usr/bin/systemctl start cobblerd.service > /dev/null 2>&1
    /usr/bin/systemctl restart httpd.service > /dev/null 2>&1
fi
%preun
# last package removal
if (( $1 == 0 )); then
    /usr/bin/systemctl disable cobblerd.service > /dev/null 2>&1
    /usr/bin/systemctl stop cobblerd.service > /dev/null 2>&1
fi
%postun
# last package removal
if (( $1 == 0 )); then
    /usr/bin/systemctl try-restart httpd.service > /dev/null 2>&1
fi
%endif


%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT


%files
# binaries
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd
%{_sbindir}/tftpd.py

# python
%{python2_sitelib}/cobbler/*.py*
%{python2_sitelib}/cobbler/modules/*.py*
%{python2_sitelib}/cobbler*.egg-info
%exclude %{python2_sitelib}/cobbler/modules/nsupdate*
%exclude %{python2_sitelib}/cobbler/web


# configuration
%config(noreplace) %{_sysconfdir}/cobbler
%exclude %{_sysconfdir}/cobbler/settings.d/nsupdate.settings

%config(noreplace) %{_sysconfdir}/logrotate.d/cobblerd
%dir %{apache_etc}
%dir %{apache_etc}/conf.d
%config(noreplace) %{apache_etc}/conf.d/cobbler.conf
%{_unitdir}/cobblerd.service

# data
%{tftp_dir}
%{apache_dir}/cobbler
%config(noreplace) %{_var}/lib/cobbler
%exclude %{apache_dir}/cobbler_webui_content
%exclude %{_var}/lib/cobbler/webui_sessions

# share
%{_usr}/share/cobbler
%exclude %{_usr}/share/cobbler/spool
%exclude %{_usr}/share/cobbler/web

# log
%{_var}/log/cobbler

# documentation
%doc AUTHORS COPYING README docs/README.suse
%{_mandir}/man1/cobbler.1.gz


#
# package: cobbler-web
#

%package -n cobbler-web

Summary: Web interface for Cobbler
Group: Applications/System
Requires: python(abi) >= %{pyver}
Requires: cobbler
Requires(post): openssl

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
Requires: httpd
Requires: Django >= 1.4
Requires: mod_wsgi
%endif

%if 0%{?suse_version} >= 1230
Requires: apache2
Requires: apache2-mod_wsgi
Requires: python-django >= 1.4
%endif


%description -n cobbler-web
Web interface for Cobbler that allows visiting
http://server/cobbler_web to configure the install server.


%post -n cobbler-web
# Change the SECRET_KEY option in the Django settings.py file
# required for security reasons, should be unique on all systems
RAND_SECRET=$(openssl rand -base64 40 | sed 's/\//\\\//g')
sed -i -e "s/SECRET_KEY = ''/SECRET_KEY = \'$RAND_SECRET\'/" /usr/share/cobbler/web/settings.py


%files -n cobbler-web
%doc AUTHORS COPYING README

%{python2_sitelib}/cobbler/web/
%dir %{apache_etc}
%dir %{apache_etc}/conf.d
%config(noreplace) %{apache_etc}/conf.d/cobbler_web.conf
%{apache_dir}/cobbler_webui_content/

%if 0%{?fedora} >=18 || 0%{?rhel} >= 7
%defattr(-,apache,apache,-)
/usr/share/cobbler/web
%dir %attr(700,apache,root) /var/lib/cobbler/webui_sessions
%endif

%if 0%{?suse_version} >= 1230
%defattr(-,%{apache_user},%{apache_group},-)
/usr/share/cobbler/web
%dir %attr(700,%{apache_user},%{apache_group}) /var/lib/cobbler/webui_sessions
%endif

# 
# package: cobbler-nsupdate
#

%package -n cobbler-nsupdate

Summary: module for dynamic dns updates
Group: Applications/System
Requires: cobbler
Requires: python-dns

%description -n cobbler-nsupdate
Cobbler module providing secure dynamic dns updates

%files -n cobbler-nsupdate
%config(noreplace) %{_sysconfdir}/cobbler/settings.d/nsupdate.settings
%{python2_sitelib}/cobbler/modules/nsupdate*

%doc AUTHORS COPYING README


%changelog
* Fri Jul 18 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.6.3 release
- Cobbler 2.4.6 release
* Tue Jul 15 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.6.2 release
* Sun Jul 13 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.4.5 release
* Thu May 22 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.6.1 release
* Tue Apr 22 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.4.4 release
* Sun Apr 13 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.6.0 release
* Wed Mar 19 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.4.3 release
* Sat Feb 15 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.4.2 release
* Mon Feb 03 2014 Jörgen Maas <jorgen.maas@gmail.com>
- Cobbler 2.4.1 release
* Thu Jun 20 2013 James Cammarata <jimi@sngx.net>
- Cobbler 2.4.0-1 release
* Sun Jun 17 2012 James Cammarata <jimi@sngx.net>
- Cobbler 2.2.3-2 release
* Tue Jun 05 2012 James Cammarata <jimi@sngx.net>
- Cobbler 2.2.3-1 release
* Tue Nov 15 2011 Scott Henson <shenson@redhat.com>
- Cobbler 2.2.2-1 release
* Wed Oct 05 2011 Scott Henson <shenson@redhat.com>
- Cobbler 2.2.1-1 release
* Wed Oct 05 2011 Scott Henson <shenson@redhat.com>
- Cobbler 2.2.0-1 release
* Tue Apr 27 2010 Scott Henson <shenson@redhat.com>
- Cobbler 2.0.4-1 release
* Thu Apr 15 2010 Devan Goodwin <dgoodwin@rm-rf.ca>
- Cobbler 2.0.3.2-1 release
* Mon Mar  1 2010 Scott Henson <shenson@redhat.com>
- Cobbler 2.0.3.1-3 release
* Mon Mar  1 2010 Scott Henson <shenson@redhat.com>
- Cobbler 2.0.3.1-2 release
* Mon Feb 15 2010 Scott Henson <shenson@redhat.com>
- Cobbler 2.0.3.1-1 release
* Thu Feb 11 2010 Scott Henson <shenson@redhat.com>
- Cobbler 2.0.3-1 release
* Mon Nov 23 2009 John Eckersberg <jeckersb@redhat.com>
- Cobbler 2.0.2-1 release
* Tue Sep 15 2009 Michael DeHaan <michael.dehaan AT gmail>
- Cobbler 2.0.0-1 release

# EOF
