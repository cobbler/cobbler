# vim: ft=dockerfile

FROM rockylinux:8

RUN dnf makecache && \
    dnf install -y epel-release dnf-utils && \
    dnf config-manager --set-enabled powertools && \
    dnf makecache

# overlay2 bug with yum/dnf
#
# OverlayFS only implements a subset of POSIX standards. This can cause RPM db corruption.
# See bottom of https://docs.docker.com/storage/storagedriver/overlayfs-driver/
# Since there is no dnf-plugin-ovl for CentOS 8 yet, we need to touch /var/lib/rpm/* before
# 'dnf install' to avoid the issue.

# Dev dependencies
RUN touch /var/lib/rpm/* &&   \
    dnf install -y            \
    iproute                   \
    git                       \
    rsync                     \
    make                      \
    openssl                   \
    mod_ssl                   \
    initscripts               \
    python3-sphinx            \
    platform-python-coverage  \
    python3-devel             \
    python3-wheel             \
    python3-distro            \
    python3-pyflakes          \
    python3-pycodestyle       \
    python3-setuptools        \
    python3-sphinx            \
    python3-schema            \
    epel-rpm-macros           \
    rpm-build                 \
    which

# Runtime dependencies
RUN touch /var/lib/rpm/* &&   \
    dnf install -y            \
    httpd                     \
    python3-mod_wsgi          \
    python3-pyyaml            \
    python3-netaddr           \
    python3-cheetah           \
    python3-magic             \
    python3-dns               \
    python3-ldap              \
    python3-librepo           \
    python3-pymongo           \
    createrepo_c              \
    dnf-plugins-core          \
    xorriso                   \
    grub2-efi-ia32-modules    \
    grub2-efi-x64-modules     \
    logrotate                 \
    syslinux                  \
    tftp-server               \
    fence-agents              \
    supervisor

# Dependencies for system tests
RUN touch /var/lib/rpm/* &&   \
    dnf install -y            \
    shim                      \
    ipxe-bootimgs             \
    dhcp-server               \
    qemu-kvm                  \
    time
RUN dnf --enablerepo=plus -y install openldap-servers

COPY ./docker/rpms/Fedora_34/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/rpms/Fedora_34/supervisord/conf.d /etc/supervisord/conf.d

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
