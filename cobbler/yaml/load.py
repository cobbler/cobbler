"""
pyyaml legacy
Copyright (c) 2001 Steve Howell and Friends; All Rights Reserved
(see open source license information in docs/ directory)
"""

import re, string
from implicit import convertImplicit
from inline import InlineTokenizer
from klass import DefaultResolver
from stream import YamlLoaderException, FileStream, StringStream, NestedDocs

try:
    iter(list()) # is iter supported by this version of Python?
except:
    # XXX - Python 2.1 does not support iterators   
    class StopIteration: pass
    class iter:
        def __init__(self,parser):
            self._docs = []
            try:
                while 1:
                   self._docs.append(parser.next())
            except StopIteration: pass
            self._idx = 0
        def __len__(self): return len(self._docs)
        def __getitem__(self,idx): return self._docs[idx]
        def next(self):
            if self._idx < len(self._docs):
                ret = self._docs[self._idx] 
                self._idx = self._idx + 1
                return ret
            raise StopIteration

def loadFile(filename, typeResolver=None):
    return loadStream(FileStream(filename),typeResolver)
   
def load(str, typeResolver=None):
    return loadStream(StringStream(str), typeResolver)

def l(str): return load(str).next()

def loadStream(stream, typeResolver):
    return iter(Parser(stream, typeResolver))

def tryProductions(productions, value):
    for production in productions:
        results = production(value)
        if results:
            (ok, result) = results
            if ok:
                return (1, result)

def dumpDictionary(): return {}

