# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.3

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Update Leap to most current packages
RUN ["zypper", "-n", "update"]

# Install runtime dependencies for Cobbler which don't resolve well via pip
RUN ["zypper", "-n", "in", "python3", "python3-devel", "python3-pip", "python3-setuptools", "python3-wheel", \
    "apache2", "apache2-devel", "acl", "ipmitool", "rsync", "fence-agents", "genders", "xorriso", \
    "tftp", "python3-Sphinx", "supervisor", "apache2-mod_wsgi-python3"]

# Packages for building & installing cobbler from sourceless
RUN ["zypper", "-n", "in", "make", "gzip", "sed", "git", "hg"]

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

# Install and setup testing framework
RUN ["pip3", "install", "--upgrade", "pip"]
RUN ["pip3", "install", "pytest-pythonpath"]

# Enable the Apache Modules
RUN ["a2enmod", "version"]
RUN ["a2enmod", "proxy"]
RUN ["a2enmod", "proxy_http"]
RUN ["a2enmod", "wsgi"]

# Install optional stuff
RUN ["pip3", "install", "pymongo", "Jinja2", "pykickstart" ]
# Install and upgrade all dependencies
RUN ["pip3", "install", "--upgrade", "pip"]
RUN ["pip3", "install", "requests", "pyyaml", "netaddr", "Cheetah3", "distro", "ldap3", "dnspython", "file-magic", \
    "schema"]
RUN ["pip3", "install", "pyflakes", "pycodestyle"]
RUN ["pip3", "install", "pytest", "pytest-cov", "codecov", "pytest-mock"]

RUN ["mkdir", "/code"]
VOLUME ["/code"]
WORKDIR "/code"

# Set this as an entrypoint
CMD ["/bin/bash"]
