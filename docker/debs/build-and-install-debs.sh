#!/bin/bash
# Utility script to build DEBs in a Docker container and then install them

set -euo pipefail

RUN_TESTS=false
RUN_SYSTEM_TESTS=false
EXECUTOR=docker

if [ "${1}" == "--with-tests" ]; then
    RUN_TESTS=true
    shift
fi

if [ "${1}" == "--with-system-tests" ]; then
    RUN_SYSTEM_TESTS=true
    shift
fi

if [ "${1}" == "--with-podman" ]; then
    EXECUTOR=podman
    shift
fi

TAG=$1
DOCKERFILE=$2

IMAGE=cobbler:$TAG

# Build container
echo "==> Build container ..."
$EXECUTOR build -t "$IMAGE" -f "$DOCKERFILE" .

# Build DEBs
echo "==> Build packages ..."
mkdir -p deb-build tmp
$EXECUTOR run -ti -v "$PWD/deb-build:/usr/src/cobbler/deb-build" -v "$PWD/tmp:/var/tmp" "$IMAGE"

# Launch container and install cobbler
echo "==> Start container ..."
$EXECUTOR run --cap-add=NET_ADMIN -t -d --name cobbler -v "$PWD/deb-build:/usr/src/cobbler/deb-build" "$IMAGE" /bin/bash

echo "==> Install fresh packages ..."
$EXECUTOR exec -it cobbler bash -c 'dpkg -i deb-build/DEBS/all/cobbler*.deb'

echo "==> Restart Apache and Cobbler daemon ..."
$EXECUTOR exec -it cobbler bash -c 'a2enconf cobbler'

echo "==> Start Supervisor"
$EXECUTOR exec -it cobbler bash -c 'supervisord -c /etc/supervisord.conf'

echo "==> Wait 20 sec. and show Cobbler version ..."
$EXECUTOR exec -it cobbler bash -c 'sleep 20 && cobbler --version'

if $RUN_TESTS
then
    # Almost all of these requirement are already satisfied in the Dockerfiles!
    # Also on Debian mod_wsgi is installed as "libapache2-mod-wsgi-py3"
    echo "==> Running tests ..."
    $EXECUTOR exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx requests future'
    $EXECUTOR exec -it cobbler bash -c 'pip3 install pyyaml netaddr Cheetah3 pymongo distro'
    $EXECUTOR exec -it cobbler bash -c 'pip3 install dnspython pyflakes pycodestyle pytest pytest-cov codecov'
    $EXECUTOR exec -it cobbler bash -c 'pytest-3'
fi

if $RUN_SYSTEM_TESTS
then
    echo "==> Wait 15 sec. because supervisord gets two unkown SIGHUPs"
    $EXECUTOR exec -t cobbler bash -c 'sleep 15'
    echo "==> Preparing the container for system tests..."
    $EXECUTOR exec --privileged -t cobbler make system-test-env
    echo "==> Running system tests ..."
    $EXECUTOR exec --privileged -t cobbler make system-test
fi

# Clean up
echo "==> Stop Cobbler container ..."
$EXECUTOR stop cobbler
echo "==> Delete Cobbler container ..."
$EXECUTOR rm cobbler
rm -rf ./tmp
