%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Summary: Boot server configurator
Name: cobbler
AutoReq: no
Version: 1.2.7
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

* Tue Oct 14 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.7-1
- Upstream changes (see CHANGELOG)

* Fri Oct 07 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.6-1
- Upstream changes (see CHANGELOG)

* Fri Sep 26 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.5-1
- Upstream changes (see CHANGELOG)

* Mon Sep 08 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.4-1
- Rebuild

* Sun Sep 07 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.3-1
- Upstream changes (see CHANGELOG)

* Fri Sep 05 2008 Michael DeHaan <mdehaan@redhat.com> - 1.2.2-1
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

