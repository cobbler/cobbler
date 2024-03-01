#!/bin/bash

echo "Copy supervisord confiuration file"
cp -r /code/docker/develop/supervisord/conf.d/* /etc/supervisord.d/
cp /code/docker/develop/supervisord/supervisord.conf /etc/

echo "Setup openLDAP"
/code/docker/develop/scripts/setup-openldap.sh

echo "Setup MongoDB"
/code/docker/develop/scripts/setup-mongodb.sh

echo "Install Cobbler"
git config --global --add safe.directory /code
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
