import pytest

class Test_Debian_Imports():
    """
    Tests imports of various distros
    """

    distros = [
        {"name": "debian_6.0.5-x86_64", "desc": "Debian Sarge (6.0.5) amd64",
         "path": "/vagrant/distros/debian_6.0.5_amd64"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_debian_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
