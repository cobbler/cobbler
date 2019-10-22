#!/bin/bash
# Utility script to build RPMs in a Docker container and then install them

TAG=$1
DOCKERFILE=$2

IMAGE=cobbler:$TAG

# Build container
docker build -t $IMAGE -f $DOCKERFILE .

# Build RPMs
mkdir rpm-build
docker run -ti -v $PWD/rpm-build:/usr/src/cobbler/rpm-build $IMAGE

# Launch container and install cobbler
docker run -d --privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro --name cobbler -v $PWD/rpm-build:/usr/src/cobbler/rpm-build $IMAGE /usr/lib/systemd/systemd --system
docker logs cobbler
docker exec -it cobbler bash -c 'rpm -Uvh rpm-build/cobbler-*.noarch.rpm'
docker exec -it cobbler bash -c 'cobbler --version'

# Clean up
docker stop cobbler
docker rm cobbler
