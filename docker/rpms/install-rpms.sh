#!/bin/bash
# Utility script to run Docker container without building the RPMs,
# just install them. So make sure they are in rpm-build dir!

if [ "$1" == "--with-tests" ]
then
    RUN_TESTS=true
    shift
else
    RUN_TESTS=false
fi

TAG=$1
IMAGE=cobbler:$TAG

# Launch container and install cobbler
echo "==> Start privileged container with systemd ..."
docker run -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE" /usr/lib/systemd/systemd --system
echo "==> Install fresh RPMs ..."
docker exec -it cobbler bash -c 'rpm -Uvh rpm-build/cobbler-*.noarch.rpm'

echo "==> Wait 3 sec. and show Cobbler version ..."
docker exec -it cobbler bash -c 'sleep 3 && cobbler version'

if $RUN_TESTS
then
    echo "==> Running tests ..."
    docker exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx mod_wsgi requests future'
    docker exec -it cobbler bash -c 'pip3 install pyyaml netaddr Cheetah3 pymongo distro'
    docker exec -it cobbler bash -c 'pip3 install dnspython pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it cobbler bash -c 'pytest'
fi

# Clean up
echo "==> Stop Cobbler container ..."
docker stop cobbler
echo "==> Delete Cobbler container ..."
docker rm cobbler
