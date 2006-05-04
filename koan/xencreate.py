#!/usr/bin/python
#
# Modification of xenguest-install to make it usable by other apps
#
# Copyright 2005-2006  Red Hat, Inc.
# Jeremy Katz <katzj@redhat.com>
# Option handling added by Andrew Puch <apuch@redhat.com>
# Simplified for use as library by koan, Michael DeHaan <mdehaan@redhat.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os, sys, time, stat
import subprocess
import tempfile
import urlgrabber.grabber as grabber
import random
from optparse import OptionParser

import libvirt

XENCONFIGPATH="/etc/xen/"

def randomMAC():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-16-3E, allocated to
    Xensource, Inc.  Last 3 fields are random.
    return: MAC address string
    """
    mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def randomUUID():
    """
    Generate a random UUID.  Copied from xend/uuid.py
    """
    return [ random.randint(0, 255) for _ in range(0, 16) ]

def uuidToString(u):
    """
    return uuid as a string
    """
    return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
                     "%02x" * 6]) % tuple(u)

def get_disk(disk,size):
    """
    Create a disk image if path does not exist.
    """
    if not os.path.exists(disk):
        # FIXME: should we create the disk here?
        fd = os.open(disk, os.O_WRONLY | os.O_CREAT)
        off = long(size * 1024L * 1024L * 1024L)
        os.lseek(fd, off, 0)
        os.write(fd, '\x00')
        os.close(fd)
    return disk

def get_uuid(uuid):
    """
    return the passed-in uuid, or a random one if it's not set.
    """
    if uuid:
       return uuid
    return uuidToString(randomUUID())

def get_mac(mac):
    """
    return the passed-in MAC, or a random one if it's not set.
    """
    if mac:
       return mac
    return randomMAC()

def get_paravirt_install_image(kernel_fn,initrd_fn):
    """
    Return a tuple of kernel_filename, intrd_filename
    where the filenames are copies of the kernel and initrd.
    This must be done because Xen deletes the kernel/initrd pairs
    that are originally passed in.
    """
    try:
        kernel = open(kernel_fn,"r")
        initrd = open(initrd_fn,"r")
    except IOError:
        print >> sys.stderr, "Invalid kernel or initrd location"
        sys.exit(2)

    (kfd, kfn) = tempfile.mkstemp(prefix="vmlinuz.", dir="/var/lib/xen")
    os.write(kfd, kernel.read())
    os.close(kfd)
    kernel.close()

    (ifd, ifn) = tempfile.mkstemp(prefix="initrd.img.", dir="/var/lib/xen")
    os.write(ifd, initrd.read())
    os.close(ifd)
    initrd.close()

    return (kfn, ifn)

def start_paravirt_install(name=None, ram=None, disk=None, mac=None,
                           uuid=None, kernel=None, initrd=None, extra=None):
    def writeConfig(cfgdict):
        cfg = "%s%s" %(XENCONFIGPATH, cfgdict['name'])
        f = open(cfg, "w+")
        buf = """
# Automatically generated xen config file
name = "%(name)s"
memory = "%(ram)s"
disk = [ '%(disktype)s:%(disk)s,xvda,w' ]
vif = [ 'mac=%(mac)s' ]
uuid = "%(uuid)s"
bootloader="/usr/bin/pygrub"
on_reboot   = 'destroy'
on_crash    = 'destroy'
""" % cfgdict
        f.write(buf)
        f.close()

    (kfn, ifn) = get_paravirt_install_image(kernel, initrd)

    if stat.S_ISBLK(os.stat(disk)[stat.ST_MODE]):
        type = "phy"
    else:
        type = "file"
    cfgdict = {
       'name': name,
       'ram': ram,
       'ramkb': int(ram) * 1024,
       'disk': disk,
       'mac': mac,
       'disktype': type,
       'uuid': uuid,
       'kernel': kfn,
       'initrd': ifn,
       'extra': extra
    }

    cfgxml = """
<domain type='xen'>
  <name>%(name)s</name>
  <os>
    <type>linux</type>
    <kernel>%(kernel)s</kernel>
    <initrd>%(initrd)s</initrd>
    <root>/dev/xvd</root>
    <cmdline>ro %(extra)s</cmdline>
  </os>
  <memory>%(ramkb)s</memory>
  <vcpu>1</vcpu>
  <uuid>%(uuid)s</uuid>
  <on_reboot>restart</on_reboot>
  <on_poweroff>destroy</on_poweroff>
  <on_crash>destroy</on_crash>
  <devices>
    <disk type='file'>
      <source file='%(disk)s'/>
      <target dev='xvda'/>
    </disk>
    <interface type='bridge'>
      <source bridge='xenbr0'/>
      <mac address='%(mac)s'/>
      <script path='/etc/xen/scripts/vif-bridge'/>
    </interface>
  </devices>
</domain>
""" % cfgdict

    conn = libvirt.open(None)
    if conn == None:
        raise "Unable to connect to hypervisor"

    print "\n\nStarting install..."
    print cfgxml

    dom = conn.createLinux(cfgxml, 0)
    if dom == None:
        raise "Unable to create domain for guest"
        sys.exit(2)

    cmd = ["/usr/sbin/xm", "console", "%s" %(dom.ID(),)]
    child = os.fork()
    if (not child):
        os.execvp(cmd[0], cmd)
        os._exit(1)

    time.sleep(5)
    os.unlink(kfn)
    os.unlink(ifn)

    # FIXME: if the domain doesn't exist now, it almost certainly crashed.
    # it'd be nice to know that for certain...
    try:
        d = conn.lookupByID(dom.ID())
    except libvirt.libvirtError:
        raise "It appears the installation has crashed"
        sys.exit(3)

    writeConfig(cfgdict)

    status = -1
    try:
        (pid, status) = os.waitpid(child, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    # ensure there's time for the domain to finish destroying if the
    # install has finished or the guest crashed
    time.sleep(1)
    try:
        d = conn.lookupByID(dom.ID())
    except libvirt.libvirtError:
        print "Reconnect with xm create -c %s" % (name)
    else:
        print "Reconnect with xm console %s" % (name)


