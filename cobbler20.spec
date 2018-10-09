%if 0%{?fedora}
%global build_py3   1
%global default_py3 1
%endif

%define pythonX %{?default_py3: python3}%{!?default_py3: python2}
%if  0%{?fedora} >= 28  || 0%{?rhel} >= 8
%global python_prefix python2
%else
%global python_prefix python
%global build_py2   1
%endif

%define manzip %{?mageia:xz}%{!?mageia:gz}

%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define _binaries_in_noarch_packages_terminate_build 0
%global debug_package %{nil}
Summary: Boot server configurator
Name: cobbler20
License: GPLv2+
AutoReq: no
Version: 2.0.11
Release: 81%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System

Provides: cobbler = %{version}-%{release}
Obsoletes: cobbler <= %{version}-%{release}

Requires: %{python_prefix}
%if 0%{?suse_version} >= 1000
Requires: apache2
Requires: apache2-mod_python
Requires: tftp
%else
Requires: httpd
Requires: tftp-server
%endif

Requires: mod_wsgi
# syslinux is only available on x86
%if "%{_arch}" == "i386" || "%{_arch}" == "i686" || "%{_arch}" == "x86_64"
Requires: syslinux
%endif

Requires: createrepo
%if 0%{?fedora} || 0%{?rhel} >= 7
Requires: fence-agents-all
%else
Requires: fence-agents
%endif
Requires: genisoimage
Requires: libyaml
Requires: %{python_prefix}-cheetah
Requires: %{python_prefix}-devel
Requires: %{python_prefix}-netaddr
Requires: %{python_prefix}-simplejson
BuildRequires: %{python_prefix}
BuildRequires: %{python_prefix}-setuptools
Requires: %{python_prefix}-urlgrabber
Requires: PyYAML
%if 0%{?suse_version} < 0
BuildRequires: redhat-rpm-config
%endif
Requires: rsync
Requires: yum-utils

%if 0%{?fedora} || 0%{?rhel} >= 7
BuildRequires: systemd
%else
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
%endif

