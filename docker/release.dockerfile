# This dockerfile is thought to create a release so you don't need to install every dependeny on your host.

FROM opensuse/leap:15.2

WORKDIR /build

ENV container docker

# Update the repositories and update any system packages
RUN ["zypper", "-n", "update"]
# Install webserver and system tools needed for Cobbler
RUN ["zypper", "-n", "in", "apache2", "apache2-devel", "acl", "apache2-mod_wsgi-python3", "ipmitool", "rsync"]
RUN ["zypper", "-n", "in", "fence-agents", "genders", "xorriso", "tftp", "hardlink"]
# Install Python dependencies for Cobbler
RUN ["zypper", "-n", "in", "python3", "python3-devel", "python3-pip", "python3-setuptools", "python3-schema"]
RUN ["zypper", "-n", "in", "python3-distro", "python3-ldap", "python3-netaddr", "python3-Django", "python3-pykickstart"]
RUN ["zypper", "-n", "in", "python3-simplejson", "python3-dnspython", "python3-Cheetah3", "python3-PyYAML"]
# Packages for building & installing Cobbler from source
RUN ["zypper", "-n", "in", "make", "gzip", "sed", "git", "hg", "python3-wheel", "python3-Sphinx"]
# Packages for linting
RUN ["zypper", "-n", "in", "python3-pyflakes", "python3-pycodestyle"]
# Packages for testing
RUN ["zypper", "-n", "in", "python3-pytest", "python3-pytest-cov", "python3-codecov", "python3-coverage"]

# Install and upgrade pip
RUN ["pip3", "install", "--upgrade", "pip"]

VOLUME [ "/build" ]

# Set this as an entrypoint
CMD make release
