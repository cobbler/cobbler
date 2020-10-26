#!/bin/bash
# Utility script to build DEBs in a Docker container and then install them

set -euo pipefail

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
echo "==> Build container ..."
docker build -t "$IMAGE" -f "$DOCKERFILE" .

# Build DEBs
echo "==> Build packages ..."
mkdir -p deb-build tmp
docker run -ti -v "$PWD/deb-build:/usr/src/cobbler/deb-build" -v "$PWD/tmp:/var/tmp" "$IMAGE"

# Launch container and install cobbler
echo "==> Start privileged container with systemd ..."
docker run -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler -v "$PWD/deb-build:/usr/src/cobbler/deb-build" "$IMAGE" /lib/systemd/systemd --system

echo "==> Install fresh packages ..."
docker exec -it cobbler bash -c 'dpkg -i deb-build/DEBS/all/cobbler*.deb'

echo "==> Restart Apache and Cobbler daemon ..."
docker exec -it cobbler bash -c 'a2enconf cobbler cobbler_web && systemctl daemon-reload && systemctl restart apache2 cobblerd'

echo "==> Wait 3 sec. and show Cobbler version ..."
docker exec -it cobbler bash -c 'sleep 3 && cobbler --version'

if $RUN_TESTS
then
    # Almost all of these requirement are already satisfied in the Dockerfiles!
    # Also on Debian mod_wsgi is installed as "libapache2-mod-wsgi-py3"
    echo "==> Running tests ..."
    docker exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx requests future'
    docker exec -it cobbler bash -c 'pip3 install pyyaml simplejson netaddr Cheetah3 Django pymongo distro ldap3 librepo'
    docker exec -it cobbler bash -c 'pip3 install dnspython tornado pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it cobbler bash -c 'pytest-3'
fi

# Clean up
echo "==> Stop Cobbler container ..."
docker stop cobbler
echo "==> Delete Cobbler container ..."
docker rm cobbler
rm -rf ./tmp
