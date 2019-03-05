import pytest


class Test_VMWare_Imports:
    """
    Tests imports of various distros
    """

    distros = [
        {"name": "vmware_esx_4.0_u1-x86_64", "desc": "VMware ESX 4.0 update1",
         "path": "/vagrant/distros/vmware_esx_4.0_u1_208167_x86_64"},
        {"name": "vmware_esx_4.0_u2-x86_64", "desc": "VMware ESX 4.0 update2",
         "path": "/vagrant/distros/vmware_esx_4.0_u2_261974_x86_64"},
        {"name": "vmware_esxi4.1-x86_64", "desc": "VMware ESXi 4.1",
         "path": "/vagrant/distros/vmware_esxi4.1_348481_x86_64"},
        {"name": "vmware_esxi5.0-x86_64", "desc": "VMware ESXi 5.0",
         "path": "/vagrant/distros/vmware_esxi5.0_469512_x86_64"},
        {"name": "vmware_esxi5.1-x86_64", "desc": "VMware ESXi 5.1",
         "path": "/vagrant/distros/vmware_esxi5.1_799733_x86_64"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_vmware_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
