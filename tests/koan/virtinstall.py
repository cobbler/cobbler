import unittest

from koan.virtinstall import build_commandline

class KoanVirtInstallTest(unittest.TestCase):
    def testXenPVBasic(self):
        cmd = build_commandline("xen:///",
            name="foo",
            ram=256,
            uuid="ad6611b9-98e4-82c8-827f-051b6b6680d7",
            vcpus=1,
            bridge="br0",
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
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
