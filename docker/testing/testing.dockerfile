# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.2

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Update Leap to most current packages
RUN zypper update -y

# Runtime & dev dependencies
RUN zypper install -y          \
    acl                        \
    apache2                    \
    apache2-devel              \
    apache2-mod_wsgi-python3   \
    bash-completion            \
    createrepo_c               \
    fence-agents               \
    genders                    \
    git                        \
    gzip                       \
    hardlink                   \
    ipmitool                   \
    make                       \
    python3                    \
    python3-Sphinx             \
    python3-coverage           \
    python3-devel              \
    python3-distro             \
    python3-schema             \
    python3-setuptools         \
    python3-simplejson         \
    python3-pip                \
    python3-wheel              \
    rpm-build                  \
    rsync                      \
    supervisor                 \
    tftp                       \
    tree                       \
    vim                        \
    which                      \
    xorriso

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

# Set tftpboot location correctly for SUSE distributions
# RUN ["sed", "-e", "\"s|/var/lib/tftpboot|/srv/tftpboot|g\"", "-i", "cobbler/settings.py", "config/cobbler/settings.yaml"]

# Update pip
RUN pip3 install --upgrade pip

# Install packages and dependencies via pip
RUN pip3 install      \
    Cheetah3          \
    codecov           \
    distro            \
    dnspython         \
    file-magic        \
    Jinja2            \
    ldap3             \
    netaddr           \
    pycodestyle       \
    pyflakes          \
    pykickstart       \
    pymongo           \
    pytest            \
    pytest-cov        \
    pytest-mock       \
    pytest-pythonpath \
    pyyaml            \
    requests

# Enable the Apache Modules
RUN ["a2enmod", "version"]
RUN ["a2enmod", "proxy"]
RUN ["a2enmod", "proxy_http"]
RUN ["a2enmod", "wsgi"]

# Create working directory and copy necessary files
WORKDIR /test_dir
COPY . /test_dir
COPY ./docker/testing/pam/login /etc/pam.d/login
COPY ./docker/testing/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/testing/supervisord/conf.d /etc/supervisord/conf.d

# Install cobbler
RUN ["make", "install"]
RUN ["cp", "/etc/cobbler/cobbler.conf", "/etc/apache2/vhosts.d/"]

# Expose the Apache Webserver
EXPOSE 80
EXPOSE 443

# Set this as an entrypoint
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
