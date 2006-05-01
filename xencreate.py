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

# stolen directly from xend/server/netif.py
def randomMAC():
    """Generate a random MAC address.
    Uses OUI (Organizationally Unique Identifier) 00-16-3E, allocated to
    Xensource, Inc. The OUI list is available at
    http://standards.ieee.org/regauth/oui/oui.txt.
    The remaining 3 fields are random, with the first bit of the first
    random field set 0.
    @return: MAC address string
    """
    mac = [ 0x00, 0x16, 0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def randomUUID():
    """Generate a random UUID.  Copied from xend/uuid.py"""
    return [ random.randint(0, 255) for _ in range(0, 16) ]

def uuidToString(u):
    return "-".join(["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2,
                     "%02x" * 6]) % tuple(u)

def get_disk(disk,size):
    if not os.path.exists(disk):
        # FIXME: should we create the disk here?
        fd = os.open(disk, os.O_WRONLY | os.O_CREAT)
        off = long(size * 1024L * 1024L * 1024L)
        os.lseek(fd, off, 0)
        os.write(fd, '\x00')
        os.close(fd)
    return disk

def get_uuid(uuid):
    if uuid:
       return uuid
    return uuidToString(randomUUID())

def get_mac(mac):
    if mac:
       return mac
    return randomMAC()

def start_hvm_guest(name, ram, disk, mac, uuid, cdrom):
    if os.uname()[4] in ("x86_64"):
        qemu = "/usr/lib64/xen/bin/qemu-dm"
    else:
        qemu = "/usr/lib/xen/bin/qemu-dm"
    if os.environ.has_key("DISPLAY"):
        hasX = True
    else:
        hasX = False

    if stat.S_ISBLK(os.stat(disk)[stat.ST_MODE]):
        type = "phy"
    else:
        type = "file"
        
    cfg = "%s%s" %(XENCONFIGPATH, name)
    f = open(cfg, "w+")
    # FIXME: need to enable vncviewer by default once vncviewer copes with
    # the geometry changes
    cfg_dict =  {'name': name,'ram': ram,'disk': disk, 
                 'mac': mac, 'devmodel': qemu,
                 'hasX': hasX, 'noX': not hasX, 'type': type, 'uuid': uuid }

    buf = """
# Automatically generated xen config file
name = "%(name)s"
builder = "hvm"
memory = "%(ram)s"
uuid = "%(uuid)s"
disk = [ '%(type)s:%(disk)s,ioemu:hda,w' ]
vif = [ 'type=ioemu,bridge=xenbr0,mac=%(mac)s' ]
on_reboot   = 'restart'
on_crash    = 'restart'
kernel = '/usr/lib/xen/boot/hvmloader'
device_model = '%(devmodel)s'
sdl = 0 # use SDL for graphics
vnc = %(hasX)d # use VNC for graphics
vncviewer = 0 # spawn vncviewer by default
nographic = %(noX)d # don't use graphics
serial='pty' # enable serial console
""" % cfg_dict
    f.write(buf)
    f.close()

    if cdrom:
        cdstr = [ "cdrom=%s" %(cdrom,), "boot=d" ]
    else:
        cdstr = []

    print "\n\nStarting guest..."
    
    # this is kind of lame.  we call xm create, then change our
    # guest config file to use a boot loader instead of the passed kernel
    cmd = ["/usr/sbin/xm", "create", "-c"]
    cmd.extend(cdstr)
    cmd.append(cfg)
    print cmd
    child = os.fork()
    if (not child):
        os.execvp(cmd[0], cmd)
        os._exit(1)

    status = -1
    try:
        (pid, status) = os.waitpid(child, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    return True


def get_paravirt_install_image(kernel_fn,initrd_fn):

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
        
def start_paravirt_install(name=None, ram=None, disk=None, mac=None, uuid=None, kernel=None, initrd=None, extra = ""):
    def writeConfig(cfgdict):
        print "!!!DICT!!! cfgdict['name'] is %s" % cfgdict['name']
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
    src="local"  
     # FIXME: I don't think "method=%(src)s" in the kernel 
     # cmdline is actually read by anything, but I could be wrong.
    cfgdict = {'name': name, 'ram': ram, 'ramkb': int(ram) * 1024, 'disk': disk, 'mac': mac, 'disktype': type, 'uuid': uuid, 'kernel': kfn, 'initrd': ifn, 'src': src, 'extra': extra }      

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

    #conn = libvirt.openReadOnly(None)
    conn = libvirt.open(None)
    if conn == None:
        raise "Unable to connect to hypervisor"

    print "\n\nStarting install..."
    print "\n\n%s\n\n" % cfgxml

    dom = conn.createLinux(cfgxml, 0)
    if dom == None:
        raise "Unable to create domain for guest"
        sys.exit(2)

    # *sigh*  would be nice to have a python version of xmconsole I guess...
    # and probably not much work at all to throw together, but this will
    # do for now
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

    print "!!!DEBUG!!! writing config"
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
    

def get_cpu_flags():
    f = open("/proc/cpuinfo")
    lines = f.readlines()
    f.close()
    for line in lines:
        if not line.startswith("flags"):
            continue
        # get the actual flags
        flags = line[:-1].split(":", 1)[1]
        # and split them
        flst = flags.split(" ")
        return flst
    return []

def is_hvm_capable():
    flags = get_cpu_flags()
    if "vmx" in flags:
        return True
    if "svm" in flags:
        return True
    return False

OLD_ENTRY = """

    hvm = False 
    name = get_name(options)
    ram = get_ram(options)
    disk = get_disk(options)
    mac = get_mac(options)
    uuid = get_uuid(options)

    if is_hvm_capable():
        hvm = get_full_virt(options)

    if not hvm:
        src = get_paravirt_install(options)
        start_paravirt_install(name, ram, disk, mac, uuid, src, options.extra)
    else:
        if get_virt_cdboot(options):
            cdrom = get_virt_cdrom(options)
        else:
            cdrom = None
        start_hvm_guest(name, ram, disk, mac, uuid, cdrom)

"""
