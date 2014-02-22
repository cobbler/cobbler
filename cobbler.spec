#
# RPM spec file for all Cobbler packages
#
# Supported/tested build targets:
# - Fedora: 18, 19, 20
# - RHEL: 6
# - CentOS: 6
# - OpenSuSE: 12.3, 13.1, Factory
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
# https://build.opensuse.org/project/subprojects/home:libertas-ict
#

%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]" || echo 0)}

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
Version: 2.5.0
Release: 1%{?dist}
Source0: http://shenson.fedorapeople.org/cobbler/cobbler-%{version}.tar.gz
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://www.cobblerd.org/

BuildRequires: git
BuildRequires: openssl
Requires: python >= 2.6
Requires: python(abi) >= %{pyver}
Requires: createrepo
Requires: python-netaddr
Requires: python-simplejson
Requires: python-urlgrabber
Requires: rsync
Requires: syslinux
Requires: yum-utils
Requires: logrotate

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 6
BuildRequires: redhat-rpm-config
BuildRequires: python-cheetah
Requires: genisoimage
Requires: python-cheetah
Requires: PyYAML
Requires: httpd
Requires: mod_wsgi
%endif

%if 0%{?suse_version} >= 1230
BuildRequires: apache2
BuildRequires: python-Cheetah
BuildRequires: suse-release
BuildRequires: systemd
%{?systemd_requires}
Requires: python-PyYAML
Requires: python-Cheetah
Requires: apache2
Requires: apache2-mod_wsgi
Requires: cdrkit-cdrtools-compat
%endif

%if 0%{?fedora} >= 18
BuildRequires: systemd-units
Requires(post): systemd-sysv
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%endif

%if 0%{?rhel} >= 6
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
%endif


%description
Cobbler is a network install server.  Cobbler supports PXE, ISO
virtualized installs, and re-installing existing Linux machines. 
The last two modes use a helper tool, 'koan', that integrates with
cobbler.  There is also a web interface 'cobbler-web'.  Cobbler's
advanced features include importing distributions from DVDs and rsync
mirrors, kickstart templating, integrated yum mirroring, and built-in
DHCP/DNS Management.  Cobbler has a XMLRPC API for integration with
other applications.


%prep
%setup -q


%build
%{__python} setup.py build


%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX

# cobbler
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobbler.conf

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d
mv $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd_rotate $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/cobblerd

mkdir -p $RPM_BUILD_ROOT%{tftp_dir}/images
mkdir -p $RPM_BUILD_ROOT%{apache_log}/cobbler

%if 0%{?rhel} == 6
# sysvinit
mkdir -p %{_sysconfdir}/init.d
mv $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd $RPM_BUILD_ROOT%{_sysconfdir}/init.d/cobblerd
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd.service
%else
# systemd
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd
rm $RPM_BUILD_ROOT%{_sysconfdir}/init.d/cobblerd
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mv $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobblerd.service $RPM_BUILD_ROOT%{_unitdir}
%endif

# cobbler-web
rm $RPM_BUILD_ROOT%{_sysconfdir}/cobbler/cobbler_web.conf

# koan
mkdir -p $RPM_BUILD_ROOT/var/spool/koan


%pre
# not used


%post
# package install
if (( $1 == 1 )); then
    %if 0%{?rhel} == 6
        /sbin/chkconfig --add cobblerd > /dev/null 2>&
        /etc/init.d/cobblerd start > /dev/null 2>&1
        /etc/init.d/httpd restart > /dev/null 2>&1
    %endif
    %if 0%{?suse_version} >= 1230
        %{fillup_and_insserv cobblerd}
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy_http
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES proxy_connect
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES rewrite
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES ssl
        sysconf_addword /etc/sysconfig/apache2 APACHE_MODULES wsgi
        /usr/bin/systemctl enable cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl start cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl restart apache2.service > /dev/null 2>&1
    %endif
    %if 0%{?fedora} >= 18
        /usr/bin/systemctl enable cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl start cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl restart httpd.service > /dev/null 2>&1
    %endif
