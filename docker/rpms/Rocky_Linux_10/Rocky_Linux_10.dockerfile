# vim: ft=dockerfile

FROM rockylinux/rockylinux:10

RUN dnf makecache && \
    dnf install -y epel-release dnf-utils && \
    dnf config-manager --set-enabled crb && \
    dnf config-manager --set-enabled highavailability && \
    dnf makecache

# Add the Cobbler 4.0.x release repository from OBS, for packages not yet available in upstream distro
# repositories (e.g. libcobblersignatures)
RUN dnf config-manager --add-repo https://download.opensuse.org/repositories/systemsmanagement:/cobbler:/release40/RockyLinux_10/systemsmanagement:cobbler:release40.repo && \
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
    systemd-devel             \
    cyrus-sasl-devel          \
    initscripts               \
    python3-pip               \
    python3-sphinx            \
    python3-devel             \
    python3-wheel             \
    python3-distro            \
    python3-setuptools        \
    python3-setuptools_scm    \
    python3-sphinx            \
    python3-sphinx_rtd_theme  \
    python3-schema            \
    epel-rpm-macros           \
    pyproject-rpm-macros      \
    rpm-build                 \
    which

# Runtime dependencies
#
# python3-docker (present in every other distro's list here) is deliberately NOT installed: it's only built
# for EPEL starting with EPEL 10.3 (see https://bugs.rockylinux.org and Fedora's package pages for
# python3-docker), while this image is pinned to rockylinux/rockylinux:10, which resolves to 10.2 -- "dnf
# install" for it fails outright with "No match for argument". This is safe to skip: cobbler.spec only lists
# python3-docker as a Recommends (see cobbler.spec's process_management.docker comment), never a
# BuildRequires, so "make rpms" (this image's only job -- see the CMD at the bottom) never needed it, and
# cobbler/modules/process_management/docker.py already handles the "docker" Python SDK being absent by
# opting the module out of the "process_management" category entirely (register() returns ""), rather than
# failing to import. The only real effect of this omission is that this one container can't exercise
# process_management.docker if a test suite is ever run inside it via
# docker/rpms/build-and-install-rpms.sh's "--with-tests" flag (not used by either "make test-rocky10" or
# .github/workflows/packaging.yml's "build-rockylinux10-rpms" job today). Revert once EPEL 10.3 ships
# python3-docker for RockyLinux 10 -- verify with
# "dnf --disablerepo='*' --enablerepo=epel repoquery python3-docker" inside a fresh
# rockylinux/rockylinux:10 container.
RUN touch /var/lib/rpm/* &&   \
    dnf install -y            \
    httpd                     \
    python3-gunicorn          \
    python3-mod_wsgi          \
    python3-pyyaml            \
    python3-netaddr           \
    python3-cheetah           \
    python3-magic             \
    python3-dns               \
    python3-ldap              \
    python3-librepo           \
    python3-pymongo           \
    python3-coverage          \
    libcobblersignatures      \
    createrepo_c              \
    dnf-plugins-core          \
    xorriso                   \
    grub2-efi-x64-modules     \
    logrotate                 \
    syslinux                  \
    tftp-server               \
    supervisor                \
    dosfstools

# Dependencies for system tests
# isc-dhcpd is missing (Kea isn't compatible with Cobbler yet)
RUN touch /var/lib/rpm/* &&   \
    dnf install -y            \
    shim                      \
    ipxe-bootimgs             \
    qemu-kvm                  \
    time
RUN dnf --enablerepo=plus -y install openldap-servers
RUN dnf --enablerepo=highavailability -y install fence-agents-all

COPY ./docker/rpms/Fedora_43/supervisord/supervisord.conf /etc/supervisord.conf
COPY ./docker/rpms/Fedora_43/supervisord/conf.d /etc/supervisord/conf.d

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
