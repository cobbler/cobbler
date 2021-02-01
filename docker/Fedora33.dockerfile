# vim: ft=dockerfile

FROM fedora:33

RUN dnf makecache

# Dev dependencies
RUN dnf install -y          \
    git                     \
    rsync                   \
    make                    \
    openssl                 \
    mod_ssl                 \
    initscripts             \
    python-sphinx           \
    python3-coverage        \
    python3-devel           \
    python3-wheel           \
    python3-distro          \
    python3-pyflakes        \
    python3-pycodestyle     \
    python3-setuptools      \
    python3-sphinx          \
    python3-pip             \
    rpm-build               \
    which

# Runtime dependencies
RUN yum install -y          \
    httpd                   \
    python3-mod_wsgi        \
    python3-PyYAML          \
    python3-cheetah         \
    python3-netaddr         \
    python3-simplejson      \
    python3-tornado         \
    python3-django          \
    python3-dns             \
    python3-file-magic      \
    python3-ldap3           \
    python3-librepo         \
    python3-pymongo         \
    python3-schema          \
    createrepo_c            \
    dnf-plugins-core        \
    xorriso                 \
    grub2-efi-ia32-modules  \
    grub2-efi-x64-modules   \
    logrotate               \
    syslinux                \
    tftp-server             \
    fence-agents            \
    supervisor

COPY ./docker/Fedora33/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/Fedora33/supervisord/conf.d /etc/supervisord/conf.d

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
