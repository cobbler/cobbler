# vim: ft=dockerfile

FROM registry.opensuse.org/opensuse/tumbleweed:latest

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

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
    hardlink                   \
    xorriso                    \
    ipmitool                   \
    tftp                       \
    supervisor                 \
    genders                    \
    fence-agents               \
    rsync                      \
    createrepo_c               \
    python-rpm-macros          \
    python3                    \
    python3-Sphinx             \
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
    python3-pip                \
    python3-PyYAML             \
    python3-wheel              \
    rpm-build                  \
    which

# Add bootloader packages
RUN zypper install --no-recommends -y \
    syslinux \
    shim \
    ipxe-bootimgs \
    grub2 \
    grub2-i386-efi \
    grub2-x86_64-efi

# Required for dhcpd
RUN zypper install --no-recommends -y \
    system-user-nobody                \
    sysvinit-tools

# Required for ldap tests
RUN zypper install --no-recommends -y \
    openldap2                         \
    openldap2-client                  \
    hostname

# Dependencies for system-tests
RUN zypper install --no-recommends -y \
    dhcp-server                       \
    iproute2                          \
    qemu-kvm                          \
    time

COPY ./docker/rpms/opensuse_leap/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/rpms/opensuse_leap/supervisord/conf.d /etc/supervisord/conf.d

# Build RPMs
COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler
VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
