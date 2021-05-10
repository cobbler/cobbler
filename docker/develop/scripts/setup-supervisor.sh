#!/bin/bash

echo "Copy supervisord confiuration file"
cp -r /code/docker/develop/supervisord/conf.d/* /etc/supervisord.d/
cp /code/docker/develop/supervisord/supervisord.conf /etc/

echo "Install Cobbler"
cd /code || exit
make install

echo "Load supervisord configuration file and wait 2s"
supervisord -c /etc/supervisord.conf
sleep 2

echo "Show Cobbler version"
cobbler version
