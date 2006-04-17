#!/usr/bin/env python
#
# xen-net-install is a network provisioning tool for xen-instances.
# the expectation is that 'bootconf' has been run on a centralized
# boot server.  see 'man bootconf'.
#
# usage:
#       xen-net-install --profiles=[profile1,profile2,...] [--server=ip]
#   OR  xen-net-install --profiles=AUTODISCOVER [--server=ip]
#
# xen-net-install fetches Xen parameters and files over TFTP and
# does the equivalent of a Xen-net-install.  It may actually *run*
# xen-net-install to perform the actual install, we'll see.
#
# Michael DeHaan <mdehaan@redhat.com>


