%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Summary: Boot server configurator
Name: cobbler
Version: 0.5.0
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: python >= 2.3
Requires: httpd
Requires: tftp-server
Requires: python-devel
Requires: createrepo
Requires: mod_python
Requires: python-cheetah
Requires: yum-utils
Requires: rhpl
%ifarch i386 i686 x86_64
Requires: syslinux
%endif
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
BuildRequires: python-devel
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
ExcludeArch: ppc
Url: http://cobbler.et.redhat.com

%description

Cobbler is a command line tool for configuration of network
boot and update servers.  It is also available as a Python
library.  Cobbler supports PXE, provisioning virtualized images,
and reinstalling machines that are already running (over SSH).
The last two modes require a helper tool called 'koan' that
integrates with cobbler.  Cobbler's advanced features include
importing distributions from rsync mirrors, kickstart templating,
integrated yum mirroring, kickstart monitoring, and auto-managing
dhcpd.conf.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT

%post
/sbin/chkconfig --add cobblerd


%preun
if [ $1 = 0 ]; then
    /sbin/service cobblerd stop >/dev/null 2>&1 || :
    chkconfig --del cobblerd
fi

%postun
if [ "$1" -ge "1" ]; then
    /sbin/service cobblerd condrestart >/dev/null 2>&1 || :
