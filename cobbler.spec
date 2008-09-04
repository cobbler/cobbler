%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Summary: Boot server configurator
Name: cobbler
AutoReq: no
Version: 1.3.0
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
Requires: rsync
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
BuildRequires: redhat-rpm-config
BuildRequires: python-devel
BuildRequires: python-cheetah
%if 0%{?fedora} >= 8
BuildRequires: python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif
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
mirroring, and built-in DHCP/DNS Management.  Cobbler has 
a Python and XMLRPC API for integration with other  
applications.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT

%post
if [ -e /var/lib/cobbler/distros ]; then
    cp /var/lib/cobbler/distros*  /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/profiles* /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/systems*  /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/repos*    /var/lib/cobbler/backup 2>/dev/null
fi
if [ -e /var/lib/cobbler/config ]; then
    cp -a /var/lib/cobbler/config    /var/lib/cobbler/backup 2>/dev/null
fi
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
    /sbin/service httpd condrestart >/dev/null 2>&1 || :
fi

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files

%defattr(755,apache,apache)
%dir /var/www/cobbler/web/
/var/www/cobbler/web/*.py*
%dir /var/www/cobbler/svc/
/var/www/cobbler/svc/*.py*

%defattr(755,apache,apache)
%dir /usr/share/cobbler/webui_templates
%defattr(444,apache,apache)
/usr/share/cobbler/webui_templates/*.tmpl

%defattr(755,apache,apache)
%dir /var/log/cobbler
%dir /var/log/cobbler/kicklog
%dir /var/www/cobbler/
%dir /var/www/cobbler/localmirror
%dir /var/www/cobbler/repo_mirror
%dir /var/www/cobbler/ks_mirror
%dir /var/www/cobbler/ks_mirror/config
%dir /var/www/cobbler/images
%dir /var/www/cobbler/links
%defattr(755,apache,apache)
%dir /var/www/cobbler/webui
%defattr(444,apache,apache)
/var/www/cobbler/webui/*.css
/var/www/cobbler/webui/*.js
/var/www/cobbler/webui/*.png
/var/www/cobbler/webui/*.html

%defattr(755,root,root)
%{_bindir}/cobbler
%{_bindir}/cobblerd
%{_bindir}/cobbler-completion

# %defattr(644,root,root)
# %config(noreplace) /etc/bash_completion.d/cobbler_bash

%defattr(-,root,root)
%dir /etc/cobbler
%config(noreplace) /etc/cobbler/*.ks
%config(noreplace) /etc/cobbler/*.template
%config(noreplace) /etc/cobbler/rsync.exclude
%config(noreplace) /etc/logrotate.d/cobblerd_rotate
%config(noreplace) /etc/cobbler/modules.conf
%config(noreplace) /etc/cobbler/users.conf
%config(noreplace) /etc/cobbler/acls.conf
%config(noreplace) /etc/cobbler/cheetah_macros
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
%config(noreplace) /etc/httpd/conf.d/cobbler_svc.conf
%dir /var/log/cobbler/syslog

%defattr(755,root,root)
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
/var/lib/cobbler/completions

%defattr(744,root,root)
%config(noreplace) /var/lib/cobbler/triggers/sync/post/restart-services.trigger
%config(noreplace) /var/lib/cobbler/triggers/install/pre/status_pre.trigger
%config(noreplace) /var/lib/cobbler/triggers/install/post/status_post.trigger

%defattr(664,root,root)
%config(noreplace) /etc/cobbler/settings
%config(noreplace) /var/lib/cobbler/snippets/partition_select
%config(noreplace) /var/lib/cobbler/snippets/pre_partition_select
%config(noreplace) /var/lib/cobbler/snippets/main_partition_select
%config(noreplace) /var/lib/cobbler/snippets/post_install_kernel_options
/var/lib/cobbler/elilo-3.6-ia64.efi
/var/lib/cobbler/menu.c32
%defattr(660,root,root)
%config(noreplace) /etc/cobbler/users.digest 

%defattr(664,root,root)
%config(noreplace) /var/lib/cobbler/cobbler_hosts

%defattr(-,root,root)
%if 0%{?fedora} > 8
%{python_sitelib}/cobbler*.egg-info
%endif
%doc AUTHORS CHANGELOG README COPYING


%changelog

* Fri Aug 29 2008 Michael DeHaan <mdehaan@redhat.com> - 1.3.0-1
- Upstream changes (see CHANGELOG)

* Fri Sep 04 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.2-1
- Upstream changes (see CHANGELOG)

* Tue Sep 02 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.1-1
- Upstream changes (see CHANGELOG)
- Package unowned directories

* Fri Aug 29 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.0-1
- Upstream changes (see CHANGELOG)

* Tue Jun 10 2008 Michael DeHaan <mdehaan@redhat.com> - 1.0.3-1
- Upstream changes (see CHANGELOG)

* Mon Jun 09 2008 Michael DeHaan <mdehaan@redhat.com> - 1.0.2-1
- Upstream changes (see CHANGELOG)

* Tue Jun 03 2008 Michael DeHaan <mdehaan@redhat.com> - 1.0.1-1
- Upstream changes (see CHANGELOG)
- stop owning files in tftpboot
- condrestart for Apache

* Wed May 27 2008 Michael DeHaan <mdehaan@redhat.com> - 1.0.0-2
- Upstream changes (see CHANGELOG)

* Fri May 16 2008 Michael DeHaan <mdehaan@redhat.com> - 0.9.2-2
- Upstream changes (see CHANGELOG)
- moved /var/lib/cobbler/settings to /etc/cobbler/settings

* Fri May 09 2008 Michael DeHaan <mdehaan@redhat.com> - 0.9.1-1
- Upstream changes (see CHANGELOG)
- packaged /etc/cobbler/users.conf
- remaining CGI replaced with mod_python

* Tue Apr 08 2008 Michael DeHaan <mdehaan@redhat.com> - 0.8.3-2
- Upstream changes (see CHANGELOG)

* Fri Mar 07 2008 Michael DeHaan <mdehaan@redhat.com> - 0.8.2-1
- Upstream changes (see CHANGELOG)

* Wed Feb 20 2008 Michael DeHaan <mdehaan@redhat.com> - 0.8.1-1
- Upstream changes (see CHANGELOG)

* Fri Feb 15 2008 Michael DeHaan <mdehaan@redhat.com> - 0.8.0-2
- Fix egg packaging

* Fri Feb 15 2008 Michael DeHaan <mdehaan@redhat.com> - 0.8.0-1
- Upstream changes (see CHANGELOG)

* Mon Jan 21 2008 Michael DeHaan <mdehaan@redhat.com> - 0.7.2-1
- Upstream changes (see CHANGELOG)
- prune changelog, see git for full

* Mon Jan 07 2008 Michael DeHaan <mdehaan@redhat.com> - 0.7.1-1
- Upstream changes (see CHANGELOG)
- Generalize what files are included in RPM
- Add new python module directory
- Fixes for builds on F9 and later

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
