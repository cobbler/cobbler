import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_FreeBSD_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"freebsd8.2-x86_64", "desc":"FreeBSD 8.2 amd64", "path":"/vagrant/distros/freebsd8.2_amd64"},
 {"name":"freebsd8.3-x86_64", "desc":"FreeBSD 8.3 amd64", "path":"/vagrant/distros/freebsd8.3_amd64"},
 {"name":"freebsd9.0-i386", "desc":"FreeBSD 9.0 i386", "path":"/vagrant/distros/freebsd9.0_i386"},
 {"name":"freebsd9.0-x86_64", "desc":"FreeBSD 9.0 amd64", "path":"/vagrant/distros/freebsd9.0_amd64"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_freebsd_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_FreeBSD_Imports, test_func.__name__, test_func)
   del test_func
