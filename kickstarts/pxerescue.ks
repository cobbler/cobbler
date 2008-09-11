# Rescue Boot Template

# Set the language and language support
lang en_US
langsupport en_US

# Set the keyboard
keyboard "us"

# Network kickstart
network --bootproto dhcp

# Rescue method (only NFS/FTP/HTTP currently supported)
#import string
#if string.find($tree,'nfs') == 0
#set parts = string.split($tree,':')
nfs --server=$parts[1][2:] --dir=$parts[2]
#else
url --url=$tree
#end if
