#
# Sample scripted installation file
# for ESXi 5+
#

vmaccepteula
reboot --noeject
rootpw --iscrypted $default_password_crypted

install --firstdisk --overwritevmfs
clearpart --firstdisk --overwritevmfs

$SNIPPET('network_config')

%pre --interpreter=busybox

$SNIPPET('kickstart_start')
$SNIPPET('pre_install_network_config')

%post --interpreter=busybox

$SNIPPET('kickstart_done')
