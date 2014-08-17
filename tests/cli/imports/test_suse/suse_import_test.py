import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_Suse_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"opensuse11.3-i386", "desc":"OpenSuSE 11.3 i586", "path":"/vagrant/distros/opensuse11.3_i586"},
 {"name":"opensuse11.4-x86_64", "desc":"OpenSuSE 11.4 x86_64", "path":"/vagrant/distros/opensuse11.4_x86_64"},
 {"name":"opensuse12.1-x86_64", "desc":"OpenSuSE 12.1 x86_64", "path":"/vagrant/distros/opensuse12.1_x86_64"},
 {"name":"opensuse12.2-i386", "desc":"OpenSuSE 12.2 i586", "path":"/vagrant/distros/opensuse12.2_i586"},
 {"name":"opensuse12.2-x86_64", "desc":"OpenSuSE 12.2 x86_64", "path":"/vagrant/distros/opensuse12.2_x86_64"},
 {"name":"opensuse12.3-i386", "desc":"OpenSuSE 12.3 i586", "path":"/vagrant/distros/opensuse12.3_i586"},
 {"name":"opensuse12.3-x86_64", "desc":"OpenSuSE 12.3 x86_64", "path":"/vagrant/distros/opensuse12.3_x86_64"},
 {"name":"opensuse13.1-i386", "desc":"OpenSuSE 13.1 i586", "path":"/vagrant/distros/opensuse13.1_i586"},
 {"name":"opensuse13.1-x86_64", "desc":"OpenSuSE 13.1 x86_64", "path":"/vagrant/distros/opensuse13.1_x86_64"},
 {"name":"sles11_sp2-i386", "desc":"SLES 11 SP2 i586", "path":"/vagrant/distros/sles11_sp2_i586"},
 {"name":"sles11_sp2-x86_64", "desc":"SLES 11 SP2 x86_64", "path":"/vagrant/distros/sles11_sp2_x86_64"},
 {"name":"sles11_sp2-ppc64", "desc":"SLES 11 SP2 ppc64", "path":"/vagrant/distros/sles11_sp2_ppc64"},
 {"name":"sles11_sp3-i386", "desc":"SLES 11 SP3 i586", "path":"/vagrant/distros/sles11_sp3_i586"},
 {"name":"sles11_sp3-x86_64", "desc":"SLES 11 SP3 x86_64", "path":"/vagrant/distros/sles11_sp3_x86_64"},
 {"name":"sles11_sp3-ppc64", "desc":"SLES 11 SP3 ppc64", "path":"/vagrant/distros/sles11_sp3_ppc64"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_suse_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_Suse_Imports, test_func.__name__, test_func)
   del test_func
