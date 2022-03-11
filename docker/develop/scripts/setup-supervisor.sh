#!/bin/bash

echo "Copy supervisord confiuration file"
cp -r /code/docker/develop/supervisord/conf.d/* /etc/supervisord.d/
cp /code/docker/develop/supervisord/supervisord.conf /etc/

echo "Setup openLDAP"
/code/docker/develop/scripts/setup-openldap.sh

echo "Setup reposync"
/code/docker/develop/scripts/setup-reposync.sh

echo "Install Cobbler"
cd /code || exit
make install

echo "Load supervisord configuration file and wait 5s"
supervisord -c /etc/supervisord.conf
sleep 5

echo "Load openLDAP database"
ldapadd -Y EXTERNAL -H ldapi:/// -f /code/docker/develop/openldap/test.ldif

echo "Create DHCPD leases file"
touch /var/lib/dhcp/db/dhcpd.leases

echo "Show Cobbler version"
cobbler version

echo "Execute system-test-env"
make system-test-env
