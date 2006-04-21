#!/usr/bin/python
#
# Quick and dirty script to set up a Xen guest and kick off an install
#
# Copyright 2005-2006  Red Hat, Inc.
# Jeremy Katz <katzj@redhat.com>
# Option handling added by Andrew Puch <apuch@redhat.com>
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
import traceback
from optparse import OptionParser

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

def yes_or_no(s):
    s = s.lower()
    if s in ("y", "yes", "1", "true", "t"):
        return True
    elif s in ("n", "no", "0", "false", "f"):
        return False
    raise ValueError, "A yes or no response is required" 
    

def get_name(options):
    name = options.name
    while not name:
    	print "What is the name of your virtual machine? ",
    	name = sys.stdin.readline().strip()
    return name

def get_ram(options):
    ram = options.memory
    while not ram or ram < 256:
        if ram and ram < 256:
            print "ERROR: Installs currently require 256 megs of RAM."
            print ""
    	print "How much RAM should be allocated (in megabytes)? ",
    	ram = sys.stdin.readline().strip()
    	ram = int(ram)
    return ram

def get_disk_size(options):
    size = options.disksize
    while not size:
        print "How large would you like the disk to be (in gigabytes)? ",
        disksize = sys.stdin.readline().strip()
        size = float(disksize)
    return size

def get_disk(options):
    disk = options.diskfile
    while not disk:
    	print "What would you like to use as the disk (path)? ",
    	disk = sys.stdin.readline().strip()

    if not os.path.exists(disk):
        size = get_disk_size(options)
        # FIXME: should we create the disk here?
        fd = os.open(disk, os.O_WRONLY | os.O_CREAT)
        off = long(size * 1024L * 1024L * 1024L)
        os.lseek(fd, off, 0)
        os.write(fd, '\x00')
        os.close(fd)

    return disk

def get_mac(options):
    if options.mac:
        return options.mac
    return randomMAC()

def get_full_virt(options):
    if options.fullvirt is not None:
        return options.fullvirt
    while 1:
        print "Would you like a fully virtualized guest (yes or no)?  This will allow you "
        print "  to run unmodified operating systems."
        res = sys.stdin.readline().strip()
        try:
            return yes_or_no(res)
        except ValueError, e:
            print e

def get_virt_cdboot(options):
    if options.cdrom:
        return True
    while 1:
        print "Would you like to boot the guest from a virtual CD?"
        res = sys.stdin.readline().strip()    
        try:
            return yes_or_no(res)
        except ValueError, e:
            print e

def get_virt_cdrom(options):
    cdrom = options.cdrom
    while not cdrom:
        print "What would you like to use for the virtual CD image?"
        cdrom = sys.stdin.readline().strip()
    return cdrom

def start_hvm_guest(name, ram, disk, mac, cdrom):
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
    buf = """# Automatically generated xen config file
name = "%(name)s"
builder = "hvm"
memory = "%(ram)s"
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
""" % {'name': name, 'ram': ram, 'disk': disk, 'mac': mac, 'devmodel': qemu,
       'hasX': hasX, 'noX': not hasX, 'type': type }
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

    print ("XM command exited. Your guest can be restarted by running\n" 
           "'xm create -c %s'.  Otherwise, you can reconnect to the console\n"
           "with vncviewer or 'xm console'" %(name,))

def get_paravirt_install_image(src):
    if src.startswith("http://") or src.startswith("ftp://"):
    	try:
            kernel = grabber.urlopen("%s/images/xen/vmlinuz" %(src,))
            initrd = grabber.urlopen("%s/images/xen/initrd.img" %(src,))
	except IOError:
            print >> sys.stderr, "Invalid URL location given"
            sys.exit(2); 
    elif src.startswith("nfs:"):
        nfsmntdir = tempfile.mkdtemp(prefix="xennfs.", dir="/var/lib/xen")
        cmd = ["mount", "-o", "ro", src[4:], nfsmntdir]
        ret = subprocess.call(cmd)
        if ret != 0:
            print >> sys.stderr, "Mounting nfs share failed!"
            sys.exit(1)
	try:
            kernel = open("%s/images/xen/vmlinuz" %(nfsmntdir,), "r")
            initrd = open("%s/images/xen/initrd.img" %(nfsmntdir,), "r")
        except IOError:
            print >> sys.stderr, "Invalid NFS location given"
            sys.exit(2)
    elif src.startswith("file://"):
        try:
            # takes *two* files as in "--location=file://initrd.img,vmlinuz"
            initrd, kernel = map(lambda(f): open(f,"r"), src[7:].split(","))    
        except:
            traceback.print_exc()
            print >> sys.stderr, "Invalid local files given"
            sys.exit(2)   

    (kfd, kfn) = tempfile.mkstemp(prefix="vmlinuz.", dir="/var/lib/xen")
    os.write(kfd, kernel.read())
    os.close(kfd)
    kernel.close()

    (ifd, ifn) = tempfile.mkstemp(prefix="initrd.img.", dir="/var/lib/xen")
    os.write(ifd, initrd.read())
    os.close(ifd)
    initrd.close()

    # and unmount
    if src.startswith("nfs"):
        cmd = ["umount", nfsmntdir]
        ret = subprocess.call(cmd)
	os.rmdir(nfsmntdir)

    return (kfn, ifn)

