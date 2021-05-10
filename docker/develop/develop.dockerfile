# vim: ft=dockerfile

# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.3

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
    util-linux                 \
    vim                        \
    which                      \
    xorriso

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

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

# create working directory
RUN ["mkdir", "/code"]
VOLUME ["/code"]
WORKDIR "/code"

# Set this as an entrypoint
CMD ["/bin/bash"]
