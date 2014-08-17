import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_VMWare_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"vmware_esx_4.0_u1-x86_64", "desc":"VMware ESX 4.0 update1", "path":"/vagrant/distros/vmware_esx_4.0_u1_208167_x86_64"},
 {"name":"vmware_esx_4.0_u2-x86_64", "desc":"VMware ESX 4.0 update2", "path":"/vagrant/distros/vmware_esx_4.0_u2_261974_x86_64"},
 {"name":"vmware_esxi4.1-x86_64", "desc":"VMware ESXi 4.1", "path":"/vagrant/distros/vmware_esxi4.1_348481_x86_64"},
 {"name":"vmware_esxi5.0-x86_64", "desc":"VMware ESXi 5.0", "path":"/vagrant/distros/vmware_esxi5.0_469512_x86_64"},
 {"name":"vmware_esxi5.1-x86_64", "desc":"VMware ESXi 5.1", "path":"/vagrant/distros/vmware_esxi5.1_799733_x86_64"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_vmware_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_VMWare_Imports, test_func.__name__, test_func)
   del test_func
