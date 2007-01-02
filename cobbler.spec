%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Boot server configurator
Name: cobbler
Version: 0.3.6
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: python >= 2.3
Requires: httpd
Requires: tftp-server
Requires: python-devel
Requires: createrepo
BuildRequires: python-devel
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
ExcludeArch: ppc
Url: http://cobbler.et.redhat.com

%description

Cobbler is a command line tool for configuration of network boot and update servers.  It is also accessible as a Python library.  Cobbler supports PXE, provisioning virtualized images, and reinstalling machines that are already up and running (over SSH).  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from rsync mirrors, kickstart templating, integrated yum mirroring, kickstart monitoring, and auto-managing dhcpd.conf.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,apache,apache)
%dir /var/log/cobbler
%defattr(-,root,root)
%{_bindir}/cobbler
%dir /etc/cobbler
%config(noreplace) /etc/cobbler/default.ks
%config(noreplace) /etc/cobbler/kickstart_fc5.ks
%config(noreplace) /etc/cobbler/dhcp.template
%config(noreplace) /etc/cobbler/default.pxe
%config(noreplace) /etc/cobbler/rsync.exclude
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/yaml
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/yaml/*.py*
%{_mandir}/man1/cobbler.1.gz
%dir /var/lib/cobbler
%dir /var/www/cobbler
%dir /var/log/cobbler
/var/lib/cobbler/elilo-3.6-ia64.efi
/var/www/cobbler/watcher.py
%attr(644, root, root)
/etc/logrotate.d/cimbiote-logrotate

%doc AUTHORS CHANGELOG NEWS README COPYING

%changelog

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

