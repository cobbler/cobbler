#!/usr/bin/env python
# $Id: Template.py,v 1.16 2006/02/03 21:05:50 tavis_rudd Exp $
"""Tests of the Template class API

Meta-Data
================================================================================
Author: Tavis Rudd <tavis@damnsimple.com>,
Version: $Revision: 1.16 $
Start Date: 2001/10/01
Last Revision Date: $Date: 2006/02/03 21:05:50 $
"""
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.16 $"[11:-2]


##################################################
## DEPENDENCIES ##

import sys
import types
import os
import os.path
import tempfile
import shutil
import unittest_local_copy as unittest
from Cheetah.Template import Template

##################################################
## CONSTANTS & GLOBALS ##

majorVer, minorVer = sys.version_info[0], sys.version_info[1]
versionTuple = (majorVer, minorVer)

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

class ClassMethods_compile(TemplateTest):
    """I am using the same Cheetah source for each test to root out clashes
    caused by the compile caching in Template.compile().
    """
    
    def test_basicUsage(self):
        klass = Template.compile(source='$foo')
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'

    def test_baseclassArg(self):
        klass = Template.compile(source='$foo', baseclass=dict)
        t = klass({'foo':1234})
        assert str(t)=='1234'

        klass2 = Template.compile(source='$foo', baseclass=klass)
        t = klass2({'foo':1234})
        assert str(t)=='1234'

        klass3 = Template.compile(source='#implements dummy\n$bar', baseclass=klass2)
        t = klass3({'foo':1234})
        assert str(t)=='1234'

        klass4 = Template.compile(source='$foo', baseclass='dict')
        t = klass4({'foo':1234})
        assert str(t)=='1234'

    def test_moduleFileCaching(self):
        if versionTuple < (2,3):
            return
        tmpDir = tempfile.mkdtemp()
        try:
            #print tmpDir
            assert os.path.exists(tmpDir)
            klass = Template.compile(source='$foo',
                                     cacheModuleFilesForTracebacks=True,
                                     cacheDirForModuleFiles=tmpDir)
            mod = sys.modules[klass.__module__]
            #print mod.__file__
            assert os.path.exists(mod.__file__)
            assert os.path.dirname(mod.__file__)==tmpDir
        finally:
            shutil.rmtree(tmpDir, True)

    def test_classNameArg(self):
        klass = Template.compile(source='$foo', className='foo123')
        assert klass.__name__=='foo123'
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'

    def test_moduleNameArg(self):
        klass = Template.compile(source='$foo', moduleName='foo99')
        mod = sys.modules['foo99']
        assert klass.__name__=='foo99'
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'


        klass = Template.compile(source='$foo',
                                 moduleName='foo1',
                                 className='foo2')
        mod = sys.modules['foo1']
        assert klass.__name__=='foo2'
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'


    def test_mainMethodNameArg(self):
        klass = Template.compile(source='$foo',
                                 className='foo123',
                                 mainMethodName='testMeth')
        assert klass.__name__=='foo123'
        t = klass(namespaces={'foo':1234})
        #print t.generatedClassCode()
        assert str(t)=='1234'
        assert t.testMeth()=='1234'

        klass = Template.compile(source='$foo',
                                 moduleName='fooXXX',                                 
                                 className='foo123',
                                 mainMethodName='testMeth',
                                 baseclass=dict)
        assert klass.__name__=='foo123'
        t = klass({'foo':1234})
        #print t.generatedClassCode()
        assert str(t)=='1234'
        assert t.testMeth()=='1234'



    def test_moduleGlobalsArg(self):
        klass = Template.compile(source='$foo',
                                 moduleGlobals={'foo':1234})
        t = klass()
        assert str(t)=='1234'

        klass2 = Template.compile(source='$foo', baseclass='Test1',
                                  moduleGlobals={'Test1':dict})
        t = klass2({'foo':1234})
        assert str(t)=='1234'

        klass3 = Template.compile(source='$foo', baseclass='Test1',
                                  moduleGlobals={'Test1':dict, 'foo':1234})
        t = klass3()
        assert str(t)=='1234'


    def test_keepRefToGeneratedCodeArg(self):
        klass = Template.compile(source='$foo',
                                 className='unique58',
                                 cacheCompilationResults=False,
                                 keepRefToGeneratedCode=False)
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'
        assert not t.generatedModuleCode()


        klass2 = Template.compile(source='$foo',
                                 className='unique58',
                                 keepRefToGeneratedCode=True)
        t = klass2(namespaces={'foo':1234})
        assert str(t)=='1234'
        assert t.generatedModuleCode()

        klass3 = Template.compile(source='$foo',
                                 className='unique58',
                                 keepRefToGeneratedCode=False)
        t = klass3(namespaces={'foo':1234})
        assert str(t)=='1234'
        # still there as this class came from the cache
        assert t.generatedModuleCode() 


    def test_compilationCache(self):
        klass = Template.compile(source='$foo',
                                 className='unique111',
                                 cacheCompilationResults=False)
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'
        assert not klass._CHEETAH_isInCompilationCache


        # this time it will place it in the cache
        klass = Template.compile(source='$foo',
                                 className='unique111',
                                 cacheCompilationResults=True)
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'
        assert klass._CHEETAH_isInCompilationCache

        # by default it will be in the cache
        klass = Template.compile(source='$foo',
                                 className='unique999099')
        t = klass(namespaces={'foo':1234})
        assert str(t)=='1234'
        assert klass._CHEETAH_isInCompilationCache


