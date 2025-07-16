# vim: ft=dockerfile

FROM docker.io/library/debian:12

ENV DEBIAN_FRONTEND noninteractive

# TERM=screen is fairly neutral and works with xterm for example, for others
# you might need to pass -e TERM=<terminal>, like rxvt-unicode.
ENV TERM screen
ENV OSCODENAME bookworm

# Add repo for debbuild and install all packages required
# hadolint ignore=DL3008,DL3015,DL4006
RUN apt-get update -qq && \
    apt-get install -qqy \
    build-essential \
    devscripts \
    dh-python \
    debhelper \
    gnupg \
    curl \
    wget \
    pycodestyle \
    pyflakes3 \
    python3-cheetah  \
    python3-gunicorn  \
    python3-coverage \
    python3-wheel   \
    python3-distro \
    python3-distutils \
    python3-dnspython \
    python3-dns  \
    python3-dnsq  \
    python3-magic  \
    python3-ldap \
    python3-netaddr \
    python3-pip \
    python3-pycodestyle \
    python3-pymongo \
    python3-pytest \
    python3-setuptools \
    python3-simplejson  \
    python3-sphinx \
    python3-tz \
    python3-yaml \
    python3-schema \
    python3-systemd \
    liblocale-gettext-perl \
    lsb-release \
    xz-utils \
    bzip2 \
    dpkg-dev \
    tftpd-hpa \
    createrepo-c \
    isc-dhcp-server \
    rsync \
    xorriso\
    fence-agents\
    fakeroot \
    patch \
    pax \
    git \
    hardlink \
    apache2 \
    iproute2 \
    systemd \
    systemd-sysv \
    supervisor \
    mtools \
    dosfstools && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Make /bin/sh point to bash, not dash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "dash dash/sh boolean false" | debconf-set-selections && \
    dpkg-reconfigure dash

COPY ./docker/debs/Debian_11/supervisord/conf.d /etc/supervisor/conf.d

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/deb-build

CMD ["/bin/bash", "-c", "make debs"]
