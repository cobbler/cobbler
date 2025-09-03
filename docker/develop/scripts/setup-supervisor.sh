#!/bin/bash

echo "Copy supervisord confiuration file"
cp -r /code/docker/develop/supervisord/conf.d/* /etc/supervisord.d/
cp /code/docker/develop/supervisord/supervisord.conf /etc/

echo "Setup openLDAP"
/code/docker/develop/scripts/setup-openldap.sh

echo "Setup reposync"
/code/docker/develop/scripts/setup-reposync.sh

echo "Enable Apache2 modules"
a2enmod proxy
a2enmod proxy_http

echo "Install Cobbler"
mkdir /srv/www/cobbler # Create web directory so the Cobbler daemon starts
cd /code || exit
make install
cobblerd setup

echo "Load supervisord configuration file and wait 5s"
supervisord -c /etc/supervisord.conf
sleep 5

echo "Load openLDAP database"
ldapadd -Y EXTERNAL -H ldapi:/// -f /code/docker/develop/openldap/test.ldif

echo "Create DHCPD leases file"
touch /var/lib/dhcp/db/dhcpd.leases

echo "Show Cobbler version"
curl -XPOST -d '<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>extended_version</methodName></methodCall>' http://localhost:25151/

echo "Update pytest"
pip install --break-system-packages -U pytest
