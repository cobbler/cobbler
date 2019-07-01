# vim: ft=dockerfile

FROM fedora:29

RUN dnf makecache

# Dev dependencies
RUN dnf install -y          \
    git                     \
    make                    \
    openssl                 \
    python-sphinx           \
    python3-coverage        \
    python3-devel           \
    python3-distro          \
    python3-future          \
    python3-pep8            \
    python3-pyflakes        \
    python3-pycodestyle     \
    python3-setuptools      \
    rpm-build

# Runtime dependencies
RUN yum install -y          \
    httpd                   \
    python3-mod_wsgi        \
    python3-PyYAML          \
    python3-cheetah         \
    python3-netaddr         \
    python3-simplejson

ADD . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make install && make rpms"]
