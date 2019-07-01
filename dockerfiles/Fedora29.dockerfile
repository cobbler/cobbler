FROM fedora:29

RUN dnf makecache

# Dev dependencies
RUN dnf install -y          \
    git                     \
    make                    \
    openssl                 \
    pyflakes                \
    python-devel            \
    python-pep8             \
    python-sphinx           \
    python3-coverage        \
    python3-devel           \
    python3-distro          \
    python3-future          \
    python3-pyflakes        \
    python3-pycodestyle     \
    python3-setuptools      \
    rpm-build

# Runtime dependencies
RUN yum install -y          \
    PyYAML                  \
    httpd                   \
    mod_wsgi                \
    python-cheetah          \
    python-netaddr          \
    python-simplejson

ADD . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make install && make rpms"]