fi

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files
%defattr(2755,apache,apache)
%dir /var/log/cobbler
%dir /var/log/cobbler/kicklog
%dir /var/www/cobbler/
%dir /var/www/cobbler/localmirror
%dir /var/www/cobbler/kickstarts
%dir /var/www/cobbler/kickstarts_sys
%dir /var/www/cobbler/repo_mirror
%dir /var/www/cobbler/ks_mirror
%dir /var/www/cobbler/ks_mirror/config
%dir /var/www/cobbler/images
%dir /var/www/cobbler/distros
%dir /var/www/cobbler/profiles
%dir /var/www/cobbler/systems
%dir /var/www/cobbler/links
%defattr(-,root,root)
%dir /tftpboot/pxelinux.cfg
%dir /tftpboot/images
%{_bindir}/cobbler
%{_bindir}/cobblerd
%dir /etc/cobbler
%config(noreplace) /etc/cobbler/default.ks
%config(noreplace) /etc/cobbler/kickstart_fc5.ks
%config(noreplace) /etc/cobbler/kickstart_fc6.ks
%config(noreplace) /etc/cobbler/kickstart_fc6_domU.ks
%config(noreplace) /etc/cobbler/dhcp.template
%config(noreplace) /etc/cobbler/dnsmasq.template
%config(noreplace) /etc/cobbler/pxedefault.template
%config(noreplace) /etc/cobbler/pxeprofile.template
%config(noreplace) /etc/cobbler/pxesystem.template
%config(noreplace) /etc/cobbler/pxesystem_ia64.template
%config(noreplace) /etc/cobbler/rsync.exclude
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/yaml
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/yaml/*.py*
%{_mandir}/man1/cobbler.1.gz
/etc/init.d/cobblerd
/etc/httpd/conf.d/cobbler.conf
%dir /var/log/cobbler/syslog
%defattr(2550,root,root)
%dir /var/lib/cobbler
%dir /var/lib/cobbler/triggers/add/distro/pre
%dir /var/lib/cobbler/triggers/add/distro/post
%dir /var/lib/cobbler/triggers/add/profile/pre
%dir /var/lib/cobbler/triggers/add/profile/post
%dir /var/lib/cobbler/triggers/add/system/pre
%dir /var/lib/cobbler/triggers/add/system/post
%dir /var/lib/cobbler/triggers/add/repo/pre
%dir /var/lib/cobbler/triggers/add/repo/post
%dir /var/lib/cobbler/triggers/delete/distro/pre
%dir /var/lib/cobbler/triggers/delete/distro/post
%dir /var/lib/cobbler/triggers/delete/profile/pre
%dir /var/lib/cobbler/triggers/delete/profile/post
%dir /var/lib/cobbler/triggers/delete/system/pre
%dir /var/lib/cobbler/triggers/delete/system/post
%dir /var/lib/cobbler/triggers/delete/repo/pre
%dir /var/lib/cobbler/triggers/delete/repo/post
/var/lib/cobbler/elilo-3.6-ia64.efi
/var/lib/cobbler/menu.c32
%defattr(-,root,root)
%doc AUTHORS CHANGELOG NEWS README COPYING


%changelog

* Wed Jun 12 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.0-1
- Upstream changes (see CHANGELOG)
- Added dnsmasq.template 

* Fri Apr 27 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.9-1
- Upstream changes (see CHANGELOG)

* Thu Apr 26 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.8-1
- Upstream changes (see CHANGELOG)
- Fix defattr in spec file

* Fri Apr 20 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.7-5
- Upstream changes (see CHANGELOG)
- Added triggers to /var/lib/cobbler/triggers

* Thu Apr 05 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.6-0
- Upstream changes (see CHANGELOG)
- Packaged 'config' directory under ks_mirror

* Fri Mar 23 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.5-3
- Upstream changes (see CHANGELOG)
- Fix sticky bit on /var/www/cobbler files

* Fri Mar 23 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.4-0
- Upstream changes (see CHANGELOG)

* Wed Feb 28 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.3-0
- Upstream changes (see CHANGELOG)
- Description cleanup

* Mon Feb 19 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.2-0
- Upstream changes (see CHANGELOG)

* Mon Feb 19 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.1-0
- Bundles menu.c32 (syslinux) for those distros that don't provide it.
- Unbundles Cheetah since it's available at http://www.python.org/pyvault/centos-4-i386/
- Upstream changes (see CHANGELOG)

* Mon Feb 19 2007 Michael DeHaan <mdehaan@redhat.com> - 0.4.0-1
- Upstream changes (see CHANGELOG)
- Cobbler RPM now owns various directories it uses versus creating them using commands.
- Bundling a copy of Cheetah for older distros

* Mon Jan 28 2007 Michael DeHaan <mdehaan@redhat.com> - 0.3.9-1
- Changed init script pre/post code to match FC-E guidelines/example
- Shortened RPM description
- (also see CHANGELOG)

* Thu Jan 24 2007 Michael DeHaan <mdehaan@redhat.com> - 0.3.8-1
- Upstream changes (see CHANGELOG)

* Thu Jan 24 2007 Michael DeHaan <mdehaan@redhat.com> - 0.3.7-1
- Upstream changes (see CHANGELOG)
- Added packaging for new logfile directory and syslog watcher daemon
- Added Requires for mod_python
- Added sample FC6 kickstart that I forgot to add from months ago.  doh!
- Added FC6 mini domU kickstart

* Thu Dec 21 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.6-1
- Upstream changes (see CHANGELOG)
- Description updated
- Added mod_python kickstart watcher script and associated logging changes

* Thu Dec 21 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.5-4
- Upstream changes (see CHANGELOG)
- Added createrepo as Requires
- BuildRequires: python-devel (needed for 2.5)

* Tue Dec 05 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.4-1
- Upstream changes (see CHANGELOG)

* Tue Nov 14 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.3-1
- Upstream changes (see CHANGELOG)

* Thu Oct 26 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.2-1
- Upstream changes (see CHANGELOG)

* Wed Oct 25 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.1-1
- Upstream changes (see CHANGELOG)
- Updated description

* Tue Oct 24 2006 Michael DeHaan <mdehaan@redhat.com> - 0.3.0-1
- Upstream changes (see CHANGELOG)
- Marked files in /etc/cobbler as config
- Marked /etc/cobbler/dhcpd.template as noreplace 

* Tue Oct 24 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.9-1
- Upstream changes (see CHANGELOG)

* Wed Oct 18 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.8-1
- Upstream changes (see CHANGELOG)

* Tue Oct 17 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.7-1
- Upstream changes (see CHANGELOG), includes removing pexpect as a require
- This RPM now builds on RHEL4

* Tue Oct 17 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.6-1
- Upstream changes (see CHANGELOG), includes removing Cheetah as a require

* Mon Oct 16 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.5-1
- Upstream features and bugfixes (see CHANGELOG)
- Packaged additional kickstart file and specfile cleanup

* Thu Oct 12 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.4-1
- Upstream features and bugfixes (see CHANGELOG)

* Mon Oct 9 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.3-1
- Upstream features (see CHANGELOG) & URL update

* Fri Oct 6 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.2-1
- Upstream bugfixes

* Fri Sep 29 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.1-2
- URL update

* Thu Sep 28 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.1-1
- Upstream pull of bugfixes and new remote system "enchant" feature

* Fri Sep 22 2006 Michael DeHaan <mdehaan@redhat.com> - 0.2.0-1
- Lots of new PXE and dhcpd.conf upstream, elilo.efi now included.

* Thu Sep 21 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-8
- Added doc files to doc, removed INSTALLED_FILES code

* Wed Sep 20 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-7
- Upstream updates

* Fri Sep 15 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-6
- Make koan own it's directory, add GPL "COPYING" file.

* Wed Aug 16 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-5
- Spec file tweaks only for FC-Extras

* Thu Jul 20 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-4
- Fixed python import paths in yaml code, which errantly assumed yaml was installed as a module.

* Wed Jul 12 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.1-3
- Added templating support using Cheetah

* Thu Jul 9 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.0-2
- Fedora-Extras rpm spec tweaks

* Tue Jun 28 2006 Michael DeHaan <mdehaan@redhat.com> - 0.1.0-1
- rpm genesis

