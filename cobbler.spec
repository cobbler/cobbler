%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Boot server configurator
Name: cobbler
Version: 0.2.0
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: python >= 2.3
Requires: httpd
Requires: tftp-server
Requires: python-cheetah
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://et.redhat.com/page/Cobbler_%26_Koan_Provisioning_Tools

%description

Cobbler is a command line tool for simplified configuration of provisioning
servers.  It is also accessible as a Python library.  Cobbler supports PXE,
Xen, and re-provisioning an existing Linux system via auto-kickstart.  The
last two modes require 'koan' to be run on the remote system.

%prep
%setup -q

%build
python setup.py build

%install
rm -rf $RPM_BUILD_ROOT
python setup.py install --optimize=1 --root=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{_bindir}/cobbler
%dir /etc/cobbler
/etc/cobbler/dhcp.template
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/yaml
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/yaml/*.py*
%{_mandir}/man1/cobbler.1.gz
%dir /var/lib/cobbler
%dir /var/www/cobbler
/var/lib/cobbler/elilo-3.6-ia64.efi

%doc AUTHORS CHANGELOG NEWS README COPYING

%changelog
* Fri Sep 22 2006 - 0.2.0-1
- Lots of new PXE and dhcpd.conf upstream, elilo.efi now included.
* Thu Sep 21 2006 - 0.1.1-8
- Added doc files to %doc, removed INSTALLED_FILES code
* Wed Sep 20 2006 - 0.1.1-7
- Upstream updates
* Fri Sep 15 2006 - 0.1.1-6
- Make koan own it's directory, add GPL "COPYING" file.
* Wed Aug 16 2006 - 0.1.1-5
- Spec file tweaks only for FC-Extras
* Thu Jul 20 2006 - 0.1.1-4
- Fixed python import paths in yaml code, which errantly assumed yaml was installed as a module.
* Wed Jul 12 2006 - 0.1.1-3
- Added templating support using Cheetah
* Thu Jul 9 2006 - 0.1.0-2
- Fedora-Extras rpm spec tweaks
* Tue Jun 28 2006 - 0.1.0-1
- rpm genesis
