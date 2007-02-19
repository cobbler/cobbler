#!/usr/bin/env python

"""Provides a mixin/base class for collecting and managing application settings

Meta-Data
==========
Author: Tavis Rudd <tavis@damnsimple.com>
Version: $Revision: 1.28 $
Start Date: 2001/05/30
Last Revision Date: $Date: 2006/01/29 07:19:12 $
"""

# $Id: SettingsManager.py,v 1.28 2006/01/29 07:19:12 tavis_rudd Exp $
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.28 $"[11:-2]


##################################################
## DEPENDENCIES ##

import sys
import os.path
import copy as copyModule
from ConfigParser import ConfigParser 
import re
from tokenize import Intnumber, Floatnumber, Number
from types import *
import types
import new
import tempfile
import imp
import time

from StringIO import StringIO # not cStringIO because of unicode support

import imp                 # used by SettingsManager.updateSettingsFromPySrcFile()

try:
    import threading
    from threading import Lock  # used for thread lock on sys.path manipulations
except:
    ## provide a dummy for non-threading Python systems
    class Lock:
        def acquire(self):
            pass
        def release(self):
            pass

class BaseErrorClass: pass

##################################################
## CONSTANTS & GLOBALS ##

try:
    True,False
except NameError:
    True, False = (1==1),(1==0)

numberRE = re.compile(Number)
complexNumberRE = re.compile('[\(]*' +Number + r'[ \t]*\+[ \t]*' + Number + '[\)]*')

convertableToStrTypes = (StringType, IntType, FloatType,
                         LongType, ComplexType, NoneType,
                         UnicodeType)

##################################################
## FUNCTIONS ##

def mergeNestedDictionaries(dict1, dict2, copy=False, deepcopy=False):
    
    """Recursively merge the values of dict2 into dict1.

    This little function is very handy for selectively overriding settings in a
    settings dictionary that has a nested structure.
    """

    if copy:
        dict1 = copyModule.copy(dict1)
    elif deepcopy:
        dict1 = copyModule.deepcopy(dict1)
        
    for key,val in dict2.items():
        if dict1.has_key(key) and type(val) == types.DictType and \
           type(dict1[key]) == types.DictType:
            
            dict1[key] = mergeNestedDictionaries(dict1[key], val)
        else:
            dict1[key] = val
    return dict1
    
def stringIsNumber(S):
    
    """Return True if theString represents a Python number, False otherwise.
    This also works for complex numbers and numbers with +/- in front."""

    S = S.strip()
    
    if S[0] in '-+' and len(S) > 1:
        S = S[1:].strip()
    
    match = complexNumberRE.match(S)
    if not match:
        match = numberRE.match(S)
    if not match or (match.end() != len(S)):
        return False
    else:
        return True
        
def convStringToNum(theString):
    
    """Convert a string representation of a Python number to the Python version"""
    
    if not stringIsNumber(theString):
        raise Error(theString + ' cannot be converted to a Python number')
    return eval(theString, {}, {})



######

ident = r'[_a-zA-Z][_a-zA-Z0-9]*'
firstChunk = r'^(?P<indent>\s*)(?P<class>[_a-zA-Z][_a-zA-Z0-9]*)'
customClassRe = re.compile(firstChunk + r'\s*:')
baseClasses = r'(?P<bases>\(\s*([_a-zA-Z][_a-zA-Z0-9]*\s*(,\s*[_a-zA-Z][_a-zA-Z0-9]*\s*)*)\))'
customClassWithBasesRe = re.compile(firstChunk + baseClasses + '\s*:')

def translateClassBasedConfigSyntax(src):
    
    """Compiles a config file in the custom class-based SettingsContainer syntax
    to Vanilla Python
    
    # WebKit.config
    Applications:
        MyApp:
            Dirs:
                ROOT = '/home/www/Home'
                Products = '/home/www/Products'
    becomes:
    # WebKit.config
    from Cheetah.SettingsManager import SettingsContainer
    class Applications(SettingsContainer):
        class MyApp(SettingsContainer):
            class Dirs(SettingsContainer):
                ROOT = '/home/www/Home'
                Products = '/home/www/Products'
    """
    
    outputLines = []
    for line in src.splitlines():
        if customClassRe.match(line) and \
           line.strip().split(':')[0] not in ('else','try', 'except', 'finally'):
            
            line = customClassRe.sub(
                r'\g<indent>class \g<class>(SettingsContainer):', line)
            
        elif customClassWithBasesRe.match(line) and not line.strip().startswith('except'):
            line = customClassWithBasesRe.sub(
                 r'\g<indent>class \g<class>\g<bases>:', line)
            
        outputLines.append(line)

    ## prepend this to the first line to make sure that tracebacks report the right line nums
    if outputLines[0].find('class ') == -1:
        initLine = 'from Cheetah.SettingsManager import SettingsContainer; True, False = 1, 0; '
    else:
        initLine = 'from Cheetah.SettingsManager import SettingsContainer; True, False = 1, 0\n'
    return initLine + '\n'.join(outputLines) + '\n'


