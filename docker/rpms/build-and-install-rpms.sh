#!/bin/bash
# Utility script to build RPMs in a docker/podman container and then install them

set -eo pipefail

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

# Build RPMs
echo "==> Build RPMs ..."
mkdir -p rpm-build
$EXECUTOR run -t -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE"

# Launch container and install cobbler
echo "==> Start container ..."
$EXECUTOR run --cap-add=NET_ADMIN -t -d --name cobbler \
    -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" \
    -v "$PWD/system-tests:/usr/src/cobbler/system-tests" \
    "$IMAGE" /bin/bash

echo "==> Install fresh RPMs ..."
$EXECUTOR exec -t cobbler bash -c 'rpm -Uvh rpm-build/cobbler-*.noarch.rpm'

# openSUSE does not have this file so skip it
if test "${TAG#*opensuse}" == "$TAG"
then
    echo "==> Remove httpd SSL default config which is automatically loaded normally"
    $EXECUTOR exec -t cobbler bash -c 'rm /etc/httpd/conf.d/ssl.conf'
fi

echo "==> Start Supervisor ..."
if $EXECUTOR exec -t cobbler bash -c 'test ! -d "/var/log/supervisor"'
then
    echo "==> /var/log/supervisor does not exist, create it"
    $EXECUTOR exec -t cobbler bash -c 'mkdir -p /var/log/supervisor'
fi
$EXECUTOR exec -t cobbler bash -c 'supervisord -c /etc/supervisord.conf'

echo "==> Show Logs ..."
$EXECUTOR exec -t cobbler bash -c 'cat /var/log/supervisor/supervisor.log'

echo "==> Wait 5 sec. and show Cobbler version ..."
$EXECUTOR exec -t cobbler bash -c 'sleep 5 && cobbler version'

if $RUN_TESTS
then
    echo "==> Running tests ..."
    $EXECUTOR exec -t cobbler bash -c 'pip3 install coverage distro future setuptools sphinx mod_wsgi requests future'
    $EXECUTOR exec -t cobbler bash -c 'pip3 install pyyaml netaddr Cheetah3 pymongo distro'
    $EXECUTOR exec -t cobbler bash -c 'pip3 install dnspython pyflakes pycodestyle pytest pytest-cov codecov'
    $EXECUTOR exec -t cobbler bash -c 'pytest'
fi

if $RUN_SYSTEM_TESTS
then
    echo "==> Wait 15 sec. because supervisord gets two unkown sighups"
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
