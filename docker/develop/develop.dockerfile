# vim: ft=dockerfile

# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.4

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Runtime & dev dependencies
RUN zypper install --no-recommends -y \
    acl                         \
    apache2                     \
    apache2-devel               \
    nginx                       \
    bash-completion             \
    createrepo_c                \
    fence-agents                \
    genders                     \
    git                         \
    gzip                        \
    ipmitool                    \
    make                        \
    curl                        \
    wget2                       \
    python3                     \
    python3-Sphinx              \
    python3-coverage            \
    python3-devel               \
    python3-distro              \
    python3-schema              \
    python3-setuptools          \
    python3-pip                 \
    python3-wheel               \
    python3-Cheetah3            \
    python3-distro              \
    python3-dnspython           \
    python3-Jinja2              \
    python3-requests            \
    python3-PyYAML              \
    python3-pykickstart         \
    python3-pycodestyle         \
    python3-pyflakes            \
    python3-pytest-cov          \
    python3-pytest-mock         \
    python3-pytest-pythonpath   \
    python3-netaddr             \
    python3-pymongo             \
    python3-gunicorn            \
    python3-importlib_resources \
    rpm-build                   \
    rsync                       \
    supervisor                  \
    tftp                        \
    tree                        \
    util-linux                  \
    vim                         \
    wget                        \
    which                       \
    xorriso

# Add virtualization repository
RUN zypper ar https://download.opensuse.org/repositories/Virtualization/15.4/Virtualization.repo
RUN zypper --gpg-auto-import-keys install -y --from "Virtualization (15.4)" python3-hivex
RUN zypper rr "Virtualization (15.3)"
RUN zypper ar https://download.opensuse.org/repositories/devel:/languages:/python/15.4/devel:languages:python.repo
RUN zypper --gpg-auto-import-keys install -y --from "Python Modules (15.4)" python3-pefile
RUN zypper rr "Python Modules (15.3)"

# Add bootloader packages
RUN zypper install --no-recommends -y \
    syslinux \
    shim \
    ipxe-bootimgs \
    grub2 \
    grub2-i386-efi \
    grub2-x86_64-efi \
    grub2-arm64-efi

# Required for dhcpd
RUN zypper install --no-recommends -y \
    system-user-nobody                \
    sysvinit-tools

# Required for ldap tests
RUN zypper install --no-recommends -y \
    openldap2                         \
    openldap2-client                  \
    hostname                          \
    python3-ldap

# Required for reposync tests
RUN zypper install --no-recommends -y \
    python3-librepo                   \
    dnf                               \
    dnf-plugins-core

# Required for reposync apt test
RUN zypper install --no-recommends -y \
    perl-LockFile-Simple              \
    perl-Net-INET6Glue                \
    perl-LWP-Protocol-https           \
    ed
RUN dnf install -y http://download.fedoraproject.org/pub/fedora/linux/releases/37/Everything/x86_64/os/Packages/d/debmirror-2.36-4.fc37.noarch.rpm

# Dependencies for system-tests
RUN zypper install --no-recommends -y \
    dhcp-server                       \
    iproute2                          \
    qemu-kvm                          \
    time

# Allow dhcpd to listen on any interface
RUN sed -i 's/DHCPD_INTERFACE=""/DHCPD_INTERFACE="ANY"/' /etc/sysconfig/dhcpd

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

# Add Developer scripts to PATH
ENV PATH="/code/docker/develop/scripts:${PATH}"

# Install packages and dependencies via pip
RUN pip3 install file-magic
# We need pytest greater 6
RUN pip3 install -U pytest

# Install codecov
RUN curl -Os https://uploader.codecov.io/latest/linux/codecov && chmod +x codecov

# Enable the Apache Modules
RUN ["a2enmod", "version"]
RUN ["a2enmod", "proxy"]
RUN ["a2enmod", "proxy_http"]

# create working directory
RUN ["mkdir", "/code"]
VOLUME ["/code"]
WORKDIR "/code"

# Set this as an entrypoint
CMD ["/bin/bash"]
