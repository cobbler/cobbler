# vim: ft=dockerfile

FROM centos:7

RUN yum makecache fast && yum install -y epel-release && yum makecache fast

# Dev dependencies
RUN yum install -y          \
    git                     \
    make                    \
    openssl                 \
    python-sphinx           \
    python36-coverage       \
    python36-devel          \
    python36-distro         \
    python36-future         \
    python36-pyflakes       \
    python36-pycodestyle    \
    python36-setuptools     \
    rpm-build

# Runtime dependencies
RUN yum install -y          \
    httpd                   \
    mod_wsgi                \
    python36-PyYAML         \
    python36-netaddr        \
    python36-simplejson

ADD . /usr/src/cobbler
WORKDIR /usr/src/cobbler

VOLUME /usr/src/cobbler/rpm-build

CMD ["/bin/bash", "-c", "make install && make rpms"]
