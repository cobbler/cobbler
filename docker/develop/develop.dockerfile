# vim: ft=dockerfile
# Define the names/tags of the container
#!BuildTag: cobbler-test-github:release33 cobbler-test-github:release33.%RELEASE%

# We are using https://github.com/hadolint/hadolint to lint our Dockerfile.
# We don't want to version pin our dependencies for testing. Always retrieve what is up to date.
# hadolint global ignore=DL3037

# WARNING! This is not in any way production ready. It is just for testing!
FROM opensuse/leap:15.4

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.example
LABEL org.opencontainers.image.title="cobbler-test-github"
LABEL org.opencontainers.image.description="This contains the environment to run the testsuites of Cobbler inside a container."
LABEL org.opencontainers.image.version="release33.%RELEASE%"
LABEL org.opensuse.reference="registry.opensuse.org/home/cobbler-project/github-ci/cobbler-test-github:release33.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opencontainers.image.created="%BUILDTIME%"
# endlabelprefix

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Custom repository
RUN zypper ar https://download.opensuse.org/repositories/home:/cobbler-project:/release33/15.4/ "Cobbler 3.3.x release project (15.4)" \
    && zypper --gpg-auto-import-keys refresh

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
    bind                       \    
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
    xorriso                    \
    && zypper clean

# Add virtualization repository
RUN zypper install -y \
    python3-hivex     \
    python3-pefile    \
    && zypper clean

# Add bootloader packages
RUN zypper install --no-recommends -y \
    syslinux \
    shim \
    ipxe-bootimgs \
    grub2 \
#    grub2-i386-efi \
    grub2-x86_64-efi \
    grub2-arm64-efi \
    && zypper clean

# Required for dhcpd
RUN zypper install --no-recommends -y \
    system-user-nobody                \
    sysvinit-tools \
    && zypper clean

# Required for ldap tests
RUN zypper install --no-recommends -y \
    openldap2                         \
    openldap2-client                  \
    hostname                          \
    python3-ldap \
    && zypper clean

# Required for reposync tests
RUN zypper install --no-recommends -y \
    python3-librepo                   \
    dnf                               \
    dnf-plugins-core                  \
    && zypper clean

# Required for reposync apt test
RUN zypper install --no-recommends -y \
    perl-LockFile-Simple              \
    perl-Net-INET6Glue                \
    perl-LWP-Protocol-https           \
    ed                                \
    debmirror                         \
    && zypper clean

# Dependencies for system-tests
RUN zypper install --no-recommends -y \
    dhcp-server                       \
    iproute2                          \
    qemu-kvm                          \
    time \
    && zypper clean

# Allow dhcpd to listen on any interface
RUN sed -i 's/DHCPD_INTERFACE=""/DHCPD_INTERFACE="ANY"/' /etc/sysconfig/dhcpd

# Add Testuser for the PAM tests
RUN useradd -p "$(perl -e 'print crypt("test", "password")')" test

# Add Developer scripts to PATH
ENV PATH="/code/docker/develop/scripts:${PATH}"

# Install additional packages
RUN zypper install --no-recommends -y \
    python3-codecov                   \
    python3-magic                     \
    python3-pycodestyle               \
    python3-pyflakes                  \
    python3-pytest                    \
    python3-pytest-cov                \
    python3-pytest-mock               \
    python3-pytest-pythonpath \
    && zypper clean

# Enable the Apache Modules
RUN a2enmod version \
    && a2enmod proxy \
    && a2enmod proxy_http \
    && a2enmod wsgi

# create working directory
WORKDIR "/code"
VOLUME ["/code"]

# Set this as an entrypoint
CMD ["/bin/bash"]
