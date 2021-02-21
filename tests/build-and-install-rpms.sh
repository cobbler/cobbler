#!/bin/bash
# Utility script to build RPMs in a Docker container and then install them

set -eo pipefail

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

# Build RPMs
echo "==> Build RPMs ..."
mkdir -p rpm-build
docker run -ti -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE"

# Launch container and install cobbler
echo "==> Start container ..."
docker run -t -d --name cobbler -v "$PWD/rpm-build:/usr/src/cobbler/rpm-build" "$IMAGE" /bin/bash

echo "==> Install fresh RPMs ..."
docker exec -it cobbler bash -c 'rpm -Uvh rpm-build/cobbler-*.noarch.rpm'

# === HACK === HACK === HACK
# To get around this Apache error:
# AH02240: Server should be SSL-aware but has no certificate configured [Hint: SSLCertificateFile] (/etc/httpd/conf.d/cobbler_web.conf:13)
# make cobbler_web listen on HTTP instead of HTTPS.
echo "==> Use HTTP instead of HTTPS ..."
docker exec -it cobbler bash -c 'sed -i s/443/80/g /etc/httpd/conf.d/cobbler_web.conf'
docker exec -it cobbler bash -c 'rm /etc/httpd/conf.d/ssl.conf'
# END === HACK ===

echo "==> Start Supervisor ..."
docker exec -it cobbler bash -c 'supervisord -c /etc/supervisord.conf'

echo "==> Show Logs ..."
docker exec -it cobbler bash -c 'cat /var/log/supervisor/supervisor.log'

echo "==> Wait 5 sec. and show Cobbler version ..."
docker exec -it cobbler bash -c 'sleep 5 && cobbler version'

if $RUN_TESTS
then
    echo "==> Running tests ..."
    docker exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx mod_wsgi requests future'
    docker exec -it cobbler bash -c 'pip3 install pyyaml simplejson netaddr Cheetah3 Django pymongo distro ldap3 librepo'
    docker exec -it cobbler bash -c 'pip3 install dnspython tornado pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it cobbler bash -c 'pytest'
fi

# Clean up
echo "==> Stop Cobbler container ..."
docker stop cobbler
echo "==> Delete Cobbler container ..."
docker rm cobbler
