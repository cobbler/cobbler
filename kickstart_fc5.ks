#platform=x86, AMD64, or Intel EM64T
# System authorization information
auth  --useshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr
# Partition clearing information
clearpart --all --initlabel
# Use text mode install
text
# Firewall configuration
firewall --enabled
# Run the Setup Agent on first boot
firstboot --disable
# System keyboard
keyboard us
# System language
lang en_US
# Use network installation
url --url=TEMPLATE::tree
# Network information
network --bootproto=dhcp --device=eth0 --onboot=on
# Reboot after installation
reboot

#Root password
rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.
# SELinux configuration
selinux --disabled
# Do not configure the X Window System
skipx
# System timezone
timezone  America/New_York
# Install OS instead of upgrade
install
# Clear the Master Boot Record
zerombr
# Magically figure out how to partition this thing
%include /tmp/partinfo

%pre
# Determine how many drives we have
set \$(list-harddrives)
let numd=\$#/2
d1=\$1
d2=\$3

cat << EOF >> /tmp/partinfo
part / --fstype ext3 --size=1024 --grow --ondisk=\$d1 --asprimary
part swap --size=1024 --ondisk=\$d1 --asprimary
#EOF

%packages

%post
TEMPLATE::yum_config_stanza
TEMPLATE::kickstart_done

