import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_Ubuntu_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"ubuntu12.04-server-x86_64", "desc":"Ubuntu Precise (12.04) Server amd64", "path":"/vagrant/distros/ubuntu_1204_server_amd64"},
 {"name":"ubuntu12.04.1-server-i386", "desc":"Ubuntu Precise (12.04.1) Server i386", "path":"/vagrant/distros/ubuntu_1204_1_server_i386"},
 {"name":"ubuntu12.10-server-x86_64", "desc":"Ubuntu Quantal (12.10) Server amd64", "path":"/vagrant/distros/ubuntu_1210_server_amd64"},
 {"name":"ubuntu12.10-server-i386", "desc":"Ubuntu Quantal (12.10) Server i386", "path":"/vagrant/distros/ubuntu_1210_server_i386"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_ubuntu_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_Ubuntu_Imports, test_func.__name__, test_func)
   del test_func
