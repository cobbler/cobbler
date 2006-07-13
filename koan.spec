%define name koan

Summary: Network provisioning tool for Xen and Existing Non-Bare Metal
Name: %{name}
Version: 0.1.1
Release: 3%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: mkinitrd
Requires: syslinux
Requires: python >= 2.3
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://et.redhat.com/page/Cobbler_%26_Koan_Provisioning_Tools

%description

Koan standards for kickstart-over-a-network and allows for both
network provisioning of new Xen guests and destructive re-provisioning of
any existing system.  For use with a boot-server configured with
'cobbler'

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
* Fri Jul 12 2006 - 0.1.1-3
- allow installing with per-system cobbler data in addition to per-profile
* Thu Jul 09 2006 - 0.1.0-2
- rpm tweaks for Fedora Extras
* Wed Jun 28 2006 - 0.1.0-1
- rpm genesis
