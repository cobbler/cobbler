#!/usr/bin/env python
# $Id: FileRefresh.py,v 1.6 2002/10/01 17:52:03 tavis_rudd Exp $
"""Tests to make sure that the file-update-monitoring code is working properly

THIS TEST MODULE IS JUST A SHELL AT THE MOMENT. Feel like filling it in??

Meta-Data
================================================================================
Author: Tavis Rudd <tavis@damnsimple.com>,
Version: $Revision: 1.6 $
Start Date: 2001/10/01
Last Revision Date: $Date: 2002/10/01 17:52:03 $
"""
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.6 $"[11:-2]


##################################################
## DEPENDENCIES ##

import sys
import types
import os
import os.path


import unittest_local_copy as unittest
from Cheetah.Template import Template

##################################################
## CONSTANTS & GLOBALS ##

try:
    True,False
except NameError:
    True, False = (1==1),(1==0)

##################################################
## TEST DATA FOR USE IN THE TEMPLATES ##

##################################################
## TEST BASE CLASSES

class TemplateTest(unittest.TestCase):
    pass

##################################################
## TEST CASE CLASSES


##################################################
## if run from the command line ##
        
if __name__ == '__main__':
    unittest.main()
