import os
import sys
import unittest

from cobbler import utils

class CobblerImportTest(unittest.TestCase):
   imported_distros = []
   def setUp(self):
      """
      Set up, mounts NFS share
      """
   def tearDown(self):
      """
      Cleanup here
      """
      for d in self.imported_distros:
         try:
             (data,rc) = utils.subprocess_sp(None,["cobbler","distro","remove","--recursive","--name=%s" % d],shell=False)
         except:
             print "Failed to remove distro '%s' during cleanup" % d

def create_import_func(data):
   name = data["name"]
   desc = data["desc"]
   path = data["path"]
   def do_import(self):
      print "doing import, name=%s, desc=%s, path=%s" % (name,desc,path)
      (data,rc) = utils.subprocess_sp(None,["cobbler","import","--name=test-%s" % name,"--path=%s" % path],shell=False)
      print data
      self.assertEqual(rc,0)
      # TODO: scan output of import to build list of imported distros/profiles
      #       and compare to expected list. Then use that list to run reports 
      #       and for later cleanup
      (data,rc) = utils.subprocess_sp(None,["cobbler","distro","report","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","profile","report","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","distro","remove","--recursive","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
   return do_import

