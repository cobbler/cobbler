#!/bin/bash
# Utility script to run Docker container without building the DEBs,
# just install them. So make sure they are in deb-build dir!

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
docker run -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler -v "$PWD/deb-build:/usr/src/cobbler/deb-build" "$IMAGE" /lib/systemd/systemd --system

docker exec -it cobbler bash -c 'dpkg -i deb-build/DEBS/all/cobbler*.deb'
docker exec -it cobbler bash -c 'a2enmod proxy proxy_http wsgi && a2enconf cobbler'
docker exec -it cobbler bash -c 'systemctl daemon-reload && systemctl restart apache2 cobblerd'
docker exec -it cobbler bash -c 'sleep 3 && cobbler --version'

if $RUN_TESTS
then
    # Most of these requirement are already satisfied in the Dockerfiles!
    # Also on Debian mod_wsgi is installed as "libapache2-mod-wsgi-py3"
    docker exec -it cobbler bash -c 'pip3 install coverage distro future setuptools sphinx requests future'
    docker exec -it cobbler bash -c 'pip3 install pyyaml netaddr Cheetah3 pymongo distro librepo'
    docker exec -it cobbler bash -c 'pip3 install dnspython pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it cobbler bash -c 'pytest-3'
fi

# Entering the running container
docker exec -ti cobbler bash
