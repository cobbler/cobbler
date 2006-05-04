%define name koan
%define version 0.1.0
%define release 1

Summary: Network provisioning tool for Xen and Existing Non-Bare Metal
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Michael DeHaan <mdehaan@redhat.com>
Url: http://bugzilla.redhat.com

%description

koan standards for ’kickstart-over-a-network’ and allows for both
network provisioning of new Xen guests and destructive re-provisioning of
any existing system.  For use with a boot-server configured with
'cobbler'


%prep
%setup

%build
python setup.py build

%install
python setup.py install --optimize=1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
