import pytest


class Test_Ubuntu_Imports():
    """
    Tests imports of various distros
    """
    distros = [
        {"name": "ubuntu12.04-server-x86_64", "desc": "Ubuntu Precise (12.04) Server amd64",
         "path": "/vagrant/distros/ubuntu_1204_server_amd64"},
        {"name": "ubuntu12.04.1-server-i386", "desc": "Ubuntu Precise (12.04.1) Server i386",
         "path": "/vagrant/distros/ubuntu_1204_1_server_i386"},
        {"name": "ubuntu12.10-server-x86_64", "desc": "Ubuntu Quantal (12.10) Server amd64",
         "path": "/vagrant/distros/ubuntu_1210_server_amd64"},
        {"name": "ubuntu12.10-server-i386", "desc": "Ubuntu Quantal (12.10) Server i386",
         "path": "/vagrant/distros/ubuntu_1210_server_i386"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_ubuntu_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
