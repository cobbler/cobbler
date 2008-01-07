%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Summary: Boot server configurator
Name: cobbler
AutoReq: no
Version: 0.7.1
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPLv2+
Group: Applications/System
Requires: python >= 2.3
Requires: httpd
Requires: tftp-server
Requires: python-devel
Requires: createrepo
Requires: mod_python
Requires: python-cheetah
Requires: rhpl
Requires: rsync
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
BuildRequires: redhat-rpm-config
BuildRequires: python-devel
BuildRequires: python-cheetah
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
ExcludeArch: ppc
Url: http://cobbler.et.redhat.com

%description

Cobbler is a network boot and update server.  Cobbler 
supports PXE, provisioning virtualized images, and 
reinstalling existing Linux machines.  The last two 
modes require a helper tool called 'koan' that 
integrates with cobbler.  Cobbler's advanced features 
include importing distributions from DVDs and rsync 
mirrors, kickstart templating, integrated yum 
mirroring, and built-in DHCP Management.  Cobbler has 
a Python API for integration with other GPL systems 
management applications.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT

%post
cp /var/lib/cobbler/distros*  /var/lib/cobbler/backup 2>/dev/null
cp /var/lib/cobbler/profiles* /var/lib/cobbler/backup 2>/dev/null
cp /var/lib/cobbler/systems*  /var/lib/cobbler/backup 2>/dev/null
cp /var/lib/cobbler/repos*    /var/lib/cobbler/backup 2>/dev/null
/usr/bin/cobbler reserialize
/sbin/chkconfig --add cobblerd
/sbin/service cobblerd condrestart


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

%defattr(755,apache,apache)
%dir /var/www/cobbler/web/
/var/www/cobbler/web/*.py*
%dir /var/www/cgi-bin/cobbler/
/var/www/cgi-bin/cobbler/*.cgi

%defattr(755,apache,apache)
%dir /usr/share/cobbler/webui_templates
%defattr(444,apache,apache)
/usr/share/cobbler/webui_templates/*.tmpl

%defattr(4755,apache,apache)
%dir /var/log/cobbler
%dir /var/log/cobbler/kicklog
%dir /var/www/cobbler/
%dir /var/www/cobbler/localmirror
%dir /var/www/cobbler/kickstarts
%dir /var/www/cobbler/kickstarts_sys
%dir /var/www/cobbler/repo_mirror
%dir /var/www/cobbler/repos_profile
%dir /var/www/cobbler/repos_system
%dir /var/www/cobbler/ks_mirror
%dir /var/www/cobbler/ks_mirror/config
%dir /var/www/cobbler/images
%dir /var/www/cobbler/distros
%dir /var/www/cobbler/profiles
%dir /var/www/cobbler/systems
%dir /var/www/cobbler/links
%defattr(755,apache,apache)
%dir /var/www/cobbler/webui
%defattr(444,apache,apache)
/var/www/cobbler/webui/*.css
/var/www/cobbler/webui/*.js
/var/www/cobbler/webui/*.png
/var/www/cobbler/webui/*.html
%defattr(-,root,root)
%dir /tftpboot/pxelinux.cfg
%dir /tftpboot/images
%{_bindir}/cobbler
%{_bindir}/cobblerd
%{_bindir}/cobbler_auth_help
%dir /etc/cobbler
%config(noreplace) /etc/cobbler/*.ks
%config(noreplace) /etc/cobbler/*.template
%config(noreplace) /etc/cobbler/rsync.exclude
%config(noreplace) /etc/logrotate.d/cobblerd_rotate
%config(noreplace) /etc/cobbler/modules.conf
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/yaml
%dir %{python_sitelib}/cobbler/modules
%dir %{python_sitelib}/cobbler/webui
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/yaml/*.py*
%{python_sitelib}/cobbler/server/*.py*
%{python_sitelib}/cobbler/modules/*.py*
%{python_sitelib}/cobbler/webui/*.py*
%{_mandir}/man1/cobbler.1.gz
/etc/init.d/cobblerd
%config(noreplace) /etc/httpd/conf.d/cobbler.conf
%dir /var/log/cobbler/syslog

%defattr(755,root,root)
%dir /var/lib/cobbler
%dir /var/lib/cobbler/kickstarts/
%dir /var/lib/cobbler/backup/
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
%dir /var/lib/cobbler/triggers/sync/pre
%dir /var/lib/cobbler/triggers/sync/post
%dir /var/lib/cobbler/triggers/install/post
%dir /var/lib/cobbler/snippets/

%defattr(744,root,root)
%config(noreplace) /var/lib/cobbler/triggers/sync/post/restart-services.trigger

%defattr(664,root,root)
%config(noreplace) /var/lib/cobbler/settings
%config(noreplace) /var/lib/cobbler/snippets/partition_select
/var/lib/cobbler/elilo-3.6-ia64.efi
/var/lib/cobbler/menu.c32
%defattr(660,root,root)
%config(noreplace) /etc/cobbler/users.digest 

%defattr(664,root,root)
%config(noreplace) /var/lib/cobbler/cobbler_hosts

%defattr(-,root,root)
%doc AUTHORS CHANGELOG README COPYING


%changelog

* Mon Jan 07 2008 Michael DeHaan <mdehaan@redhat.com> - 0.7.1-1
- Upstream changes (see CHANGELOG)
- Generalize what files are included in RPM
- Add new python module directory

* Thu Dec 14 2007 Michael DeHaan <mdehaan@redhat.com> - 0.7.0-1
- Upstream changes (see CHANGELOG), testing branch
- Don't require syslinux
- Added requires on rsync
- Disable autoreq to avoid slurping in perl modules

* Wed Nov 14 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.4-2
- Upstream changes (see CHANGELOG)
- Permissions changes

* Wed Nov 07 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.3-2
- Upstream changes (see CHANGELOG)
- now packaging javascript file(s) seperately for WUI
- backup state files on upgrade 
- cobbler sync now has pre/post triggers, so package those dirs/files
- WebUI now has .htaccess file
- removed yum-utils as a requirement

* Fri Sep 28 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.2-2
- Upstream changes (see CHANGELOG)
- removed syslinux as a requirement (cobbler check will detect absense)
- packaged /var/lib/cobbler/settings as a config file
- added BuildRequires of redhat-rpm-config to help src RPM rebuilds on other platforms
- permissions cleanup
- make license field conform to rpmlint
- relocate cgi-bin files to cobbler subdirectory 
- include the WUI!

* Thu Aug 30 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.1-2
- Upstream changes (see CHANGELOG)

* Thu Aug 09 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.0-1
- Upstream changes (see CHANGELOG)

* Thu Jul 26 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.2-1
- Upstream changes (see CHANGELOG)
- Tweaked description

* Fri Jul 20 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.1-1
- Upstream changes (see CHANGELOG)
- Modified description
- Added logrotate script
- Added findks.cgi

* Wed Jun 27 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.0-1
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

