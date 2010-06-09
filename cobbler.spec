%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]" || echo 0)}

%define _binaries_in_noarch_packages_terminate_build 0
%global debug_package %{nil}
Summary: Boot server configurator
Name: cobbler
License: GPLv2+
AutoReq: no
Version: 2.0.4
Release: 1%{?dist}
Source0: cobbler-%{version}.tar.gz
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://fedorahosted.org/cobbler

BuildRequires: redhat-rpm-config
BuildRequires: PyYAML
BuildRequires: python-cheetah

Requires: python >= 2.3
Requires: httpd
Requires: tftp-server
Requires: mod_wsgi
Requires: createrepo
Requires: libyaml
Requires: python-cheetah
Requires: python-devel
Requires: python-netaddr
Requires: python-simplejson
Requires: python-urlgrabber
Requires: PyYAML
Requires: rsync

%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
Requires: python(abi) >= %{pyver}
Requires: genisoimage
%else
Requires: mkisofs
%endif
%if 0%{?fedora} >= 8
BuildRequires: python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif
%if 0%{?fedora} >= 6 || 0%{?rhel} >= 5
Requires: yum-utils
%endif

Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service

%description

Cobbler is a network install server.  Cobbler
supports PXE, virtualized installs, and
reinstalling existing Linux machines.  The last two
modes use a helper tool, 'koan', that
integrates with cobbler.  There is also a web interface
'cobbler-web'.  Cobbler's advanced features
include importing distributions from DVDs and rsync
mirrors, kickstart templating, integrated yum
mirroring, and built-in DHCP/DNS Management.  Cobbler has
a XMLRPC API for integration with other applications.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX
mkdir -p $RPM_BUILD_ROOT/etc/httpd/conf.d
install -p config/cobbler.conf $RPM_BUILD_ROOT/etc/httpd/conf.d/
install -p config/cobbler_web.conf $RPM_BUILD_ROOT/etc/httpd/conf.d/

mkdir -p $RPM_BUILD_ROOT/var/spool/koan

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

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


%files

%defattr(-,root,root,-)

%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd

%config(noreplace) %{_sysconfdir}/cobbler
/etc/init.d/cobblerd

%{python_sitelib}/cobbler

%config(noreplace) /var/lib/cobbler

/var/log/cobbler

%{_mandir}/man1/cobbler.1.gz

%config(noreplace) /etc/httpd/conf.d/cobbler.conf

%if 0%{?fedora} >= 9 || 0%{?rhel} >= 5
%exclude %{python_sitelib}/cobbler/sub_process.py*
%{python_sitelib}/cobbler*.egg-info
%endif

%defattr(-,apache,apache-)
/var/www/cobbler

%doc AUTHORS CHANGELOG README COPYING

%package -n koan

Summary: Helper tool that performs cobbler orders on remote machines.
Group: Applications/System
Requires: python >= 2.0
%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
Requires: python(abi) >= %{pyver}
%endif


%description -n koan

Koan stands for kickstart-over-a-network and allows for both
network installation of new virtualized guests and reinstallation
of an existing system.  For use with a boot-server configured with Cobbler

%files -n koan
%defattr(-,root,root,-)
%dir /var/spool/koan
%{_bindir}/koan
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
%doc AUTHORS COPYING CHANGELOG README


%package -n cobbler-web

Summary: Web interface for Cobbler
Group: Applications/System
Requires: cobbler
Requires: Django
%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
Requires: python(abi) >= %{pyver}
%endif

%description -n cobbler-web

Web interface for Cobbler that allows visiting http://server/cobbler_web to configure the install server.

%files -n cobbler-web
%defattr(-,apache,apache,-)
/usr/share/cobbler/web
%config(noreplace) /etc/httpd/conf.d/cobbler_web.conf
%dir /var/lib/cobbler/webui_sessions
/var/www/cobbler_webui_content/
%doc AUTHORS COPYING CHANGELOG README

%changelog
* Tue Apr 27 2010 Scott Henson <shenson@redhat.com> - 2.0.4-1
- Bug fix release, see Changelog for details

* Thu Apr 15 2010 Devan Goodwin <dgoodwin@rm-rf.ca> 2.0.3.2-1
- Tagging for new build tools.

* Mon Mar  1 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-3
- Bump release because I forgot cobbler-web

* Mon Mar  1 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-2
- Remove requires on mkinitrd as it is not used

* Mon Feb 15 2010 Scott Henson <shenson@redhat.com> - 2.0.3.1-1
- Upstream Brown Paper Bag Release (see CHANGELOG)

* Thu Feb 11 2010 Scott Henson <shenson@redhat.com> - 2.0.3-1
- Upstream changes (see CHANGELOG)

* Mon Nov 23 2009 John Eckersberg <jeckersb@redhat.com> - 2.0.2-1
- Upstream changes (see CHANGELOG)

* Tue Sep 15 2009 Michael DeHaan <mdehaan@redhat.com> - 2.0.0-1
- First release with unified spec files
