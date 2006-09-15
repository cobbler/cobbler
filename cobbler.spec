%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Boot server configurator
Name: cobbler
Version: 0.1.1
Release: 6%{?dist}
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
python setup.py install --optimize=1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
sed -e 's|/[^/]*$||' INSTALLED_FILES | grep "site-packages/" | \
sort | uniq | awk '{ print "%attr(755,root,root) %dir " $1}' > INSTALLED_DIRS
cat INSTALLED_FILES INSTALLED_DIRS > INSTALLED_OBJECTS

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{_bindir}/cobbler
%dir %{python_sitelib}/cobbler
%dir %{python_sitelib}/cobbler/yaml
%{python_sitelib}/cobbler/*.py*
%{python_sitelib}/cobbler/yaml/*.py*
%{_mandir}/man1/cobbler.1.gz

%changelog
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
