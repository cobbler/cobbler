"""
pyyaml legacy
Copyright (c) 2001 Steve Howell and Friends; All Rights Reserved
(see open source license information in docs/ directory)
"""


import types
import string
from types import StringType, UnicodeType, IntType, FloatType
from types import DictType, ListType, TupleType, InstanceType
from klass import hasMethod, isDictionary
import re

"""
  The methods from this module that are exported to the top 
  level yaml package should remain stable.  If you call
  directly into other methods of this module, be aware that 
  they may change or go away in future implementations.
  Contact the authors if there are methods in this file 
  that you wish to remain stable.
"""

def dump(*data):
    return Dumper().dump(*data)

def d(data): return dump(data)

def dumpToFile(file, *data):
    return Dumper().dumpToFile(file, *data)

class Dumper:
    def __init__(self):
        self.currIndent   = "\n"
        self.indent = "    "
        self.keysrt   = None
        self.alphaSort = 1 # legacy -- on by default

    def setIndent(self, indent):
        self.indent = indent
        return self

    def setSort(self, sort_hint):
        self.keysrt = sortMethod(sort_hint)
        return self

    def dump(self, *data):
        self.result = []  
        self.output = self.outputToString
        self.dumpDocuments(data)
        return string.join(self.result,"")

    def outputToString(self, data):
        self.result.append(data)

    def dumpToFile(self, file, *data):
        self.file = file
        self.output = self.outputToFile
        self.dumpDocuments(data)

    def outputToFile(self, data):
        self.file.write(data)

    def dumpDocuments(self, data):
        for obj in data:
            self.anchors  = YamlAnchors(obj)
            self.output("---")
            self.dumpData(obj)
            self.output("\n")       

    def indentDump(self, data):
        oldIndent = self.currIndent
        self.currIndent += self.indent
        self.dumpData(data)
        self.currIndent = oldIndent

    def dumpData(self, data):
        anchor = self.anchors.shouldAnchor(data)
        # Disabling anchors because they are lame for strings that the user might want to view/edit -- mdehaan
        # 
        #if anchor: 
        #    self.output(" &%d" % anchor )
        #else:
        #    anchor = self.anchors.isAlias(data)
        #    if anchor:
        #        self.output(" *%d" % anchor )
        #        return
        if (data is None):
            self.output(' ~')
        elif hasMethod(data, 'to_yaml'):
            self.dumpTransformedObject(data)            
        elif hasMethod(data, 'to_yaml_implicit'):
            self.output(" " + data.to_yaml_implicit())
        elif type(data) is InstanceType:
            self.dumpRawObject(data)
        elif isDictionary(data):
            self.dumpDict(data)
        elif type(data) in [ListType, TupleType]:
            self.dumpList(data)
        else:
            self.dumpScalar(data)

    def dumpTransformedObject(self, data):
        obj_yaml = data.to_yaml()
        if type(obj_yaml) is not TupleType:
            self.raiseToYamlSyntaxError()
        (data, typestring) = obj_yaml
        if typestring:
            self.output(" " + typestring)
        self.dumpData(data)

    def dumpRawObject(self, data):
        self.output(' !!%s.%s' % (data.__module__, data.__class__.__name__))
        self.dumpData(data.__dict__)

    def dumpDict(self, data):
        keys = data.keys()
        if len(keys) == 0:
            self.output(" {}")
            return
        if self.keysrt:
            keys = sort_keys(keys,self.keysrt)
        else:
            if self.alphaSort:
                keys.sort()
        for key in keys:
            self.output(self.currIndent)
            self.dumpKey(key)
            self.output(":")
            self.indentDump(data[key])

    def dumpKey(self, key):
        if type(key) is TupleType:
            self.output("?")
            self.indentDump(key) 
            self.output("\n")
        else:
            self.output(quote(key))

    def dumpList(self, data):
        if len(data) == 0:
            self.output(" []")
            return
        for item in data:
            self.output(self.currIndent)
            self.output("-")
            self.indentDump(item)

    def dumpScalar(self, data):
        if isUnicode(data):
            self.output(' "%s"' % repr(data)[2:-1])
        elif isMulti(data):
            self.dumpMultiLineScalar(data.splitlines())
        else:
            self.output(" ")
            self.output(quote(data))
    
    def dumpMultiLineScalar(self, lines):
        self.output(" |")
        if lines[-1] == "":
            self.output("+")
        for line in lines:
            self.output(self.currIndent)
            self.output(line)

    def raiseToYamlSyntaxError(self):
            raise """
to_yaml should return tuple w/object to dump 
and optional YAML type.  Example:
({'foo': 'bar'}, '!!foobar')
"""

