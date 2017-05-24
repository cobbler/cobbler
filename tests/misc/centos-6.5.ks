text
install
url --url=
lang en_US
keyboard us
network --bootproto=dhcp
rootpw --iscrypted Z2flfTXrUtnJM
reboot
firewall --disabled
selinux --disabled
timezone --utc America/New_York
bootloader --location=mbr

zerombr
clearpart --all
autopart

%packages
@Core
%end