class ClassMethods_subclass(TemplateTest):

    def test_basicUsage(self):
        klass = Template.compile(source='$foo', baseclass=dict)
        t = klass({'foo':1234})
        assert str(t)=='1234'

        klass2 = klass.subclass(source='$foo')
        t = klass2({'foo':1234})
        assert str(t)=='1234'

        klass3 = klass2.subclass(source='#implements dummy\n$bar')
        t = klass3({'foo':1234})
        assert str(t)=='1234'
        

class Preprocessors(TemplateTest):

    def test_basicUsage1(self):
        src='''\
        %set foo = @a
        $(@foo*10)
        @a'''
        src = '\n'.join([ln.strip() for ln in src.splitlines()])
        preprocessors = {'tokens':'@ %',
                         'namespaces':{'a':99}
                         }
        klass = Template.compile(src, preprocessors=preprocessors)
        assert str(klass())=='990\n99'

    def test_normalizePreprocessorArgVariants(self):
        src='%set foo = 12\n%%comment\n$(@foo*10)'

        class Settings1: tokens = '@ %' 
        Settings1 = Settings1()
            
        from Cheetah.Template import TemplatePreprocessor
        settings = Template._normalizePreprocessorSettings(Settings1)
        preprocObj = TemplatePreprocessor(settings)

        def preprocFunc(source, file):
            return '$(12*10)', None

        class TemplateSubclass(Template):
            pass

        compilerSettings = {'cheetahVarStartToken':'@',
                            'directiveStartToken':'%',
                            'commentStartToken':'%%',
                            }
        
        for arg in ['@ %',
                    {'tokens':'@ %'},
                    {'compilerSettings':compilerSettings},
                    {'compilerSettings':compilerSettings,
                     'templateInitArgs':{}},
                    {'tokens':'@ %',
                     'templateAPIClass':TemplateSubclass},
                    Settings1,
                    preprocObj,
                    preprocFunc,                    
                    ]:
            
            klass = Template.compile(src, preprocessors=arg)
            assert str(klass())=='120'


    def test_complexUsage(self):
        src='''\
        %set foo = @a
        %def func1: #def func(arg): $arg("***")
        %% comment
        $(@foo*10)
        @func1
        $func(lambda x:c"--$x--@a")'''
        src = '\n'.join([ln.strip() for ln in src.splitlines()])

        
        for arg in [{'tokens':'@ %', 'namespaces':{'a':99} },
                    {'tokens':'@ %', 'namespaces':{'a':99} },
                    ]:
            klass = Template.compile(src, preprocessors=arg)
            t = klass()
            assert str(t)=='990\n--***--99'



    def test_i18n(self):
        src='''\
        %i18n: This is a $string that needs translation
        %i18n id="foo", domain="root": This is a $string that needs translation
        '''
        src = '\n'.join([ln.strip() for ln in src.splitlines()])
        klass = Template.compile(src, preprocessors='@ %', baseclass=dict)
        t = klass({'string':'bit of text'})
        #print str(t), repr(str(t))
        assert str(t)==('This is a bit of text that needs translation\n'*2)[:-1]


##################################################
## if run from the command line ##
        
if __name__ == '__main__':
    unittest.main()
