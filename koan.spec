%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Network provisioning tool for Xen and Existing Non-Bare Metal
Name: koan
Version: 0.2.3
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: mkinitrd
Requires: syslinux
Requires: python >= 2.3
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
ExcludeArch: ppc
Url: http://cobbler.et.redhat.com/

%description

Koan stands for kickstart-over-a-network and allows for both
network provisioning of new Xen guests and destructive re-provisioning of
any existing system.  For use with a boot-server configured with
'cobbler'

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
%defattr(-,root,root)
%{_bindir}/koan
%dir %{python_sitelib}/koan
%dir %{python_sitelib}/koan/yaml
%{python_sitelib}/koan/*.py*
%{python_sitelib}/koan/yaml/*.py*
%{_mandir}/man1/koan.1.gz

%doc AUTHORS COPYING CHANGELOG README NEWS

%changelog
* Tue Oct 24 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.2.3-1
- Upstream changes (see CHANGELOG)

* Wed Oct 18 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.2.2-2
- Use __python instead of python, test RPM dir before deletion
- Update URLs

* Mon Oct 09 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.2.2-1
- Upstream change -- support Python 2.3

* Mon Oct 09 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.2.1-1
- Upstream features (see CHANGELOG)

* Thu Sep 28 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-10
- Bumping build rev for FC-E

* Thu Sep 28 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-9
- Excluding PPC since syslinux (gethostip) isn't available for ppc

* Thu Sep 21 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-8
- Added doc files to %doc, removed INSTALLED_FILES code

* Wed Sep 20 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-7
- Upstream updates

* Fri Sep 15 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-6
- Make koan own it's directory, add GPL "COPYING" file.

* Wed Aug 16 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-5
- Spec-file only changes for FC-Extras submission

* Thu Jul 20 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-4
- Fixed python import paths in yaml code, which errantly assumed yaml was installed as a module.

* Fri Jul 12 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.1-3
- allow installing with per-system cobbler data in addition to per-profile

* Thu Jul 09 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.0-2
- rpm tweaks for Fedora Extras

* Wed Jun 28 2006 - Michael DeHaan <mdehaan@redhat.com> - 0.1.0-1
- rpm genesis