def get_paravirt_install(options):
    src = options.location
    while True:
        if src and (src.startswith("http://") or src.startswith("ftp://")):
            return src
        elif src and src.startswith("nfs:"):
            return src
        elif src and src.startswith("file://"):
            return src
        if src is not None: print "Invalid source specified.  Please specify an NFS, HTTP, or FTP install source"
    	print "What is the install location? ",
    	src = sys.stdin.readline().strip()

def start_paravirt_install(name, ram, disk, mac, src, extra = ""):
    (kfn, ifn) = get_paravirt_install_image(src)

    if stat.S_ISBLK(os.stat(disk)[stat.ST_MODE]):
        type = "phy"
    else:
        type = "file"
    
    cfg = "%s%s" %(XENCONFIGPATH, name)
    f = open(cfg, "w+")
    buf = """# Automatically generated xen config file
name = "%(name)s"
memory = "%(ram)s"
disk = [ '%(type)s:%(disk)s,xvda,w' ]
vif = [ 'mac=%(mac)s' ]
#bootloader="/usr/bin/pygrub"

on_reboot   = 'destroy'
on_crash    = 'destroy'
""" % {'name': name, 'ram': ram, 'disk': disk, 'mac': mac, 'type': type }
    f.write(buf)
    f.close()

    print "\n\nStarting install..."

    # this is kind of lame.  we call xm create, then change our
    # guest config file to use a boot loader instead of the passed kernel
    cmd = ["/usr/sbin/xm", "create", "-c", "kernel=%s" %(kfn,),
           "ramdisk=%s" %(ifn,),
           "extra=method=%s %s" %(src,extra),
           cfg]
    child = os.fork()
    if (not child):
        os.execvp(cmd[0], cmd)
        os._exit(1)

    time.sleep(5)
    f = open(cfg, "r")
    buf = f.read()
    f.close()
    os.unlink(kfn)
    os.unlink(ifn)
    
    buf = buf.replace("#bootloader", "bootloader")
    buf = buf.replace("'destroy'", "'restart'")

    f = open(cfg, "w+")
    f.write(buf)
    f.close()

    status = -1
    try:
        (pid, status) = os.waitpid(child, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    print ("If your install has exited, you can restart your guest by running\n"
           "'xm create -c %s'.  Otherwise, you can reconnect to the console\n"
           "by running 'xm console %s'" %(name, name)) 
    

def parse_args():
    parser = OptionParser()
    parser.add_option("-n", "--name", type="string", dest="name",
                      help="Name of the guest instance")
    parser.add_option("-f", "--file", type="string", dest="diskfile",
                      help="File to use as the disk image")
    parser.add_option("-s", "--file-size", type="float", dest="disksize",
                      help="Size of the disk image (if it doesn't exist) in gigabytes")
    parser.add_option("-r", "--ram", type="int", dest="memory",
                      help="Memory to allocate for guest instance in megabytes")
    parser.add_option("-m", "--mac", type="string", dest="mac",
                      help="Fixed MAC address for the guest; if none is given a random address will be used")
    
    # vmx/svm options
    if is_hvm_capable():
        parser.add_option("-v", "--hvm", action="store_true", dest="fullvirt",
                          help="This guest should be a fully virtualized guest")
        parser.add_option("-c", "--cdrom", type="string", dest="cdrom",
                          help="File to use a virtual CD-ROM device for fully virtualized guests")

    # paravirt options
    parser.add_option("-p", "--paravirt", action="store_false", dest="fullvirt",
                      help="This guest should be a paravirtualized guest")
    parser.add_option("-l", "--location", type="string", dest="location",
                      help="Installation source for paravirtualized guest (eg, nfs:host:/path, http://host/path, ftp://host/path)")
    parser.add_option("-x", "--extra-args", type="string",
                      dest="extra", default="",
                      help="Additional arguments to pass to the installer with paravirt guests")


    (options,args) = parser.parse_args()
    return options

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

def main():
    options = parse_args()

    hvm = False 
    name = get_name(options)
    ram = get_ram(options)
    disk = get_disk(options)
    mac = get_mac(options)

    if is_hvm_capable():
        hvm = get_full_virt(options)

    if not hvm:
        src = get_paravirt_install(options)
        start_paravirt_install(name, ram, disk, mac, src, options.extra)
    else:
        if get_virt_cdboot(options):
            cdrom = get_virt_cdrom(options)
        else:
            cdrom = None
        start_hvm_guest(name, ram, disk, mac, cdrom)

if __name__ == "__main__":
    main()
