#
# RPM spec file for all Cobbler packages
#
# Supported build targets:
# - Fedora >= 18
# - RHEL >= 6
# - OpenSuSE >= 13.1
#

%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]" || echo 0)}

%global debug_package %{nil}
%define _binaries_in_noarch_packages_terminate_build 0

%if 0%{?suse_version}
%define apache_dir /srv/www/
%define apache_etc /etc/apache2/conf.d/
%define apache_user wwwrun
%define apache_group www
%endif

%if 0%{?fedora} || 0%{?rhel}
%define apache_dir /var/www/
%define apache_etc /etc/httpd/conf.d/
%define apache_user apache
%define apache_group apache
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
BuildRequires: python-setuptools
Requires: python >= 2.6
Requires: createrepo
Requires: python-netaddr
Requires: python-simplejson
Requires: python-urlgrabber
Requires: rsync
Requires: syslinux
Requires: yum-utils

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 6
BuildRequires: redhat-rpm-config
BuildRequires: PyYAML
BuildRequires: python-cheetah
Requires: python(abi) >= %{pyver}
Requires: genisoimage
Requires: python-cheetah
Requires: PyYAML
Requires: httpd
Requires: mod_wsgi
%endif

%if 0%{?suse_version} >= 1230
BuildRequires: python-PyYAML
BuildRequires: python-Cheetah
Requires: python-PyYAML
Requires: python-Cheetah
Requires: apache2
Requires: apache2-mod_wsgi
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
virtualized installs, and re-installing existing Linux machines.  The
last two modes use a helper tool, 'koan', that integrates with
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
rm $RPM_BUILD_ROOT/etc/cobbler/cobbler.conf
rm $RPM_BUILD_ROOT/etc/cobbler/cobbler_web.conf
mkdir -p $RPM_BUILD_ROOT/etc/logrotate.d
mv config/cobblerd_rotate $RPM_BUILD_ROOT/etc/logrotate.d/cobblerd

mkdir -p $RPM_BUILD_ROOT/var/spool/koan

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 6
mkdir -p $RPM_BUILD_ROOT/var/lib/tftpboot/images
%endif

%if 0%{?suse_version} >= 1230
mkdir -p $RPM_BUILD_ROOT/srv/tftpboot/images
%endif

rm -f $RPM_BUILD_ROOT/etc/cobbler/cobblerd

%if 0%{?fedora} >= 18 || 0%{?suse_version} >= 1230
rm -rf $RPM_BUILD_ROOT/etc/init.d
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mv $RPM_BUILD_ROOT/etc/cobbler/cobblerd.service $RPM_BUILD_ROOT%{_unitdir}

