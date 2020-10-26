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
    python36-wheel          \
    python36-distro         \
    python36-future         \
    python36-pyflakes       \
    python36-pycodestyle    \
    python36-setuptools     \
    python36-requests       \
    python36-sphinx         \
    rpm-build               \
    which

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
    python36-librepo        \
    createrepo_c            \
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