BuildRequires: PyYAML
BuildRequires: %{python_prefix}-cheetah
BuildRequires: /usr/bin/pod2man
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://fedorahosted.org/cobbler

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
make all

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%if 0%{?suse_version} >= 1000
PREFIX="--prefix=/usr"
%endif
%{__python2} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX
%if 0%{?build_py2}
mv $RPM_BUILD_ROOT/usr/bin/koan $RPM_BUILD_ROOT/usr/bin/koan-%{python_version}
mv $RPM_BUILD_ROOT/usr/bin/cobbler-register $RPM_BUILD_ROOT/usr/bin/cobbler-register-%{python_version}
%endif
%if 0%{?build_py3}
make clean
%{__python3} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX
mv $RPM_BUILD_ROOT/usr/bin/koan $RPM_BUILD_ROOT/usr/bin/koan-%{python3_version}
mv $RPM_BUILD_ROOT/usr/bin/cobbler-register $RPM_BUILD_ROOT/usr/bin/cobbler-register-%{python3_version}
%endif
# create links to default script version
%define default_suffix %{?default_py3:-%{python3_version}}%{!?default_py3:-%{python_version}}
ln -s "koan%{default_suffix}" "$RPM_BUILD_ROOT%{_bindir}/koan"
ln -s "cobbler-register%{default_suffix}" "$RPM_BUILD_ROOT%{_bindir}/cobbler-register"
mkdir $RPM_BUILD_ROOT/var/www/cobbler/rendered/
%if ! 0%{?build_py2}
rm -rf $RPM_BUILD_ROOT/%{python2_sitelib}/koan/*
%endif
%if 0%{?fedora} || 0%{?rhel} >= 7
rm $RPM_BUILD_ROOT/etc/init.d/cobblerd
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
install -m 0644 config/cobblerd.service $RPM_BUILD_ROOT%{_unitdir}/
%endif

%post
if [ "$1" = "1" ];
then
    # This happens upon initial install. Upgrades will follow the next else
    if [ -f /etc/init.d/cobblerd ]; then
        /sbin/chkconfig --add cobblerd
    fi
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
%if 0%{?fedora} || 0%{?rhel} >= 7
    /usr/bin/systemctl condrestart cobblerd.service
%else
    /sbin/service cobblerd condrestart
%endif
fi

%preun
if [ $1 = 0 ]; then
    if [ -f /etc/init.d/cobblerd ]; then
        /sbin/service cobblerd stop >/dev/null 2>&1 || :
        chkconfig --del cobblerd || :
    fi
fi

%postun
if [ "$1" -ge "1" ]; then
%if 0%{?fedora} || 0%{?rhel} >= 7
    /usr/bin/systemctl condrestart cobblerd.service >/dev/null 2>&1 || :
    /usr/bin/systemctl condrestart httpd.service >/dev/null 2>&1 || :
%else
    /sbin/service cobblerd condrestart >/dev/null 2>&1 || :
    /sbin/service httpd condrestart >/dev/null 2>&1 || :
%endif
fi


%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files

%defattr(644,apache,apache,755)
%dir /var/www/cobbler/pub/
%dir /var/www/cobbler/web/
/var/www/cobbler/web/index.html
%dir /var/www/cobbler/svc/
%dir /var/www/cobbler/rendered/
/var/www/cobbler/svc/*.py*
/var/www/cobbler/svc/*.wsgi*

%defattr(644,root,root,755)
%dir /usr/share/cobbler/installer_templates
/usr/share/cobbler/installer_templates/*.template
/usr/share/cobbler/installer_templates/defaults

%defattr(644,root,apache,775)
%dir /var/log/cobbler
%dir /var/log/cobbler/tasks
%dir /var/log/cobbler/kicklog
%defattr(644,apache,apache,755)
%dir /var/www/cobbler/
%dir /var/www/cobbler/localmirror
%dir /var/www/cobbler/repo_mirror
%dir /var/www/cobbler/ks_mirror
%dir /var/www/cobbler/ks_mirror/config
%dir /var/www/cobbler/images
%dir /var/www/cobbler/links
%defattr(444,apache,apache,755)
%dir /var/www/cobbler/aux
/var/www/cobbler/aux/anamon
/var/www/cobbler/aux/anamon.init

%defattr(755,root,root,755)
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd

%defattr(644,root,root,755)
%dir /etc/cobbler
%dir /etc/cobbler/pxe
%dir /etc/cobbler/reporting
%dir /etc/cobbler/power
%config(noreplace) /var/lib/cobbler/kickstarts/*.ks
%config(noreplace) /var/lib/cobbler/kickstarts/*.seed
%config(noreplace) /etc/cobbler/*.template
%config(noreplace) /etc/cobbler/pxe/*.template
%config(noreplace) /etc/cobbler/reporting/*.template
%config(noreplace) /etc/cobbler/power/*.template
%config(noreplace) /etc/cobbler/rsync.exclude
%config(noreplace) /etc/logrotate.d/cobblerd_rotate
%config(noreplace) /etc/cobbler/modules.conf
%config(noreplace) /etc/cobbler/users.conf
%config(noreplace) /etc/cobbler/cheetah_macros
%dir %{python2_sitelib}/cobbler
%dir %{python2_sitelib}/cobbler/modules
%{python2_sitelib}/cobbler/*.py*
%{python2_sitelib}/cobbler/modules/*.py*
%{_mandir}/man1/cobbler.1.%{manzip}
%if 0%{?fedora} || 0%{?rhel} >= 7
%{_unitdir}/cobblerd.service
%else
%attr(755,root,root) /etc/init.d/cobblerd
%endif

%if 0%{?suse_version} >= 1000
%config(noreplace) /etc/apache2/conf.d/cobbler.conf
%else
%config(noreplace) /etc/httpd/conf.d/cobbler_wsgi.conf
%exclude /etc/httpd/conf.d/cobbler.conf
%endif

%dir /var/log/cobbler/syslog
%dir /var/log/cobbler/anamon

%defattr(644,root,root,755)
%dir /var/lib/cobbler
%dir /var/lib/cobbler/config/
%dir /var/lib/cobbler/config/distros.d/
%dir /var/lib/cobbler/config/profiles.d/
%dir /var/lib/cobbler/config/systems.d/
%dir /var/lib/cobbler/config/repos.d/
%dir /var/lib/cobbler/config/images.d/
%dir /var/lib/cobbler/kickstarts/
%dir /var/lib/cobbler/backup/
%dir /var/lib/cobbler/triggers
%dir /var/lib/cobbler/triggers/change
%dir /var/lib/cobbler/triggers/add
%dir /var/lib/cobbler/triggers/add/distro
%dir /var/lib/cobbler/triggers/add/distro/pre
%dir /var/lib/cobbler/triggers/add/distro/post
%dir /var/lib/cobbler/triggers/add/profile
%dir /var/lib/cobbler/triggers/add/profile/pre
%dir /var/lib/cobbler/triggers/add/profile/post
%dir /var/lib/cobbler/triggers/add/system
%dir /var/lib/cobbler/triggers/add/system/pre
%dir /var/lib/cobbler/triggers/add/system/post
%dir /var/lib/cobbler/triggers/add/repo
%dir /var/lib/cobbler/triggers/add/repo/pre
%dir /var/lib/cobbler/triggers/add/repo/post
%dir /var/lib/cobbler/triggers/delete
%dir /var/lib/cobbler/triggers/delete/distro
%dir /var/lib/cobbler/triggers/delete/distro/pre
%dir /var/lib/cobbler/triggers/delete/distro/post
%dir /var/lib/cobbler/triggers/delete/profile
%dir /var/lib/cobbler/triggers/delete/profile/pre
%dir /var/lib/cobbler/triggers/delete/profile/post
%dir /var/lib/cobbler/triggers/delete/system
%dir /var/lib/cobbler/triggers/delete/system/pre
%dir /var/lib/cobbler/triggers/delete/system/post
%dir /var/lib/cobbler/triggers/delete/repo
%dir /var/lib/cobbler/triggers/delete/repo/pre
%dir /var/lib/cobbler/triggers/delete/repo/post
%dir /var/lib/cobbler/triggers/sync
%dir /var/lib/cobbler/triggers/sync/pre
%dir /var/lib/cobbler/triggers/sync/post
%dir /var/lib/cobbler/triggers/install
%dir /var/lib/cobbler/triggers/install/pre
%dir /var/lib/cobbler/triggers/install/post
%dir /var/lib/cobbler/snippets/
%dir /var/cache/cobbler
%dir /var/cache/cobbler/buildiso

%defattr(644,root,root,755)
%config(noreplace) /etc/cobbler/settings
/var/lib/cobbler/version
%config(noreplace) /var/lib/cobbler/snippets/*
%dir /var/lib/cobbler/loaders/
/var/lib/cobbler/loaders/zpxe.rexx
%defattr(640,root,root,755)
%config(noreplace) /etc/cobbler/users.digest 

%defattr(644,root,root,755)
%config(noreplace) /var/lib/cobbler/cobbler_hosts

%{python2_sitelib}/cobbler*.egg-info
%doc AUTHORS CHANGELOG README COPYING

%package -n koan20

Summary: Helper tool that performs cobbler orders on remote machines.
Group: Applications/System
Requires: %{pythonX}-koan20 = %{version}-%{release}
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://fedorahosted.org/cobbler/

Provides: koan = %{version}-%{release}
Obsoletes: koan <= %{version}-%{release}
Obsoletes: koan >= 2.2

%description -n koan20

Koan stands for kickstart-over-a-network and allows for both
network installation of new virtualized guests and reinstallation 
of an existing system.  For use with a boot-server configured with Cobbler

%files -n koan20
%defattr(644,root,root,755)
# FIXME: need to generate in setup.py
%dir /var/spool/koan
%{_bindir}/koan
%{_bindir}/cobbler-register
%{_mandir}/man1/koan.1.%{manzip}
%{_mandir}/man1/cobbler-register.1.%{manzip}
%dir /var/log/koan
%doc AUTHORS COPYING CHANGELOG README

%if 0%{?build_py2}

%package -n python2-koan20

Summary: Helper tool that performs cobbler orders on remote machines.
BuildRequires:  python
BuildRequires:  %{python_prefix}-setuptools
Requires:       python

%description -n python2-koan20
Python 2 specific files for koan.

%files -n python2-koan20
%{_bindir}/koan-%{python_version}
%{_bindir}/cobbler-register-%{python_version}
%{python2_sitelib}/koan/
%endif

%if 0%{?build_py3}

%package -n python3-koan20
Summary: Helper tool that performs cobbler orders on remote machines.
%{?python_provide:%python_provide python3-koan20}
BuildRequires:  python3
BuildRequires:  python3-rpm-macros
BuildRequires:  python3-setuptools
Requires:       python3

%description -n python3-koan20
Python 3 specific files for koan.

%files -n python3-koan20
%{_bindir}/koan-%{python3_version}
%{_bindir}/cobbler-register-%{python3_version}
%{python3_sitelib}/koan/
%{python3_sitelib}/koan-*.egg-info

%endif

%package -n cobbler2
Summary: Compatibility package to pull in cobbler from Spacewalk repo
Group: Applications/System
Requires: cobbler20 = %{version}-%{release}

%description -n cobbler2

Compatibility package to pull in cobbler from Spacewalk repo.

%files -n cobbler2

%package -n cobbler-epel
Summary: Compatibility package to pull in cobbler package from EPEL/Fedora
Group: Applications/System
Requires: cobbler >= 2.2
Provides: cobbler2

%description -n cobbler-epel

Compatibility package to pull in cobbler package from EPEL/Fedora.

%files -n cobbler-epel

%package -n cobbler-web

Summary: Web interface for Cobbler
Group: Applications/System
Requires: cobbler
Requires: Django
%if 0%{?suse_version} >= 1000
Requires: apache2-mod_python
%else
Requires: mod_python
%endif
BuildRequires: %{python_prefix}-setuptools
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://fedorahosted.org/cobbler/

%description -n cobbler-web

Web interface for Cobbler that allows visiting http://server/cobbler_web to configure the install server.

%files -n cobbler-web
%defattr(644,apache,apache,755)
%dir /usr/share/cobbler/web
/usr/share/cobbler/web/*
%config(noreplace) /etc/httpd/conf.d/cobbler_web.conf
%dir /var/lib/cobbler/webui_sessions
%dir /var/www/cobbler_webui_content
/var/www/cobbler_webui_content/*
%doc AUTHORS COPYING CHANGELOG README

%changelog
* Tue Oct 09 2018 Michael Mraka <michael.mraka@redhat.com> 2.0.11-81
- updated list of available OSes

* Wed Oct 03 2018 Michael Mraka <michael.mraka@redhat.com> 2.0.11-80
- mageia uses xz to compress man pages

* Tue Oct 02 2018 Michael Mraka <michael.mraka@redhat.com> 2.0.11-79
- use explicit version of python

* Thu Aug 09 2018 Tomas Kasparek <tkasparek@redhat.com> 2.0.11-78
- forbid exposure of private methods in the API

* Wed Apr 04 2018 Jiri Dostal <jdostal@redhat.com> 2.0.11-77
- Root needs write access to cobbler log

* Tue Mar 27 2018 Jiri Dostal <jdostal@redhat.com> 2.0.11-76
- Fix permission issue with cobbler/selinux

* Wed Mar 21 2018 Jiri Dostal <jdostal@redhat.com> 2.0.11-75
- Make cobbler follow fedora packaging guidelines

* Mon Nov 06 2017 Jan Dobes 2.0.11-74
- workaround on Python 2.6 - shlex.split can't parse unicode strings

* Fri Nov 03 2017 Jan Dobes 2.0.11-73
- check_output is not on older (EL6 based) distros, using call from Cobbler 2.8

* Thu Nov 02 2017 Jan Dobes 2.0.11-72
- fixing TypeError - bytes like object expected
- updating from Cobbler 2.8 to support listing using osinfo-query
- support kvm type

* Fri Oct 27 2017 Jan Dobes <jdobes@redhat.com> 2.0.11-71
- 1487007 - copy init info from Cobbler 2.8

* Fri Oct 20 2017 Jan Dobes <jdobes@redhat.com> 2.0.11-70
- specify base version instead of branch to fix tito build

* Wed Oct 18 2017 Jan Dobes 2.0.11-69
- keys() and sort() doesn't work on Python 3
- package both Python 2 and Python 3 versions
- relative imports don't work on both Python 2 and 3

* Mon Oct 16 2017 Jan Dobes 2.0.11-68
- new pod2man doesn't accept empty string as release
- build koan for Python 3
- build koan20 similarly as cobbler20 due to incompatibility with koan from
  EPEL
- has_key is not in Python 3
- Python 3 ethtool and indentation fixes
- make sure list is returned
- make sure it's a string
- open target file in binary mode
- replace iteritems with items
- do not require urlgrabber
- Python 3 compatible string operations
- octal number Python 3 fix
- Python 3 compatible exceptions
- Python 3 compatible prints
- fixing xmlrpclib, urllib2 and local imports in Python 3
- cleanup ANCIENT_PYTHON stuff and unused imports
- exceptions module doesn't have to be imported

* Wed Sep 27 2017 Jan Dobes 2.0.11-67
- 1314379 - updating logrotate config to cobbler 2.8 state

* Tue Sep 26 2017 Jan Dobes 2.0.11-66
- fence-agents-all are on fedora and el7, fence-agents on el6 and suse
- do this on el7 too
- init.d script needs to be executable
- don't include email in changelog generated from commits

* Mon Sep 25 2017 Jan Dobes 2.0.11-65
- new package built with tito

* Fri Dec 24 2010 Scott Henson <shenson@redhat.com> - 2.0.10-1
- New upstream release

* Wed Dec  8 2010 Scott Henson <shenson@redhat.com> - 2.0.9-1
- New upstream release

* Fri Dec  3 2010 Scott Henson <shenson@redhat.com> - 2.0.8-1
- New upstream release

* Mon Oct 18 2010 Scott Henson <shenson@redhat.com> - 2.0.7-1
- Bug fix relase, see Changelog for details

* Tue Jul 13 2010 Scott Henson <shenson@redhat.com> - 2.0.5-1
- Bug fix release, see Changelog for details

* Tue Apr 27 2010 Scott Henson <shenson@redhat.com> - 2.0.4-1
- Bug fix release, see Changelog for details

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