%post
if [ $1 -eq 1 ] ; then
    # Initial installation
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
elif [ "$1" -ge "2" ]; then
    # backup config
    if [ -e /var/lib/cobbler/distros ]; then
        cp /var/lib/cobbler/distros*  /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/profiles* /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/systems*  /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/repos*    /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/networks* /var/lib/cobbler/backup 2>/dev/null
    fi
    if [ -e /var/lib/cobbler/config ]; then
        cp -a /var/lib/cobbler/config    /var/lib/cobbler/backup 2>/dev/null
    fi
    # upgrade older installs
    # move power and pxe-templates from /etc/cobbler, backup new templates to *.rpmnew
    for n in power pxe; do
      rm -f /etc/cobbler/$n*.rpmnew
      find /etc/cobbler -maxdepth 1 -name "$n*" -type f | while read f; do
        newf=/etc/cobbler/$n/`basename $f`
        [ -e $newf ] &&  mv $newf $newf.rpmnew
        mv $f $newf
      done
    done
    # upgrade older installs
    # copy kickstarts from /etc/cobbler to /var/lib/cobbler/kickstarts
    rm -f /etc/cobbler/*.ks.rpmnew
    find /etc/cobbler -maxdepth 1 -name "*.ks" -type f | while read f; do
      newf=/var/lib/cobbler/kickstarts/`basename $f`
      [ -e $newf ] &&  mv $newf $newf.rpmnew
      cp $f $newf
    done
    /bin/systemctl try-restart cobblerd.service >/dev/null 2>&1 || :
fi

%preun
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    /bin/systemctl --no-reload disable cobblerd.service > /dev/null 2>&1 || :
    /bin/systemctl stop cobblerd.service > /dev/null 2>&1 || :
fi

%postun
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
if [ $1 -ge 1 ] ; then
    # Package upgrade, not uninstall
    /bin/systemctl try-restart cobblerd.service >/dev/null 2>&1 || :
fi

%triggerun -- cobbler < 2.0.11-3
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply cobblerd
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save cobblerd >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del cobblerd >/dev/null 2>&1 || :
/bin/systemctl try-restart cobblerd.service >/dev/null 2>&1 || :

%else

%post
if [ "$1" = "1" ];
then
    # This happens upon initial install. Upgrades will follow the next else
    /sbin/chkconfig --add cobblerd
elif [ "$1" -ge "2" ];
then
    # backup config
    if [ -e /var/lib/cobbler/distros ]; then
        cp /var/lib/cobbler/distros*  /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/profiles* /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/systems*  /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/repos*    /var/lib/cobbler/backup 2>/dev/null
        cp /var/lib/cobbler/networks* /var/lib/cobbler/backup 2>/dev/null
    fi
    if [ -e /var/lib/cobbler/config ]; then
        cp -a /var/lib/cobbler/config    /var/lib/cobbler/backup 2>/dev/null
    fi
    # upgrade older installs
    # move power and pxe-templates from /etc/cobbler, backup new templates to *.rpmnew
    for n in power pxe; do
      rm -f /etc/cobbler/$n*.rpmnew
      find /etc/cobbler -maxdepth 1 -name "$n*" -type f | while read f; do
        newf=/etc/cobbler/$n/`basename $f`
        [ -e $newf ] &&  mv $newf $newf.rpmnew
        mv $f $newf
      done
    done
    # upgrade older installs
    # copy kickstarts from /etc/cobbler to /var/lib/cobbler/kickstarts
    rm -f /etc/cobbler/*.ks.rpmnew
    find /etc/cobbler -maxdepth 1 -name "*.ks" -type f | while read f; do
      newf=/var/lib/cobbler/kickstarts/`basename $f`
      [ -e $newf ] &&  mv $newf $newf.rpmnew
      cp $f $newf
    done
    # reserialize and restart
    # FIXIT: ?????
    #/usr/bin/cobbler reserialize
    /sbin/service cobblerd condrestart
fi

%preun
if [ $1 = 0 ]; then
    /sbin/service cobblerd stop >/dev/null 2>&1 || :
    chkconfig --del cobblerd || :
fi

%postun
if [ "$1" -ge "1" ]; then
    /sbin/service cobblerd condrestart >/dev/null 2>&1 || :
    /sbin/service httpd condrestart >/dev/null 2>&1 || :
fi

%endif

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files

%defattr(-,root,root,-)

%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd
%{_sbindir}/tftpd.py*

%config(noreplace) %{_sysconfdir}/cobbler
%config(noreplace) %{_sysconfdir}/logrotate.d/cobblerd

%if 0%{?fedora} >= 18 || 0%{?suse_version} >= 1230
%{_unitdir}/cobblerd.service
%endif

%if 0%{?rhel} == 6
/etc/init.d/cobblerd
%endif

%{python_sitelib}/cobbler

%config(noreplace) /var/lib/cobbler
%exclude /var/lib/cobbler/webui_sessions

/var/log/cobbler
%{apache_dir}/cobbler
%config(noreplace) %{apache_etc}/cobbler.conf

%{_mandir}/man1/cobbler.1.gz
%{python_sitelib}/cobbler*.egg-info

%if 0%{?fedora} >= 18 || 0%{?rhel} >= 6
/var/lib/tftpboot/images
%endif

%if 0%{?suse_version} >= 1230
/srv/tftpboot/images
%endif

%doc AUTHORS README COPYING


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
%dir /var/spool/koan
%dir /var/lib/koan/config
%{_bindir}/koan
%{_bindir}/ovz-install
%{_bindir}/cobbler-register
%{python_sitelib}/koan

%if 0%{?fedora} >= 9 || 0%{?rhel} >= 5
%exclude %{python_sitelib}/koan/sub_process.py*
%exclude %{python_sitelib}/koan/opt_parse.py*
%exclude %{python_sitelib}/koan/text_wrap.py*
%endif

%{_mandir}/man1/koan.1.gz
%{_mandir}/man1/cobbler-register.1.gz
%dir /var/log/koan
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

%config(noreplace) %{apache_etc}/cobbler_web.conf
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