class Parser:
    def __init__(self, stream, typeResolver=None):
        try:
            self.dictionary = dict
        except:
            self.dictionary = dumpDictionary
        self.nestedDocs = NestedDocs(stream)
        self.aliases = {}
        if typeResolver:
            self.typeResolver = typeResolver
        else:
            self.typeResolver = DefaultResolver()

    def error(self, msg):
        self.nestedDocs.error(msg, self.line)

    def nestPop(self):
        line = self.nestedDocs.pop()
        if line is not None:
            self.line = line
            return 1

    def value(self, indicator):
        return getToken(indicator+"\s*(.*)", self.line)

    def getNextDocument(self): raise "getNextDocument() deprecated--use next()"

    def next(self):
        line = self.nestedDocs.popDocSep()
        indicator = getIndicator(line)
        if indicator:
            return self.parse_value(indicator)
        if line:
            self.nestedDocs.nestToNextLine()
            return self.parseLines()
        raise StopIteration

    def __iter__(self): return self

    def parseLines(self):
        peekLine = self.nestedDocs.peek()
        if peekLine:
            if re.match("\s*-", peekLine):
                return self.parse_collection([], self.parse_seq_line)
            else:
                return self.parse_collection(self.dictionary(), self.parse_map_line)
        raise StopIteration

    def parse_collection(self, items, lineParser):
        while self.nestPop():
            if self.line:
                lineParser(items)
        return items    

    def parse_seq_line(self, items):
        value = self.value("-")
        if value is not None:
            items.append(self.parse_seq_value(value))
        else:
            self.error("missing '-' for seq")

    def parse_map_line(self, items):
        if (self.line == '?'):
            self.parse_map_line_nested(items)
        else:
            self.parse_map_line_simple(items, self.line)

    def parse_map_line_nested(self, items):
        self.nestedDocs.nestToNextLine()
        key = self.parseLines()
        if self.nestPop():
            value = self.value(':')
            if value is not None:
                items[tuple(key)] = self.parse_value(value)
                return
        self.error("key has no value for nested map")

    def parse_map_line_simple(self, items, line):
        map_item = self.key_value(line)
        if map_item:
            (key, value) = map_item
            key = convertImplicit(key)
            if items.has_key(key):
                self.error("Duplicate key "+key)
            items[key] = self.parse_value(value)
        else:
            self.error("bad key for map")

    def is_map(self, value):
        # XXX - need real tokenizer
        if len(value) == 0:
            return 0
        if value[0] == "'":
            return 0
        if re.search(':(\s|$)', value):       
            return 1

    def parse_seq_value(self, value):
        if self.is_map(value):
            return self.parse_compressed_map(value)
        else:
            return self.parse_value(value)

    def parse_compressed_map(self, value):
        items = self.dictionary()
        line = self.line
        token = getToken("(\s*-\s*)", line)
        self.nestedDocs.nestBySpecificAmount(len(token))
        self.parse_map_line_simple(items, value)
        return self.parse_collection(items, self.parse_map_line)

    def parse_value(self, value):
        (alias, value) = self.testForRepeatOfAlias(value)
        if alias:
            return value
        (alias, value) = self.testForAlias(value)            
        value = self.parse_unaliased_value(value)
        if alias:
            self.aliases[alias] = value
        return value          

    def parse_unaliased_value(self, value):
        match = re.match(r"(!\S*)(.*)", value)
        if match:
            (url, value) = match.groups()
            value = self.parse_untyped_value(value)
            if url[:2] == '!!':
                return self.typeResolver.resolveType(value, url)
            else:
                # XXX - allows syntax, but ignores it
                return value
        return self.parse_untyped_value(value)

    def parseInlineArray(self, value):        
        if re.match("\s*\[", value):
            return self.parseInline([], value, ']', 
                self.parseInlineArrayItem)

    def parseInlineHash(self, value):        
        if re.match("\s*{", value):
            return self.parseInline(self.dictionary(), value, '}', 
                self.parseInlineHashItem)

    def parseInlineArrayItem(self, result, token):
        return result.append(convertImplicit(token))

    def parseInlineHashItem(self, result, token):
        (key, value) = self.key_value(token)
        result[key] = value

    def parseInline(self, result, value, end_marker, itemMethod):
        tokenizer = InlineTokenizer(value)
        tokenizer.next()
        while 1:
            token = tokenizer.next()
            if token == end_marker:
                break
            itemMethod(result, token)
        return (1, result)

    def parseSpecial(self, value):
        productions = [
            self.parseMultiLineScalar,
            self.parseInlineHash,
            self.parseInlineArray,
        ]
        return tryProductions(productions, value)

    def parse_untyped_value(self, value):
        parse = self.parseSpecial(value)
        if parse:
            (ok, data) = parse
            return data
        token = getToken("(\S.*)", value)
        if token:
            lines = [token] + \
                pruneTrailingEmpties(self.nestedDocs.popNestedLines())
            return convertImplicit(joinLines(lines))
        else:
            self.nestedDocs.nestToNextLine()
            return self.parseLines()

    def parseNative(self, value):
        return (1, convertImplicit(value))

    def parseMultiLineScalar(self, value):
        if value == '>':
            return (1, self.parseFolded())
        elif value == '|':
            return (1, joinLiteral(self.parseBlock()))
        elif value == '|+':
            return (1, joinLiteral(self.unprunedBlock()))

    def parseFolded(self):
        data = self.parseBlock()
        i = 0
        resultString = ''
        while i < len(data)-1:
            resultString = resultString + data[i]
            resultString = resultString + foldChar(data[i], data[i+1])
            i = i + 1
        return resultString + data[-1] + "\n"        

    def unprunedBlock(self):
        self.nestedDocs.nestToNextLine()
        data = []
        while self.nestPop():
            data.append(self.line)
        return data

    def parseBlock(self):
        return pruneTrailingEmpties(self.unprunedBlock())

    def testForAlias(self, value):
        match = re.match("&(\S*)\s*(.*)", value)
        if match:
            return match.groups()
        return (None, value)

    def testForRepeatOfAlias(self, value):
        match = re.match("\*(\S+)", value)
        if match:
            alias = match.groups()[0]
            if self.aliases.has_key(alias):
                return (alias, self.aliases[alias])
            else:
                self.error("Unknown alias")
        return (None, value)

    def key_value(self, str):
        if str[-1] == ' ':
            self.error("Trailing spaces not allowed without quotes.")
        # XXX This allows mis-balanced " vs. ' stuff
        match = re.match("[\"'](.+)[\"']\s*:\s*(.*)", str)
        if match:
            (key, value) = match.groups()
            return (key, value)
        match = re.match("(.+?)\s*:\s*(.*)", str)
        if match:
            (key, value) = match.groups()
            if len(value) and value[0] == '#':
                value = ''
            return (key, value)

def getToken(regex, value):
    match = re.search(regex, value)
    if match:
        return match.groups()[0]

def pruneTrailingEmpties(data):
    while len(data) > 0 and data[-1] == '':
        data = data[:-1]
    return data

def foldChar(line1, line2):
    if re.match("^\S", line1) and re.match("^\S", line2):
        return " "
    return "\n"

def getIndicator(line):
    if line:
        header = r"(#YAML:\d+\.\d+\s*){0,1}"
        match = re.match("--- "+header+"(\S*.*)", line)
        if match:
            return match.groups()[-1]

def joinLines(lines):
    result = ''
    for line in lines[:-1]:
        if line[-1] == '\\':
            result = result + line[:-1]
        else:
            result = result + line + " "
    return result + lines[-1]

def joinLiteral(data):
    return string.join(data,"\n") + "\n"

