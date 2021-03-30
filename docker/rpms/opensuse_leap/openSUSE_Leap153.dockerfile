# vim: ft=dockerfile

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
    git                        \
    gzip                       \
    make                       \
    util-linux                 \
    xorriso                    \
    ipmitool                   \
    tftp                       \
    supervisor                 \
    genders                    \
    fence-agents               \
    rsync                      \
    createrepo_c               \
    python3-Sphinx             \
    python3                    \
    python3-Cheetah3           \
    python3-Sphinx             \
    python3-dnspython          \
    python3-coverage           \
    python3-devel              \
    python3-distro             \
    python3-file-magic         \
    python3-ldap               \
    python3-netaddr            \
    python3-pyflakes           \
    python3-pycodestyle        \
    python3-schema             \
    python3-setuptools         \
    python3-simplejson         \
    python3-pip                \
    python3-PyYAML             \
    python3-wheel              \
    rpm-build                  \
    which

COPY ./docker/rpms/opensuse_leap/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/rpms/opensuse_leap/supervisord/conf.d /etc/supervisord/conf.d

# Build RPMs
COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler
VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
