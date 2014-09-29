import os
import sys
import unittest

from cobbler import utils
from tests.cli.imports.import_base import CobblerImportTest
from tests.cli.imports.import_base import create_import_func

class Test_RedHat_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   pass

distros = [
 {"name":"rhel58-x86_64", "desc":"RHEL 5.8 x86_64", "path":"/vagrant/distros/rhel58_x86_64"},
 {"name":"rhel63-x86_64", "desc":"RHEL 6.3 x86_64", "path":"/vagrant/distros/rhel63_x86_64"},
 {"name":"centos63-x86_64", "desc":"CentOS 6.3 x86_64", "path":"/vagrant/distros/centos63_x86_64"},
 {"name":"sl62-x86_64", "desc":"Scientific Linux 6.2 x86_64", "path":"/vagrant/distros/sl62_x86_64"},
 {"name":"f16-x86_64", "desc":"Fedora 16 x86_64", "path":"/vagrant/distros/f16_x86_64"},
 {"name":"f17-x86_64", "desc":"Fedora 17 x86_64", "path":"/vagrant/distros/f17_x86_64"},
 {"name":"f18-x86_64", "desc":"Fedora 18 x86_64", "path":"/vagrant/distros/f18_x86_64"},
]

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_redhat_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_RedHat_Imports, test_func.__name__, test_func)
   del test_func
