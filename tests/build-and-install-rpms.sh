#!/bin/bash
# Utility script to build RPMs in a Docker container and then install them

if [ "$1" == "--with-tests" ]
then
    RUN_TESTS=true
    shift
else
    RUN_TESTS=false
fi

TAG=$1
DOCKERFILE=$2

IMAGE=cobbler:$TAG

# Build container
docker build -t "$IMAGE" -f "$DOCKERFILE" .

# Build RPMs
mkdir rpm-build
docker run -ti -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE"

# Launch container and install cobbler
docker run -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE" /usr/lib/systemd/systemd --system
docker logs cobbler
docker exec -it cobbler bash -c 'rpm -Uvh rpm-build/cobbler-*.noarch.rpm'
docker exec -it cobbler bash -c 'cobbler --version'

if $RUN_TESTS
then
    docker exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx mod_wsgi requests future'
    docker exec -it cobbler bash -c 'pip3 install pyyaml simplejson netaddr Cheetah3 Django pymongo distro ldap3'
    docker exec -it cobbler bash -c 'pip3 install dnspython tornado pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it cobbler bash -c 'pytest'
fi

# Clean up
docker stop cobbler
docker rm cobbler
