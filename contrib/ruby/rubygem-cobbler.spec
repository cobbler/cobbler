# Generated from cobbler-0.0.1.gem by gem2rpm -*- rpm-spec -*-
%define ruby_sitelib %(ruby -rrbconfig -e "puts Config::CONFIG['sitelibdir']")
%define gemdir %(ruby -rubygems -e 'puts Gem::dir' 2>/dev/null)
%define gemname cobbler
%define geminstdir %{gemdir}/gems/%{gemname}-%{version}
%define installroot %{buildroot}%{geminstdir}

Summary: 	An interface for interacting with a Cobbler server
Name: 		rubygem-%{gemname}
Version: 	0.0.1
Release: 	2%{?dist}
Group: 		Development/Languages
License: 	LGPLv2+
URL: 		http://cobbler.et.redhat.com/
Source0: 	http://fedorapeople.org/~mcpierce/%{gemname}-%{version}.gem
BuildRoot: 	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires: 	rubygems
BuildRequires: 	rubygems
BuildArch: 	noarch
Provides: 	rubygem(%{gemname}) = %{version}

%description
Provides Ruby bindings to interact with a Cobbler server.


%prep

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{gemdir}
gem install --local --install-dir %{buildroot}%{gemdir} \
            --force %{SOURCE0}

for file in %{installroot}/examples/*.rb; do chmod +x $file; done

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root, -)
%{gemdir}/gems/%{gemname}-%{version}/
%{gemdir}/cache/%{gemname}-%{version}.gem
%{gemdir}/specifications/%{gemname}-%{version}.gemspec

%doc %{geminstdir}/COPYING 
%doc %{geminstdir}/NEWS 
%doc %{geminstdir}/README

%{geminstdir}/config/cobbler.yml


%changelog
* Wed Aug 13 2008 Darryl Pierce <dpierce@redhat.com> - 0.0.1-2
- Removed markup of cobbler.yml and a config file. Fixed a few small bugs 
  in the code for using it as a gem.

* Mon Aug 04 2008 Darryl Pierce <dpierce@redhat.com> - 0.0.1-1
- Initial package