# package upgrade
elif (( $1 >= 2 )); then
    # backup configuration
    DATE=$(date "+%Y%m%d-%H%M%S")
    if [[ ! -d /var/lib/cobbler/backup/upgrade-${DATE} ]]; then
        mkdir -p /var/lib/cobbler/backup/upgrade-${DATE}
    fi
    for i in "config" "snippets" "kickstarts" "triggers" "scripts"; do
        if [[ -d /var/lib/cobbler/${i} ]]; then
            cp -r /var/lib/cobbler/${i} /var/lib/cobbler/backup/upgrade-${DATE}
        fi
    done
    # restart services
    %if 0%{?rhel} == 6
        /etc/init.d/cobblerd condrestart > /dev/null 2>&1
        /etc/init.d/httpd condrestart > /dev/null 2>&1
    %endif
    %if 0%{?fedora} >= 18
        /usr/bin/systemctl try-restart cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl try-restart httpd.service > /dev/null 2>&1
    %endif 
    %if 0%{?suse_version} >= 1230
        /usr/bin/systemctl try-restart cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl try-restart apache2.service > /dev/null 2>&1
    %endif
fi


%preun
# last instance of cobbler package is being removed
if (( $1 == 0 )); then
    # disable/stop cobblerd
    %if 0%{?rhel} == 6
        /sbin/chkconfig --del cobblerd > /dev/null 2>&
        /etc/init.d/cobblerd stop > /dev/null 2>&1
    %endif
    %if 0%{?suse_version} >= 1230
        /usr/bin/systemctl disable cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl stop cobblerd.service > /dev/null 2>&1
    %endif
    %if 0%{?fedora} >= 18
        /usr/bin/systemctl disable cobblerd.service > /dev/null 2>&1
        /usr/bin/systemctl stop cobblerd.service > /dev/null 2>&1
    %endif
fi


%postun
# last package removal
if (( $1 == 0 )); then
    # restart apache processes after cobbler removal
    %if 0%{?rhel} == 6
        /etc/init.d/httpd condrestart > /dev/null 2>&1
    %endif
    %if 0%{?fedora} >= 18
        /usr/bin/systemctl try-restart httpd.service > /dev/null 2>&1
    %endif
    %if 0%{?suse_version} >= 1230
        /usr/bin/systemctl try-restart apache2.service > /dev/null 2>&1
    %endif
fi


%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT


%files
# binaries
%defattr(-,root,root,-)
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd
%{_sbindir}/tftpd.py
%exclude %{_bindir}/cobbler-register
%exclude %{_bindir}/koan
%exclude %{_bindir}/ovz-install

# python
%{python_sitelib}/cobbler
%{python_sitelib}/cobbler*.egg-info
%exclude %{python_sitelib}/koan

# configuration
%config(noreplace) %{_sysconfdir}/cobbler
%config(noreplace) %{_sysconfdir}/logrotate.d/cobblerd
%dir %{apache_etc}
%dir %{apache_etc}/conf.d
%config(noreplace) %{apache_etc}/conf.d/cobbler.conf
%exclude %{apache_etc}/conf.d/cobbler_web.conf
%if 0%{?rhel} == 6
/etc/init.d/cobblerd
%else
%{_unitdir}/cobblerd.service
%endif

# data
%{tftp_dir}
%{tftp_dir}/images
%{apache_dir}/cobbler
%config(noreplace) %{_var}/lib/cobbler
%exclude %{apache_dir}/cobbler_webui_content
%exclude %{_var}/lib/cobbler/webui_sessions
%exclude %{_var}/lib/koan

# share
%{_usr}/share/cobbler
%{_usr}/share/cobbler/installer_templates
%exclude %{_usr}/share/cobbler/spool
%exclude %{_usr}/share/cobbler/web

# log
%{_var}/log/cobbler
%{apache_log}
%{apache_log}/cobbler
%exclude %{_var}/log/koan
%exclude %{_var}/spool/koan

