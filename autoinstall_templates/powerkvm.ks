# kickstart template for PowerKVM 2.1 and later

# Root password
rootpw --iscrypted $default_password_crypted
# System timezone
timezone  America/Chicago
# Allow anaconda to partition the system as needed
partition / --ondisk=/dev/sda
# network specification is also supported, but if we specify the network
# device on the command-line, we can skip it

%pre
$SNIPPET('log_ks_pre')
$SNIPPET('autoinstall_start')
%end

%post
$SNIPPET('log_ks_post')
# Start yum configuration
$yum_config_stanza
# End yum configuration
$SNIPPET('post_install_kernel_options')
$SNIPPET('post_install_network_config')
# Start final steps
$SNIPPET('autoinstall_done')
# End final steps
%end
