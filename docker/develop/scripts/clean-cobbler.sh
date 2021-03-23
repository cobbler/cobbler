#!/bin/bash

rm /var/lib/cobbler/collections/**/*.json
cp /code/config/cobbler/settings.yaml /etc/cobbler/cobbler.yaml
