Summary: Boot server configurator
Name: cobbler
Version: 0.1.1
Release: 4%{?dist}
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
%setup

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

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Thr Jul 19 2006 - 0.1.1-4
- Fixed python import paths in yaml code, which errantly assumed yaml was installed as a module.
* Wed Jul 12 2006 - 0.1.1-3
- Added templating support using Cheetah
* Thu Jul 9 2006 - 0.1.0-2
- Fedora-Extras rpm spec tweaks
* Tue Jun 28 2006 - 0.1.0-1
- rpm genesis
