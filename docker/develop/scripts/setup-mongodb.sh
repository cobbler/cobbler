#!/bin/bash

wget -O /tmp/mongodb.asc https://pgp.mongodb.com/server-5.0.asc
rpm --import /tmp/mongodb.asc
zypper addrepo --gpgcheck "https://repo.mongodb.org/zypper/suse/15/mongodb-org/5.0/x86_64/" mongodb
zypper -n install mongodb-org
mkdir -p /data/db
