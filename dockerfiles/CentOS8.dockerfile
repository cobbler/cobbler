# vim: ft=dockerfile

FROM centos:8

RUN dnf makecache && \
    dnf install -y epel-release dnf-utils && \
    dnf config-manager --set-enabled PowerTools && \
    dnf makecache

# Dev dependencies
RUN dnf install -y          \
    git                     \
    make                    \
    openssl                 \
    python3-sphinx          \
    platform-python-coverage \
    python3-devel          \
    python3-distro         \
    python3-future         \
    python3-pyflakes       \
    python3-pycodestyle    \
    python3-setuptools \
    python3-sphinx         \
    rpm-build

# Runtime dependencies
RUN dnf install -y          \
    httpd                   \
    python3-mod_wsgi        \
    python3-pyyaml         \
    python3-netaddr        \
    python3-simplejson \
    python3-cheetah \
    python3-tornado

COPY . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make install && make rpms"]
