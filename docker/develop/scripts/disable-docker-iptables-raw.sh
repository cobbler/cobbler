#!/usr/bin/bash

sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf >/dev/null <<EOT
[Service]
Environment="DOCKER_INSECURE_NO_IPTABLES_RAW=1"
EOT
sudo systemctl daemon-reload
sudo systemctl restart docker
echo "Docker iptables raw rules have been disabled."
