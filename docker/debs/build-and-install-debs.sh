#!/bin/bash
# Utility script to build DEBs in a Docker container and then install them

set -eu

SKIP_BUILD=true
RUN_TESTS=false
RUN_SYSTEM_TESTS=false
EXECUTOR=docker

if [ "${1}" = "--with-tests" ]; then
    RUN_TESTS=true
    shift
fi

if [ "${1}" = "--with-system-tests" ]; then
    RUN_SYSTEM_TESTS=true
    shift
fi

if [ "${1}" = "--with-podman" ]; then
    EXECUTOR=podman
    shift
fi

if [ "${1}" = "--skip-build" ]; then
    SKIP_BUILD=false
    shift
fi

TAG=$1
DOCKERFILE=$2

IMAGE=cobbler:$TAG

# Build container
echo "==> Build container ..."
if [ "$EXECUTOR" = "podman" ]
then
    podman build --format docker -t "$IMAGE" -f "$DOCKERFILE" .
else
    docker build -t "$IMAGE" -f "$DOCKERFILE" .
fi

if $SKIP_BUILD
then
    # Build DEBs
    echo "==> Build packages ..."
    mkdir -p deb-build
    $EXECUTOR run -ti -v "$PWD/deb-build:/usr/src/cobbler/deb-build" "$IMAGE"
fi

# Launch container and install cobbler
echo "==> Start container ..."
$EXECUTOR run --cap-add=NET_ADMIN -t -d --name cobbler -v "$PWD/deb-build:/usr/src/cobbler/deb-build" "$IMAGE" /bin/bash

echo "==> Install fresh packages ..."
$EXECUTOR exec -it cobbler bash -c 'dpkg -i deb-build/cobbler*.deb'

echo "==> Restart Apache and Cobbler daemon ..."
$EXECUTOR exec -it cobbler bash -c 'a2enmod proxy && a2enmod proxy_http'
$EXECUTOR exec -it cobbler bash -c 'a2enconf cobbler'

echo "==> Create DHCPD leases file"
$EXECUTOR exec -it cobbler bash -c 'touch /var/lib/dhcp/dhcpd.leases'

echo "==> Create webroot directory ..."
$EXECUTOR exec -it cobbler bash -c 'mkdir /var/www/cobbler'

echo "==> Start Supervisor"
$EXECUTOR exec -it cobbler bash -c 'supervisord -c /etc/supervisor/supervisord.conf'

echo "==> Wait 10 sec. and show Cobbler version ..."
$EXECUTOR exec -it cobbler bash -c 'sleep 10 && cobbler --version'

if $RUN_TESTS
then
    # Almost all of these requirement are already satisfied in the Dockerfiles!
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