##################################################
## CLASSES ##

class Error(BaseErrorClass):
    pass

class NoDefault:
    pass

class ConfigParserCaseSensitive(ConfigParser):
    
    """A case sensitive version of the standard Python ConfigParser."""
    
    def optionxform(self, optionstr):
        
        """Don't change the case as is done in the default implemenation."""
        
        return optionstr

class SettingsContainer:
    """An abstract base class for 'classes' that are used to house settings."""
    pass


class _SettingsCollector:

    """An abstract base class that provides the methods SettingsManager uses to
    collect settings from config files and SettingsContainers.

    This class only collects settings it doesn't modify the _settings dictionary
    of SettingsManager instances in any way.

    SettingsCollector is designed to:
    - be able to read settings from Python src files (or strings) so that
      complex Python objects can be stored in the application's settings
      dictionary.  For example, you might want to store references to various
      classes that are used by the application and plugins to the application
      might want to substitute one class for another.
    - be able to read/write .ini style config files (or strings)
    - allow sections in .ini config files to be extended by settings in Python
      src files
    - allow python literals to be used values in .ini config files
    - maintain the case of setting names, unlike the ConfigParser module
    
    """

    _sysPathLock = Lock()   # used by the updateSettingsFromPySrcFile() method
    _ConfigParserClass = ConfigParserCaseSensitive 
    

    def __init__(self):
        pass

    def normalizePath(self, path):
        
        """A hook for any neccessary path manipulations.

        For example, when this is used with WebKit servlets all relative paths
        must be converted so they are relative to the servlet's directory rather
        than relative to the program's current working dir.

        The default implementation just normalizes the path for the current
        operating system."""
        
        return os.path.normpath(path.replace("\\",'/'))


    def readSettingsFromContainer(self, container, ignoreUnderscored=True):
        
        """Returns all settings from a SettingsContainer or Python
        module.

        This method is recursive.
        """
        
        S = {}
        if type(container) == ModuleType:
            attrs = vars(container)
        else:
            attrs = self._getAllAttrsFromContainer(container)
    
        for k, v in attrs.items():
            if (ignoreUnderscored and k.startswith('_')) or v is SettingsContainer:
                continue
            if self._isContainer(v):
                S[k] = self.readSettingsFromContainer(v)
            else:
                S[k] = v
        return S

    # provide an alias
    readSettingsFromModule = readSettingsFromContainer
    
    def _isContainer(self, thing):

        """Check if 'thing' is a Python module or a subclass of
        SettingsContainer."""
        
        return type(thing) == ModuleType or (
            type(thing) == ClassType and issubclass(thing, SettingsContainer)
            ) 

    def _getAllAttrsFromContainer(self, container):
        """Extract all the attributes of a SettingsContainer subclass.

        The 'container' is a class, so extracting all attributes from it, an
        instance of it, and all its base classes.

        This method is not recursive.
        """

        attrs = container.__dict__.copy() 
        # init an instance of the container and get all attributes
        attrs.update( container().__dict__ ) 
        
        for base in container.__bases__:
            for k, v in base.__dict__.items():
                if not attrs.has_key(k):
                    attrs[k] = v
        return attrs

    def readSettingsFromPySrcFile(self, path):
        
        """Return new settings dict from variables in a Python source file.

        This method will temporarily add the directory of src file to sys.path so
        that import statements relative to that dir will work properly."""
        
        path = self.normalizePath(path)
        dirName = os.path.dirname(path)
        tmpPath = tempfile.mkstemp('webware_temp')
        
        pySrc = translateClassBasedConfigSyntax(open(path).read())
        modName = path.replace('.','_').replace('/','_').replace('\\','_')        
        open(tmpPath, 'w').write(pySrc)
        try:
            fp = open(tmpPath)
            self._sysPathLock.acquire()
            sys.path.insert(0, dirName)
            module = imp.load_source(modName, path, fp)
            newSettings = self.readSettingsFromModule(module)
            del sys.path[0]
            self._sysPathLock.release()            
            return newSettings
        finally:
            fp.close()
            try:
                os.remove(tmpPath)
            except:
                pass
            if os.path.exists(tmpPath + 'c'):
                try:
                    os.remove(tmpPath + 'c')
                except:
                    pass
            if os.path.exists(path + 'c'):
                try:
                    os.remove(path + 'c')
                except:
                    pass
                
        
    def readSettingsFromPySrcStr(self, theString):
        
        """Return a dictionary of the settings in a Python src string."""

        globalsDict = {'True':1,
                       'False':0,
                       'SettingsContainer':SettingsContainer,
                       }
        newSettings = {'self':self}
        exec theString in globalsDict, newSettings
        del newSettings['self'], newSettings['True'], newSettings['False']
        module = new.module('temp_settings_module')
        module.__dict__.update(newSettings)
        return self.readSettingsFromModule(module)

    def readSettingsFromConfigFile(self, path, convert=True):
        path = self.normalizePath(path)
        fp = open(path)
        settings = self.readSettingsFromConfigFileObj(fp, convert=convert)
        fp.close()
        return settings

    def readSettingsFromConfigFileObj(self, inFile, convert=True):
        
        """Return the settings from a config file that uses the syntax accepted by
        Python's standard ConfigParser module (like Windows .ini files).

        NOTE:
        this method maintains case unlike the ConfigParser module, unless this
        class was initialized with the 'caseSensitive' keyword set to False.

        All setting values are initially parsed as strings. However, If the
        'convert' arg is True this method will do the following value
        conversions:
        
        * all Python numeric literals will be coverted from string to number
        
        * The string 'None' will be converted to the Python value None
        
        * The string 'True' will be converted to a Python truth value
        
        * The string 'False' will be converted to a Python false value
        
        * Any string starting with 'python:' will be treated as a Python literal
          or expression that needs to be eval'd. This approach is useful for
          declaring lists and dictionaries.

        If a config section titled 'Globals' is present the options defined
        under it will be treated as top-level settings.        
        """
        
        p = self._ConfigParserClass()
        p.readfp(inFile)
        sects = p.sections()
        newSettings = {}

        sects = p.sections()
        newSettings = {}
        
        for s in sects:
            newSettings[s] = {}
            for o in p.options(s):
                if o != '__name__':
                    newSettings[s][o] = p.get(s,o)

        ## loop through new settings -> deal with global settings, numbers,
        ## booleans and None ++ also deal with 'importSettings' commands

        for sect, subDict in newSettings.items():
            for key, val in subDict.items():
                if convert:
                    if val.lower().startswith('python:'):
                        subDict[key] = eval(val[7:],{},{})
                    if val.lower() == 'none':
                        subDict[key] = None
                    if val.lower() == 'true':
                        subDict[key] = True
                    if val.lower() == 'false':
                        subDict[key] = False
                    if stringIsNumber(val):
                        subDict[key] = convStringToNum(val)
                        
                ## now deal with any 'importSettings' commands
                if key.lower() == 'importsettings':
                    if val.find(';') < 0:
                        importedSettings = self.readSettingsFromPySrcFile(val)
                    else:
                        path = val.split(';')[0]
                        rest = ''.join(val.split(';')[1:]).strip()
                        parentDict = self.readSettingsFromPySrcFile(path)
                        importedSettings = eval('parentDict["' + rest + '"]')
                        
                    subDict.update(mergeNestedDictionaries(subDict,
                                                           importedSettings))
                        
            if sect.lower() == 'globals':
                newSettings.update(newSettings[sect])
                del newSettings[sect]
                
        return newSettings


