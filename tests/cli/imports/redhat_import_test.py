import pytest

class Test_RedHat_Imports():
    """
    Tests imports of various distros
    """
    distros = [
        {"name": "rhel58-x86_64", "desc": "RHEL 5.8 x86_64", "path": "/vagrant/distros/rhel58_x86_64"},
        {"name": "rhel63-x86_64", "desc": "RHEL 6.3 x86_64", "path": "/vagrant/distros/rhel63_x86_64"},
        {"name": "centos63-x86_64", "desc": "CentOS 6.3 x86_64", "path": "/vagrant/distros/centos63_x86_64"},
        {"name": "sl62-x86_64", "desc": "Scientific Linux 6.2 x86_64", "path": "/vagrant/distros/sl62_x86_64"},
        {"name": "f16-x86_64", "desc": "Fedora 16 x86_64", "path": "/vagrant/distros/f16_x86_64"},
        {"name": "f17-x86_64", "desc": "Fedora 17 x86_64", "path": "/vagrant/distros/f17_x86_64"},
        {"name": "f18-x86_64", "desc": "Fedora 18 x86_64", "path": "/vagrant/distros/f18_x86_64"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_redhat_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
