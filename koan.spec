%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Network provisioning tool for Xen and Existing Non-Bare Metal
Name: koan
Version: 0.1.1
Release: 6%{?dist}
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
%{_bindir}/koan
%dir %{python_sitelib}/koan
%dir %{python_sitelib}/koan/yaml
%{python_sitelib}/koan/*.py*
%{python_sitelib}/koan/yaml/*.py*
%{_mandir}/man1/koan.1.gz

%changelog
* Fri Sep 15 2006 - 0.1.1-6
- Make koan own it's directory, add GPL "COPYING" file.
* Wed Aug 16 2006 - 0.1.1-5
- Spec-file only changes for FC-Extras submission
* Thu Jul 20 2006 - 0.1.1-4
- Fixed python import paths in yaml code, which errantly assumed yaml was installed as a module.
* Fri Jul 12 2006 - 0.1.1-3
- allow installing with per-system cobbler data in addition to per-profile
* Thu Jul 09 2006 - 0.1.0-2
- rpm tweaks for Fedora Extras
* Wed Jun 28 2006 - 0.1.0-1
- rpm genesis