#### ANCHOR-RELATED METHODS

def accumulate(obj,occur):
    typ = type(obj)
    if obj is None or \
       typ is IntType or \
       typ is FloatType or \
       ((typ is StringType or typ is UnicodeType) \
       and len(obj) < 32): return
    obid = id(obj)
    if 0 == occur.get(obid,0):
        occur[obid] = 1
        if typ is ListType:
            for x in obj: 
                accumulate(x,occur)
        if typ is DictType:
            for (x,y) in obj.items():
                accumulate(x,occur)
                accumulate(y,occur)
    else:
        occur[obid] = occur[obid] + 1

class YamlAnchors:
     def __init__(self,data):
         occur = {}
         accumulate(data,occur)
         anchorVisits = {}
         for (obid, occur) in occur.items():
             if occur > 1:
                 anchorVisits[obid] = 0 
         self._anchorVisits = anchorVisits
         self._currentAliasIndex     = 0
     def shouldAnchor(self,obj):
         ret = self._anchorVisits.get(id(obj),None)
         if 0 == ret:
             self._currentAliasIndex = self._currentAliasIndex + 1
             ret = self._currentAliasIndex
             self._anchorVisits[id(obj)] = ret
             return ret
         return 0
     def isAlias(self,obj):
         return self._anchorVisits.get(id(obj),0)

### SORTING METHODS

def sort_keys(keys,fn):
    tmp = []
    for key in keys:
        val = fn(key)
        if val is None: val = '~'
        tmp.append((val,key))
    tmp.sort()
    return [ y for (x,y) in tmp ]

def sortMethod(sort_hint):
    typ = type(sort_hint)
    if DictType == typ:
        return sort_hint.get
    elif ListType == typ or TupleType == typ:
        indexes = {}; idx = 0
        for item in sort_hint:
            indexes[item] = idx
            idx += 1
        return indexes.get
    else:
        return sort_hint

### STRING QUOTING AND SCALAR HANDLING
def isStr(data):
    # XXX 2.1 madness
    if type(data) == type(''):
        return 1
    if type(data) == type(u''):
        return 1
    return 0
    
def doubleUpQuotes(data):
    return data.replace("'", "''")

def quote(data):
    if not isStr(data):
        return str(data)
    single = "'"
    double = '"'
    mquote = ''
    if len(data) == 0:
        return "''"
    if hasSpecialChar(data) or data[0] == single:
        data = `data`[1:-1]
        data = string.replace(data, r"\x08", r"\b")
        mquote = double 
    elif needsSingleQuote(data):
        mquote = single
        data = doubleUpQuotes(data)
    return "%s%s%s" % (mquote, data, mquote)

def needsSingleQuote(data):
    if re.match(r"^-?\d", data):
        return 1
    if re.match(r"\*\S", data):
        return 1
    if data[0] in ['&', ' ']:
        return 1
    if data[0] == '"' or data[0] == "'":
        return 1
    if data[-1] == ' ':
        return 1
    return (re.search(r'[:]', data) or re.search(r'(\d\.){2}', data))

def hasSpecialChar(data):
    # need test to drive out '#' from this
    return re.search(r'[-\t\b\r\f#]', data)

def isMulti(data):
    if not isStr(data):
        return 0
    if hasSpecialChar(data):
        return 0
    return re.search("\n", data)

def isUnicode(data):
    return type(data) == unicode
    
def sloppyIsUnicode(data):
        # XXX - hack to make tests pass for 2.1
        return repr(data)[:2] == "u'" and repr(data) != data

import sys
if sys.hexversion < 0x20200000:
    isUnicode = sloppyIsUnicode
    


