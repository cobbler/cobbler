%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Network provisioning tool for Xen and Bare Metal Machines 
Name: koan
Version: 0.9.1
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Applications/System
Requires: mkinitrd
Requires: syslinux
Requires: python >= 2.2
BuildRequires: python-devel
%if 0%{?fedora} >= 8
BuildRequires: python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
ExcludeArch: ppc
ExcludeArch: ppc64
Url: http://cobbler.et.redhat.com/

%description

Koan stands for kickstart-over-a-network and allows for both
network provisioning of new virtualized guests and destructive re-provisioning 
of any existing system.  For use with a boot-server configured with
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
%if 0%{?fedora} > 8
%{python_sitelib}/koan*.egg-info
%endif
%dir /var/spool/koan
%{_bindir}/koan
%dir %{python_sitelib}/koan
%{python_sitelib}/koan/*.py*
%{_mandir}/man1/koan.1.gz

%doc AUTHORS COPYING CHANGELOG README

%changelog

* Fri May 09 2008 Michael DeHaan <mdehaan@redhat.com> - 0.9.0-1
- Upstream changes (see CHANGELOG)
- truncate changelog (see git for history)

* Thu Jan 31 2008 Michael DeHaan <mdehaan@redhat.com> - 0.6.5-1
- Upstream changes (see CHANGELOG)

* Thu Jan 10 2008 Michael DeHaan <mdehaan@redhat.com> - 0.6.4-1
- Upstream changes (see CHANGELOG)

* Thu Nov 15 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.3-3
- Upstream changes (see CHANGELOG)

* Wed Nov 07 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.3-3
- Release bump to appease the build system.

* Wed Nov 07 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.3-2
- Upstream changes (see CHANGELOG)

* Fri Sep 28 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.2-2
- Upstream changes (see CHANGELOG)

* Thu Aug 30 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.1-2
- Upstream changes (see CHANGELOG)

* Thu Aug 09 2007 Michael DeHaan <mdehaan@redhat.com> - 0.6.0-1
- Upstream changes (see CHANGELOG)

* Thu Jul 26 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.2-1
- Upstream changes (see CHANGELOG)

* Fri Jul 20 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.1-1
- Upstream changes (see CHANGELOG)

* Wed Jun 27 2007 Michael DeHaan <mdehaan@redhat.com> - 0.5.0-1
- Upstream changes (see CHANGELOG)
