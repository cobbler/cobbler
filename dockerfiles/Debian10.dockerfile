# vim: ft=dockerfile

FROM debian:10

ENV DEBIAN_FRONTEND noninteractive

# TERM=screen is fairly neutral and works with xterm for example, for others
# you might need to pass -e TERM=<terminal>, like rxvt-unicode.
ENV TERM screen
ENV OSCODENAME buster

# Add repo for debbuild and install all packages required
# hadolint ignore=DL3008,DL3015,DL4006
RUN apt-get update -qq && \
    apt-get install -qqy gnupg curl && \
    /bin/sh -c "echo 'deb http://download.opensuse.org/repositories/Debian:/debbuild/Debian_10/ /' > /etc/apt/sources.list.d/debbuild.list" && \
    curl -sL http://download.opensuse.org/repositories/Debian:/debbuild/Debian_10/Release.key | apt-key add - && \
    apt-get update -qq && \
    apt-get install -qqy \
    debbuild \
    debbuild-macros \
    wget \
    pycodestyle \
    pyflakes3 \
    python-django-common \
    python3-cheetah  \
    python3-coverage \
    python3-wheel   \
    python3-distro \
    python3-distutils \
    python3-django \
    python3-dnspython \
    python3-dns  \
    python3-dnsq  \
    python3-future \
    python3-ldap3 \
    python3-netaddr \
    python3-pip \
    python3-pycodestyle \
    python3-pytest \
    python3-setuptools \
    python3-simplejson  \
    python3-sphinx \
    python3-tornado \
    python3-tz \
    python3-yaml \
    liblocale-gettext-perl \
    lsb-release \
    xz-utils \
    bzip2 \
    dpkg-dev \
    tftpd-hpa \
    createrepo \
    rsync \
    xorriso\
    fakeroot \
    patch \
    pax \
    git \
    hardlink \
    apache2 \
    libapache2-mod-wsgi-py3 \
    systemd && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Make /bin/sh point to bash, not dash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "dash dash/sh boolean false" | debconf-set-selections && \
    dpkg-reconfigure dash

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/deb-build

CMD ["/bin/bash", "-c", "make debs"]
