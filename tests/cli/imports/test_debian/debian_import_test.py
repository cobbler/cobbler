import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_Debian_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"debian_6.0.5-x86_64", "desc":"Debian Sarge (6.0.5) amd64", "path":"/vagrant/distros/debian_6.0.5_amd64"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_debian_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_Debian_Imports, test_func.__name__, test_func)
   del test_func
