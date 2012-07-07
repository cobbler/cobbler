import unittest
import koan

from koan.virtinstall import build_commandline

def setup():
    try:
        from virtinst import version as vi_version
        koan.virtinstall.virtinst_version = vi_version.__version__.split('.')
    except:
        koan.virtinstall.virtinst_version = 6

class KoanVirtInstallTest(unittest.TestCase):
    def testXenPVBasic(self):
        cmd = build_commandline("xen:///",
            name="foo",
            ram=256,
            uuid="ad6611b9-98e4-82c8-827f-051b6b6680d7",
            vcpus=1,
            bridge="br0",
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            virt_type="xenpv",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data={
                "kernel_local" : "kernel",
                "initrd_local" : "initrd",
            },
            extra="ks=http://example.com/ks.ks")

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --connect xen:/// --name foo --ram 256 --vcpus 1 "
             "--uuid ad6611b9-98e4-82c8-827f-051b6b6680d7 --vnc --paravirt "
             "--boot kernel=kernel,initrd=initrd,kernel_args=ks=http://example.com/ks.ks "
             "--disk path=/tmp/foo1.img,size=8 --disk path=/dev/foo1 "
             "--network bridge=br0 "
             "--wait 0 --noautoconsole"))

    def testXenFVBasic(self):
        cmd = build_commandline("xen:///",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/dev/foo1", 0)],
            fullvirt=True,
            arch="x86_64",
            bridge="br0,br1",
            virt_type="xenfv",
            profile_data = {
                "breed" : "redhat",
                "os_version" : "fedora14",
                "interfaces" : {
                    "eth0": {
                        "interface_type": "na",
                        "mac_address": "11:22:33:44:55:66",
                    }, "eth1": {
                        "interface_type": "na",
                        "mac_address": "11:22:33:33:22:11",
                    }
                }
            })

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --connect xen:/// --name foo --ram 256 --vcpus 1 "
             "--vnc --hvm --pxe --arch x86_64 "
             "--os-variant fedora14 --disk path=/dev/foo1 "
             "--network bridge=br0,mac=11:22:33:44:55:66 "
             "--network bridge=br1,mac=11:22:33:33:22:11 "
             "--wait 0 --noautoconsole"))

    def testQemuCDROM(self):
        cmd = build_commandline("qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=True,
            virt_type="qemu",
            bridge="br0",
            profile_data = {
                "breed" : "windows",
                "file" : "/some/cdrom/path.iso",
            })

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --connect qemu:///system --name foo --ram 256 "
             "--vcpus 1 --vnc --virt-type qemu --hvm --cdrom /some/cdrom/path.iso "
             "--os-type windows --disk path=/tmp/foo1.img,size=8 "
             "--disk path=/dev/foo1 --network bridge=br0 "
             "--wait 0 --noautoconsole")
        )

    def testQemuURL(self):
        cmd = build_commandline("qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=True,
            arch="i686",
            bridge="br0",
            virt_type="qemu",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data = {
                "breed" : "ubuntu",
                "os_version" : "natty",
                "install_tree" : "http://example.com/some/install/tree",
            },
            extra="ks=http://example.com/ks.ks text kssendmac")

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --connect qemu:///system --name foo --ram 256 "
             "--vcpus 1 --vnc --virt-type qemu --hvm "
             "--extra-args=ks=http://example.com/ks.ks text kssendmac "
             "--location http://example.com/some/install/tree/ --arch i686 "
             "--os-variant ubuntunatty "
             "--disk path=/tmp/foo1.img,size=8,bus=virtio "
             "--disk path=/dev/foo1,bus=virtio "
             "--network bridge=br0,model=virtio --wait 0 --noautoconsole")
        )

    def testKvmURL(self):
        cmd = build_commandline("qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=None,
            arch="i686",
            bridge="br0",
            virt_type="kvm",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data = {
                "breed" : "ubuntu",
                "os_version" : "natty",
                "install_tree" : "http://example.com/some/install/tree",
            },
            extra="ks=http://example.com/ks.ks text kssendmac")

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --connect qemu:///system --name foo --ram 256 "
             "--vcpus 1 --vnc --virt-type kvm "
             "--extra-args=ks=http://example.com/ks.ks text kssendmac "
             "--location http://example.com/some/install/tree/ --arch i686 "
             "--os-variant ubuntunatty "
             "--disk path=/tmp/foo1.img,size=8,bus=virtio "
             "--disk path=/dev/foo1,bus=virtio "
             "--network bridge=br0,model=virtio --wait 0 --noautoconsole")
        )

    def testImage(self):
        cmd = build_commandline("import",
            name="foo",
            ram=256,
            vcpus=1,
            fullvirt=True,
            bridge="br0,br2",
            disks=[],
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data = {
                "file" : "/some/install/image.img",
                "network_count" : 2,
            })

        cmd = " ".join(cmd)
        self.assertEquals(cmd,
            ("virt-install --name foo --ram 256 --vcpus 1 --vnc --import "
             "--disk path=/some/install/image.img --network bridge=br0 "
             "--network bridge=br2 --wait 0 --noautoconsole")
        )
