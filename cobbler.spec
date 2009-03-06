%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%define _binaries_in_noarch_packages_terminate_build 0
Summary: Boot server configurator
Name: cobbler
AutoReq: no
Version: 1.7.0
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPLv2+
Group: Applications/System
Requires: python >= 2.3
%if 0%{?suse_version} >= 1000
Requires: apache2
Requires: apache2-mod_python
Requires: tftp
%else
Requires: httpd
Requires: tftp-server
Requires: mod_python
%endif
Requires: python-devel
Requires: createrepo
Requires: python-cheetah
Requires: rsync
Requires: python-netaddr
Requires: PyYAML
BuildRequires: PyYAML
Requires: libyaml
%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
Requires: genisoimage
%else
Requires: mkisofs
%endif
Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
%if 0%{?fedora} >= 11 || 0%{?rhel} >= 6
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]" || echo 0)}
Requires: python(abi) = %{pyver}
%endif
%if 0%{?suse_version} < 0
BuildRequires: redhat-rpm-config
%endif
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
ExcludeArch: ppc64
Url: http://cobbler.et.redhat.com

%description

Cobbler is a network install server.  Cobbler 
supports PXE, virtualized installs, and 
reinstalling existing Linux machines.  The last two 
modes use a helper tool, 'koan', that 
integrates with cobbler.  Cobbler's advanced features 
include importing distributions from DVDs and rsync 
mirrors, kickstart templating, integrated yum 
mirroring, and built-in DHCP/DNS Management.  Cobbler has 
a Python and XMLRPC API for integration with other  
applications.  There is also a web interface.

%prep
%setup -q

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%if 0%{?suse_version} >= 1000
PREFIX="--prefix=/usr"
%endif
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX

%post

# backup config
if [ -e /var/lib/cobbler/distros ]; then
    cp /var/lib/cobbler/distros*  /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/profiles* /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/systems*  /var/lib/cobbler/backup 2>/dev/null
    cp /var/lib/cobbler/repos*    /var/lib/cobbler/backup 2>/dev/null
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

%defattr(755,root,root)
%dir /usr/share/cobbler/installer_templates
%defattr(744,root,root)
/usr/share/cobbler/installer_templates/*.template
%defattr(744,root,root)
/usr/share/cobbler/installer_templates/defaults
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
%dir /var/www/cobbler/aux
%defattr(444,apache,apache)
/var/www/cobbler/webui/*
%ghost /var/www/cobbler/aux/anamon.pyc
%ghost /var/www/cobbler/aux/anamon.pyo
/var/www/cobbler/aux/*.py
/var/www/cobbler/aux/*.init

%defattr(755,root,root)
%{_bindir}/cobbler
%{_bindir}/cobbler-ext-nodes
%{_bindir}/cobblerd

%defattr(-,root,root)
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
%config(noreplace) /etc/cobbler/acls.conf
%config(noreplace) /etc/cobbler/cheetah_macros
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/modules
%dir %{python_sitelib}/cobbler/webui
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/server/*.py*
%{python_sitelib}/cobbler/modules/*.py*
%{python_sitelib}/cobbler/webui/*.py*
%{_mandir}/man1/cobbler.1.gz
/etc/init.d/cobblerd
%if 0%{?suse_version} >= 1000
%config(noreplace) /etc/apache2/conf.d/cobbler.conf
%config(noreplace) /etc/apache2/conf.d/cobbler_svc.conf
%else
%config(noreplace) /etc/httpd/conf.d/cobbler.conf
%config(noreplace) /etc/httpd/conf.d/cobbler_svc.conf
%endif
%dir /var/log/cobbler/syslog
%dir /var/log/cobbler/anamon

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

%defattr(664,root,root)
%config(noreplace) /etc/cobbler/settings
/var/lib/cobbler/version
%config(noreplace) /var/lib/cobbler/snippets/partition_select
%config(noreplace) /var/lib/cobbler/snippets/pre_partition_select
%config(noreplace) /var/lib/cobbler/snippets/main_partition_select
%config(noreplace) /var/lib/cobbler/snippets/post_install_kernel_options
%config(noreplace) /var/lib/cobbler/snippets/network_config
%config(noreplace) /var/lib/cobbler/snippets/pre_install_network_config
%config(noreplace) /var/lib/cobbler/snippets/post_install_network_config
%config(noreplace) /var/lib/cobbler/snippets/func_install_if_enabled
%config(noreplace) /var/lib/cobbler/snippets/func_register_if_enabled
%config(noreplace) /var/lib/cobbler/snippets/download_config_files
%config(noreplace) /var/lib/cobbler/snippets/koan_environment
%config(noreplace) /var/lib/cobbler/snippets/pre_anamon
%config(noreplace) /var/lib/cobbler/snippets/post_anamon
%config(noreplace) /var/lib/cobbler/snippets/post_s390_reboot
%config(noreplace) /var/lib/cobbler/snippets/redhat_register
%config(noreplace) /var/lib/cobbler/snippets/cobbler_register
/var/lib/cobbler/elilo-3.8-ia64.efi
/var/lib/cobbler/menu.c32
/var/lib/cobbler/yaboot-1.3.14
/var/lib/cobbler/zpxe.rexx
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

* Fri Mar 06 2009 Michael DeHaan <mdehaan@redhat.com> - 1.7.0-1
- Development release 1.7 start

