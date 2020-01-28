# vim: ft=dockerfile

FROM centos:7

RUN yum makecache fast && \
    yum install -y epel-release && \
    yum install -y https://repo.ius.io/ius-release-el7.rpm \
                   https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm && \
    yum makecache fast

RUN yum install -y          \
# Dev dependencies
    git                     \
    rsync                   \
    make                    \
    dnf-plugins-core        \
    epel-rpm-macros         \
    openssl                 \
    mod_ssl                 \
    python-sphinx           \
    python36-coverage       \
    python36-devel          \
    python36-distro         \
    python36-future         \
    python36-pyflakes       \
    python36-pycodestyle    \
    python36-setuptools     \
    python36-requests       \
    python36-sphinx         \
    rpm-build

# TEMPORARY !! This package is in EPEL testing since 20200127
# These lines can be deleted once the package has passed.
RUN rpm -ihv https://kojipkgs.fedoraproject.org/packages/python3-cheetah/3.2.4/1.el7/x86_64/python36-cheetah-3.2.4-1.el7.x86_64.rpm

RUN yum install -y          \
# Runtime dependencies
    httpd                   \
    python36-mod_wsgi       \
    python36-pymongo        \
    python36-PyYAML         \
    python36-netaddr        \
    python36-simplejson     \
    python36-tornado        \
    python36-django         \
    python36-dns            \
    python36-ldap3          \
    python36-cheetah        \
    createrepo              \
    xorriso                 \
    grub2-efi-ia32-modules  \
    grub2-efi-x64-modules   \
    logrotate               \
    syslinux                \
    systemd-sysv            \
    tftp-server             \
    fence-agents

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
