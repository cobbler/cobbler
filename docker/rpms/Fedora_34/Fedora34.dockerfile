# vim: ft=dockerfile

FROM fedora:34

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
    python3-dns             \
    python3-file-magic      \
    python3-ldap            \
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
    openldap-servers        \
    openldap-clients        \
    supervisor

# Dependencies for system tests
RUN dnf install -y          \
    dhcp-server             \
    qemu-kvm                \
    time

COPY ./docker/rpms/Fedora_34/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/rpms/Fedora_34/supervisord/conf.d /etc/supervisord/conf.d

ENV FQDN=`hostname`
RUN sscg -f -v \
     --ca-file=/etc/pki/tls/certs/ca-slapd.crt \
     --ca-key-file=/etc/pki/tls/private/ca-slapd.key \
     --ca-key-password=cobbler \
     --cert-file=/etc/pki/tls/certs/slapd.crt \
     --cert-key-file=/etc/pki/tls/private/slapd.key \
     --client-file=/etc/pki/tls/certs/ldap.crt \
     --client-key-file=/etc/pki/tls/private/ldap.key \
     --lifetime=365 \
     --hostname=$FQDN \
     --email=root@$FQDN \
RUN chown ldap:ldap /etc/pki/tls/{certs/slapd.crt,private/slapd.key}
RUN cp /etc/pki/tls/certs/ca-slapd.crt /etc/pki/ca-trust/source/anchors
RUN update-ca-trust
RUN supervisorctl start slapd && ldapadd -Y EXTERNAL -H ldapi:/// -f /test_dir/tests/test_data/ldap_test.ldif

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
