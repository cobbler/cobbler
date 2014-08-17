import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_Nexenta_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"nexenta-t1-x86_64", "desc":"Nexenta 3 test 1 amd64", "path":"/vagrant/distros/nexenta3_amd64"}
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_nexenta_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_Nexenta_Imports, test_func.__name__, test_func)
   del test_func
