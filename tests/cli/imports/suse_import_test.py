import pytest


class Test_Suse_Imports():
    """
    Tests imports of various distros
    """
    distros = [
        {"name": "opensuse11.3-i386", "desc": "OpenSuSE 11.3 i586", "path": "/vagrant/distros/opensuse11.3_i586"},
        {"name": "opensuse11.4-x86_64", "desc": "OpenSuSE 11.4 x86_64", "path": "/vagrant/distros/opensuse11.4_x86_64"},
        {"name": "opensuse12.1-x86_64", "desc": "OpenSuSE 12.1 x86_64", "path": "/vagrant/distros/opensuse12.1_x86_64"},
        {"name": "opensuse12.2-i386", "desc": "OpenSuSE 12.2 i586", "path": "/vagrant/distros/opensuse12.2_i586"},
        {"name": "opensuse12.2-x86_64", "desc": "OpenSuSE 12.2 x86_64", "path": "/vagrant/distros/opensuse12.2_x86_64"},
        {"name": "opensuse12.3-i386", "desc": "OpenSuSE 12.3 i586", "path": "/vagrant/distros/opensuse12.3_i586"},
        {"name": "opensuse12.3-x86_64", "desc": "OpenSuSE 12.3 x86_64", "path": "/vagrant/distros/opensuse12.3_x86_64"},
        {"name": "opensuse13.1-i386", "desc": "OpenSuSE 13.1 i586", "path": "/vagrant/distros/opensuse13.1_i586"},
        {"name": "opensuse13.1-x86_64", "desc": "OpenSuSE 13.1 x86_64", "path": "/vagrant/distros/opensuse13.1_x86_64"},
        {"name": "sles11_sp2-i386", "desc": "SLES 11 SP2 i586", "path": "/vagrant/distros/sles11_sp2_i586"},
        {"name": "sles11_sp2-x86_64", "desc": "SLES 11 SP2 x86_64", "path": "/vagrant/distros/sles11_sp2_x86_64"},
        {"name": "sles11_sp2-ppc64", "desc": "SLES 11 SP2 ppc64", "path": "/vagrant/distros/sles11_sp2_ppc64"},
        {"name": "sles11_sp3-i386", "desc": "SLES 11 SP3 i586", "path": "/vagrant/distros/sles11_sp3_i586"},
        {"name": "sles11_sp3-x86_64", "desc": "SLES 11 SP3 x86_64", "path": "/vagrant/distros/sles11_sp3_x86_64"},
        {"name": "sles11_sp3-ppc64", "desc": "SLES 11 SP3 ppc64", "path": "/vagrant/distros/sles11_sp3_ppc64"},
    ]

    @pytest.mark.skip(reason="Not fixed!")
    @pytest.mark.parametrize("name, desc, path", distros)
    def test_suse_import(self, name, desc, path, import_distro, report_distro, report_profile, remove_distro):
        (data, rc) = import_distro(name, path)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
        (data, rc) = report_profile(name)
        assert rc == 0
        (data, rc) = remove_distro(name)
        assert rc == 0
