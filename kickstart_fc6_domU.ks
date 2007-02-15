# DomU kickstart for Fedora Server Spin
# Installs 142 packages / 560MB
# Tested with FC6

install
reboot
url --url=$tree

lang en_US.UTF-8
keyboard us
xconfig --driver "fbdev" --resolution 800x600 --depth 24
network --device eth0 --bootproto dhcp
rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac. 
firewall --enabled --port=22:tcp
authconfig --enableshadow --enablemd5
selinux --disabled
timezone --utc America/New_York
bootloader --location=mbr --driveorder=xvda --append="rhgb quiet"

clearpart --all --initlabel --drives=xvda
part /boot --fstype ext3 --size=100 --ondisk=xvda
part pv.2 --size=0 --grow --ondisk=xvda
volgroup domu --pesize=32768 pv.2
logvol / --fstype ext3 --name=lv00 --vgname=domu --size=1024 --grow
logvol swap --fstype swap --name=lv01 --vgname=domu --size=272 --grow --maxsize=544

%packages --nobase
crontabs
dhclient
dhcpv6_client
nfs-utils
openssh-clients
openssh-server
yum

%post
$yum_config_stanza
$kickstart_done

