import pytest


class Test_FreeBSD_Imports():
    """
    Tests imports of various distros
    """
    distros = [
        {"name": "freebsd8.2-x86_64", "desc": "FreeBSD 8.2 amd64", "path": "/vagrant/distros/freebsd8.2_amd64"},
        {"name": "freebsd8.3-x86_64", "desc": "FreeBSD 8.3 amd64", "path": "/vagrant/distros/freebsd8.3_amd64"},
        {"name": "freebsd9.0-i386", "desc": "FreeBSD 9.0 i386", "path": "/vagrant/distros/freebsd9.0_i386"},
        {"name": "freebsd9.0-x86_64", "desc": "FreeBSD 9.0 amd64", "path": "/vagrant/distros/freebsd9.0_amd64"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_freebsd_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
