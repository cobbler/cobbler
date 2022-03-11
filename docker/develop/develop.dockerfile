# vim: ft=dockerfile

# WARNING! This is not in any way production ready. It is just for testing!
FROM registry.opensuse.org/opensuse/leap:15.3

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Runtime & dev dependencies
RUN zypper install --no-recommends -y \
    acl                        \
    apache2                    \
    apache2-devel              \
    apache2-mod_wsgi-python3   \
    bash-completion            \
    createrepo_c               \
    fence-agents               \
    genders                    \
    git                        \
    gzip                       \
    ipmitool                   \
    make                       \
    python3                    \
    python3-Sphinx             \
    python3-coverage           \
    python3-devel              \
    python3-distro             \
    python3-schema             \
    python3-setuptools         \
    python3-pip                \
    python3-wheel              \
    python3-Cheetah3           \
    python3-distro             \
    python3-dnspython          \
    python3-Jinja2             \
    python3-requests           \
    python3-PyYAML             \
    python3-pykickstart        \
    python3-netaddr            \
    python3-pymongo            \
    rpm-build                  \
    rsync                      \
    supervisor                 \
    tftp                       \
    tree                       \
    util-linux                 \
    vim                        \
    wget                       \
    which                      \
    xorriso

# Add virtualization repository
RUN zypper ar https://download.opensuse.org/repositories/Virtualization/15.3/Virtualization.repo
RUN zypper --gpg-auto-import-keys install -y --from "Virtualization (15.3)" python3-hivex
RUN zypper rr "Virtualization (15.3)"
RUN zypper ar https://download.opensuse.org/repositories/devel:/languages:/python/15.3/devel:languages:python.repo
RUN zypper --gpg-auto-import-keys install -y --from "Python Modules (15.3)" python3-pefile
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
    dnf-plugins-core                  \
    wget

# Required for reposync apt test
RUN zypper install --no-recommends -y \
    perl-LockFile-Simple              \
    perl-Net-INET6Glue                \
    perl-LWP-Protocol-https           \
    ed
RUN dnf install -y http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/d/debmirror-2.35-2.fc35.noarch.rpm

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

# Update pip
RUN pip3 install --upgrade pip

# Install packages and dependencies via pip
RUN pip3 install      \
    codecov           \
    file-magic        \
    pycodestyle       \
    pyflakes          \
    pytest            \
    pytest-cov        \
    pytest-mock       \
    pytest-pythonpath

# Enable the Apache Modules
RUN ["a2enmod", "version"]
RUN ["a2enmod", "proxy"]
RUN ["a2enmod", "proxy_http"]
RUN ["a2enmod", "wsgi"]

# create working directory
RUN ["mkdir", "/code"]
VOLUME ["/code"]
WORKDIR "/code"

# Set this as an entrypoint
CMD ["/bin/bash"]
