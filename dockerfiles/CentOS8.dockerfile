# vim: ft=dockerfile

FROM centos:8

RUN dnf makecache && \
    dnf install -y epel-release dnf-utils && \
    dnf config-manager --set-enabled PowerTools && \
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
    python3-future            \
    python3-pyflakes          \
    python3-pycodestyle       \
    python3-setuptools        \
    python3-sphinx            \
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
    python3-simplejson        \
    python3-cheetah           \
    python3-tornado           \
    python3-django            \
    python3-dns               \
    python3-ldap3             \
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
    fence-agents

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