# documentation
%doc AUTHORS README COPYING
%{_mandir}/man1/cobbler.1.gz
%exclude %{_mandir}/man1/cobbler-register.1.gz
%exclude %{_mandir}/man1/koan.1.gz


# 
# package: koan
#

%package -n koan

Summary: Helper tool that performs cobbler orders on remote machines
Group: Applications/System
Requires: python >= 2.0
%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
Requires: python(abi) >= %{pyver}
Requires: python-simplejson
Requires: virt-install
%endif


%description -n koan
Koan stands for kickstart-over-a-network and allows for both
network installation of new virtualized guests and reinstallation
of an existing system.  For use with a boot-server configured with Cobbler


%files -n koan
%defattr(-,root,root,-)
/var/spool/koan
/var/lib/koan
%{_bindir}/koan
%{_bindir}/ovz-install
%{_bindir}/cobbler-register
%{python_sitelib}/koan

%if 0%{?fedora} >= 9 || 0%{?rhel} >= 5
%exclude %{python_sitelib}/koan/sub_process.py
%exclude %{python_sitelib}/koan/opt_parse.py
%exclude %{python_sitelib}/koan/text_wrap.py
%endif

%{_mandir}/man1/koan.1.gz
%{_mandir}/man1/cobbler-register.1.gz
/var/log/koan
%doc AUTHORS COPYING README


#
# package: cobbler-web
#

%package -n cobbler-web

Summary: Web interface for Cobbler
Group: Applications/System
Requires: python(abi) >= %{pyver}
Requires: cobbler

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 6
Requires: httpd
Requires: Django >= 1.4
Requires: mod_wsgi
%endif

%if 0%{?suse_version} >= 1230
Requires: apache2
Requires: apache2-mod_wsgi
Requires: python-django
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
%defattr(-,root,root,-)
%doc AUTHORS COPYING README

%dir %{apache_etc}
%dir %{apache_etc}/conf.d
%config(noreplace) %{apache_etc}/conf.d/cobbler_web.conf
%{apache_dir}/cobbler_webui_content/

%if 0%{?fedora} >=18 || 0%{?rhel} >= 6
%defattr(-,apache,apache,-)
/usr/share/cobbler/web
%dir %attr(700,apache,root) /var/lib/cobbler/webui_sessions
%endif

%if 0%{?suse_version} >= 1230
%defattr(-,%{apache_user},%{apache_group},-)
/usr/share/cobbler/web
%dir %attr(700,%{apache_user},%{apache_group}) /var/lib/cobbler/webui_sessions
%endif


%changelog
* Sat Feb 15 2014 Jörgen Maas <jorgen.maas@gmail.com> 2.4.2
* Mon Feb 03 2014 Jörgen Maas <jorgen.maas@gmail.com> 2.4.1
* Thu Jun 20 2013 James Cammarata <jimi@sngx.net> 2.4.0-1
* Sun Jun 17 2012 James Cammarata <jimi@sngx.net> 2.2.3-2
* Tue Jun 05 2012 James Cammarata <jimi@sngx.net> 2.2.3-1
* Tue Nov 15 2011 Scott Henson <shenson@redhat.com> 2.2.2-1
* Wed Oct 05 2011 Scott Henson <shenson@redhat.com> 2.2.1-1
* Wed Oct 05 2011 Scott Henson <shenson@redhat.com> 2.2.0-1
* Tue Apr 27 2010 Scott Henson <shenson@redhat.com> - 2.0.4-1
* Thu Apr 15 2010 Devan Goodwin <dgoodwin@rm-rf.ca> 2.0.3.2-1
* Mon Mar  1 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-3
* Mon Mar  1 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-2
* Mon Feb 15 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-1
* Thu Feb 11 2010 Scott Henson <shenson@redhat.com> - 2.0.3-1
* Mon Nov 23 2009 John Eckersberg <jeckersb@redhat.com> - 2.0.2-1
* Tue Sep 15 2009 Michael DeHaan <michael.dehaan AT gmail> - 2.0.0-1

# EOF