class SettingsManager(_SettingsCollector):
    
    """A mixin class that provides facilities for managing application settings.
    
    SettingsManager is designed to work well with nested settings dictionaries
    of any depth.
    """

    ## init methods
    
    def __init__(self):
        """MUST BE CALLED BY SUBCLASSES"""
        _SettingsCollector.__init__(self)
        self._settings = {}
        self._initializeSettings()

    def _defaultSettings(self):
        return {}
    
    def _initializeSettings(self):
        
        """A hook that allows for complex setting initialization sequences that
        involve references to 'self' or other settings.  For example:
              self._settings['myCalcVal'] = self._settings['someVal'] * 15        
        This method should be called by the class' __init__() method when needed.       
        The dummy implementation should be reimplemented by subclasses.
        """
        
        pass 

    ## core post startup methods

    def setting(self, name, default=NoDefault):
        
        """Get a setting from self._settings, with or without a default value."""
        
        if default is NoDefault:
            return self._settings[name]
        else:
            return self._settings.get(name, default)


    def hasSetting(self, key):
        """True/False"""
        return self._settings.has_key(key)

    def setSetting(self, name, value):
        """Set a setting in self._settings."""
        self._settings[name] = value

    def settings(self):
        """Return a reference to the settings dictionary"""
        return self._settings
        
    def copySettings(self):
        """Returns a shallow copy of the settings dictionary"""
        return copy(self._settings)

    def deepcopySettings(self):
        """Returns a deep copy of the settings dictionary"""
        return deepcopy(self._settings)
    
    def updateSettings(self, newSettings, merge=True):
        
        """Update the settings with a selective merge or a complete overwrite."""
        
        if merge:
            mergeNestedDictionaries(self._settings, newSettings)
        else:
            self._settings.update(newSettings)




    ## source specific update methods

    def updateSettingsFromPySrcStr(self, theString, merge=True):
        
        """Update the settings from a code in a Python src string."""
        
        newSettings = self.readSettingsFromPySrcStr(theString)
        self.updateSettings(newSettings,
                            merge=newSettings.get('mergeSettings',merge) )
        
    def updateSettingsFromPySrcFile(self, path, merge=True):
        
        """Update the settings from variables in a Python source file.

        This method will temporarily add the directory of src file to sys.path so
        that import statements relative to that dir will work properly."""
        
        newSettings = self.readSettingsFromPySrcFile(path)
        self.updateSettings(newSettings,
                            merge=newSettings.get('mergeSettings',merge) )


    def updateSettingsFromConfigFile(self, path, **kw):
        
        """Update the settings from a text file using the syntax accepted by
        Python's standard ConfigParser module (like Windows .ini files). 
        """
        
        path = self.normalizePath(path)
        fp = open(path)
        self.updateSettingsFromConfigFileObj(fp, **kw)
        fp.close()

    
    def updateSettingsFromConfigFileObj(self, inFile, convert=True, merge=True):
        
        """See the docstring for .updateSettingsFromConfigFile()

        The caller of this method is responsible for closing the inFile file
        object."""

        newSettings = self.readSettingsFromConfigFileObj(inFile, convert=convert)
        self.updateSettings(newSettings,
                            merge=newSettings.get('mergeSettings',merge))

    def updateSettingsFromConfigStr(self, configStr, convert=True, merge=True):
        
        """See the docstring for .updateSettingsFromConfigFile()
        """

        configStr = '[globals]\n' + configStr
        inFile = StringIO(configStr)
        newSettings = self.readSettingsFromConfigFileObj(inFile, convert=convert)
        self.updateSettings(newSettings,
                            merge=newSettings.get('mergeSettings',merge))


    ## methods for output representations of the settings

    def _createConfigFile(self, outFile=None):
        
        """
        Write all the settings that can be represented as strings to an .ini
        style config string.

        This method can only handle one level of nesting and will only work with
        numbers, strings, and None.
	    """

        if outFile is None:
            outFile = StringIO()
        iniSettings = {'Globals':{}}
        globals = iniSettings['Globals']
        
        for key, theSetting in self.settings().items():
            if type(theSetting) in convertableToStrTypes:
                globals[key] = theSetting
            if type(theSetting) is DictType:
                iniSettings[key] = {}
                for subKey, subSetting in theSetting.items():
                    if type(subSetting) in convertableToStrTypes:
                        iniSettings[key][subKey] = subSetting
        
        sections = iniSettings.keys()
        sections.sort()
        outFileWrite = outFile.write # short-cut namebinding for efficiency
        for section in sections:
            outFileWrite("[" + section + "]\n")
            sectDict = iniSettings[section]
            
            keys = sectDict.keys()
            keys.sort()
            for key in keys:
                if key == "__name__":
                    continue
                outFileWrite("%s = %s\n" % (key, sectDict[key]))
            outFileWrite("\n")

        return outFile
        
    def writeConfigFile(self, path):
        
        """Write all the settings that can be represented as strings to an .ini
        style config file."""
        
        path = self.normalizePath(path)
        fp = open(path,'w')
        self._createConfigFile(fp)
        fp.close()
        
    def getConfigString(self):
        """Return a string with the settings in .ini file format."""
        
        return self._createConfigFile().getvalue()

# vim: shiftwidth=4 tabstop=4 expandtab
