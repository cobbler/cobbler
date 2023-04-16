# Define the names/tags of the container
#!BuildTag: cobbler-test-github:latest cobbler-test-github:main cobbler-test-github:main.%RELEASE%

FROM opensuse/tumbleweed

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.example
LABEL org.opencontainers.image.title="cobbler-test-github"
LABEL org.opencontainers.image.description="This contains the environment to run the testsuites of Cobbler inside a container."
LABEL org.opencontainers.image.version="0.1.0.%RELEASE%"
LABEL org.opensuse.reference="registry.opensuse.org/home/cobbler-project/github-ci/cobbler-test-github:main.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opencontainers.image.created="%BUILDTIME%"
# endlabelprefix

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE
# Add Developer scripts to PATH
ENV PATH="/code/docker/develop/scripts:${PATH}"

# Tmp fix for debugedit
RUN zypper install -y gdb

# Runtime & dev dependencies
RUN zypper install --no-recommends -y \
    acl                        \
    apache2                    \
    apache2-devel              \
    apache2-mod_wsgi           \
    python310-gunicorn         \
    bash-completion            \
    createrepo_c               \
    fence-agents               \
    genders                    \
    git                        \
    gzip                       \
    ipmitool                   \
    make                       \
    curl                       \
    wget2                      \
    python310                  \
    python310-Sphinx           \
    python310-coverage         \
    python310-devel            \
    python310-distro           \
    python310-schema           \
    python310-setuptools       \
    python310-pip              \
    python310-wheel            \
    python310-Cheetah3         \
    python310-distro           \
    python310-dnspython        \
    python310-Jinja2           \
    python310-requests         \
    python310-PyYAML           \
    python310-pykickstart      \
    python310-netaddr          \
    python310-pymongo          \
    python310-pytest-benchmark \
    python3-librepo            \
    rpm-build                  \
    rsync                      \
    supervisor                 \
    tftp                       \
    tree                       \
    util-linux                 \
    vim                        \
    which                      \
    xorriso                    \
    dosfstools

# Add virtualization repository
RUN zypper install -y \
    python3-hivex     \
    python3-pefile

# Add bootloader packages
RUN zypper install --no-recommends -y \
    syslinux \
    shim \
    ipxe-bootimgs \
    grub2 \
    grub2-i386-efi \
    grub2-x86_64-efi
#    grub2-arm64-efi

# Required for dhcpd
RUN zypper install --no-recommends -y \
    system-user-nobody                \
    sysvinit-tools

# Required for ldap tests
RUN zypper install --no-recommends -y \
    openssl-1_1                       \
    openldap2                         \
    openldap2-client                  \
    hostname                          \
    python310-ldap

# Dependencies for system-tests
RUN zypper install --no-recommends -y \
    dhcp-server                       \
    iproute2                          \
    qemu-kvm                          \
    time

# Install packages and dependencies via pip
RUN zypper install --no-recommends -y \
    python310-codecov            \
    python310-magic              \
    python310-pycodestyle        \
    python310-pyflakes           \
    python310-pytest             \
    python310-pytest-cov         \
    python310-pytest-mock

# Required for reposync tests
RUN zypper install --no-recommends -y \
    dnf                               \
    dnf-plugins-core                  \
    wget

# Required for reposync apt test
RUN zypper install --no-recommends -y \
    perl-LockFile-Simple              \
    perl-Net-INET6Glue                \
    perl-LWP-Protocol-https           \
    ed
# FIXME: We don't have debmirror in the right OBS projects.
#RUN dnf install -y http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/d/debmirror-2.35-2.fc35.noarch.rpm

# Clean zypper cache
RUN zypper clean -a

# Add Testuser for the PAM tests
RUN useradd -p $(perl -e 'print crypt("test", "password")') test

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