# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.2

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Update Leap to most current packages
RUN ["zypper", "-n", "update"]

# Install runtime dependencies for Cobbler
RUN ["zypper", "-n", "in", "python3", "python3-devel", "python3-pip", "python3-setuptools", "python3-wheel", \
    "python3-distro", "python3-coverage", "python3-schema", "apache2", "apache2-devel", "acl", "ipmitool", \
    "rsync", "fence-agents", "genders", "xorriso", "python3-ldap", "tftp", "python3-Sphinx", "hardlink", "supervisor", \
    "apache2-mod_wsgi-python3"]
RUN ["pip3", "install", "pykickstart"]

# Packages for building & installing cobbler from sourceless
RUN ["zypper", "-n", "in", "make", "gzip", "sed", "git", "hg"]

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

# Set tftpboot location correctly for SUSE distributions
# RUN ["sed", "-e", "\"s|/var/lib/tftpboot|/srv/tftpboot|g\"", "-i", "cobbler/settings.py", "config/cobbler/settings.yaml"]

# Install and setup testing framework
RUN ["pip3", "install", "pytest-django"]
RUN ["pip3", "install", "pytest-pythonpath"]

# Enable the Apache Modules
RUN ["a2enmod", "version"]
RUN ["a2enmod", "proxy"]
RUN ["a2enmod", "proxy_http"]
RUN ["a2enmod", "wsgi"]

WORKDIR /test_dir
COPY . /test_dir
COPY ./tests/setup_files/pam/login /etc/pam.d/login
COPY ./tests/setup_files/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./tests/setup_files/supervisord/conf.d /etc/supervisord/conf.d

# set SECRET_KEY for django tests
#RUN ["sed", "-i", "s/SECRET_KEY.*/'SECRET_KEY\ =\ \"qwertyuiopasdfghl;\"'/", "cobbler/web/settings.py"]

# Install optional stuff
RUN ["pip3", "install", "pymongo", "Jinja2" ]
# Install and upgrade all dependencies
RUN ["pip3", "install", "--upgrade", "pip"]
RUN ["pip3", "install", ".[lint,test]"]

# Install cobbler
RUN ["make", "install"]
RUN ["cp", "/etc/cobbler/cobbler.conf", "/etc/apache2/vhosts.d/"]

# Run rest of the setup script
RUN ["/bin/bash", "-c", "tests/setup-test-docker.sh"]

# Set this as an entrypoint
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
