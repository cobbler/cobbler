# sample Kickstart for ESXi

install url $tree

rootpw --iscrypted $default_password_crypted

accepteula
reboot

autopart --firstdisk --overwritevmfs
 
$SNIPPET('network_config_esxi')

%pre --unsupported --interpreter=busybox
$SNIPPET('autoinstall_start')

%post --unsupported --interpreter=busybox
$SNIPPET('autoinstall_done')
