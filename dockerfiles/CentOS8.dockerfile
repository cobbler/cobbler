# vim: ft=dockerfile

FROM centos:8

RUN yum makecache && \
    yum install -y epel-release dnf-utils && \
    yum config-manager --set-enabled PowerTools && \
    yum makecache

# Dev dependencies
RUN yum install -y          \
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
    rpm-build

# Runtime dependencies
RUN yum install -y          \
    httpd                   \
    mod_wsgi                \
    python3-PyYAML         \
    python3-netaddr        \
    python3-simplejson \
    python3-cheetah

ADD . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make install && make rpms"]
