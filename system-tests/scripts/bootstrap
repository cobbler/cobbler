#!/bin/sh -e
# Bootstrap the OS for system tests

server=192.168.1.1
bridge=pxe
etc_qemu=$(test -e /etc/qemu-kvm && echo /etc/qemu-kvm || echo /etc/qemu)

ip link add ${bridge} type bridge
ip address add ${server}/24 dev ${bridge}
ip link set up dev ${bridge}

mkdir -p ${etc_qemu}
echo allow ${bridge} >>${etc_qemu}/bridge.conf

cat >/etc/cobbler/settings.d/system-tests.settings <<-EOF
	server: ${server}
	next_server_v4: ${server}
	manage_dhcp: true
	manage_dhcp_v4: true
	manage_dhcp_v6: false
	power_management_default_type: 'ipmilan'
EOF

supervisorctl restart cobblerd

cobbler mkloaders
