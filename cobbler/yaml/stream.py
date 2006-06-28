import re
import string

def indentLevel(line):
    n = 0
    while n < len(line) and line[n] == ' ':
        n = n + 1
    return n

class LineNumberStream:
    def __init__(self, filename=None):
        self.curLine = 0
        self.filename = filename

    def get(self):
        line = self.getLine()
        self.curLine += 1 # used by subclass
        if line:
            line = noLineFeed(line)
        return line

    def lastLineRead(self):
        return self.curLine

class FileStream(LineNumberStream):
    def __init__(self, filename):
        self.fp = open(filename)
        LineNumberStream.__init__(self, filename)

    def getLine(self):
        line = self.fp.readline()
        if line == '': line = None
        return line

class StringStream(LineNumberStream):
    def __init__(self, text):
        self.lines = split(text)
        self.numLines = len(self.lines)
        LineNumberStream.__init__(self)

    def getLine(self):
        if self.curLine < self.numLines:
            return self.lines[self.curLine]

def split(text):
    lines = string.split(text, '\n')
    if lines[-1] == '':
        lines.pop()
    return lines

def eatNewLines(stream):
    while 1:
       line = stream.get()
       if line is None or len(string.strip(line)):
           return line

COMMENT_LINE_REGEX = re.compile(R"\s*#")
def isComment(line):
    return line is not None and COMMENT_LINE_REGEX.match(line)

class CommentEater:
    def __init__(self, stream):
        self.stream = stream
        self.peeked = 1
        self.line = eatNewLines(stream)
        self.eatComments()

    def eatComments(self):
        while isComment(self.line):
            self.line = self.stream.get()

    def peek(self):
        if self.peeked:
            return self.line
        self.peeked = 1
        self.line = self.stream.get()
        self.eatComments()
        return self.line

    def lastLineRead(self):
        return self.stream.lastLineRead()

    def pop(self):
        data = self.peek()
        self.peeked = 0
        return data

class NestedText:
    def __init__(self, stream):
        self.commentEater = CommentEater(stream)
        self.reset()

    def lastLineRead(self):
        return self.commentEater.lastLineRead()

    def reset(self):
        self.indentLevel = 0
        self.oldIndents = [0]

    def peek(self):
        nextLine = self.commentEater.peek()
        if nextLine is not None:
            if indentLevel(nextLine) >= self.indentLevel:
                return nextLine[self.indentLevel:]
            elif nextLine == '':
                return ''                

    def pop(self):
        line = self.peek()
        if line is None:
            self.indentLevel = self.oldIndents.pop()
            return
        self.commentEater.pop()
        return line

    def popNestedLines(self):
        nextLine = self.peek()
        if nextLine is None or nextLine == '' or nextLine[0] != ' ':
            return []
        self.nestToNextLine()
        lines = []
        while 1:
            line = self.pop()
            if line is None:
                break
            lines.append(line)
        return lines

    def nestToNextLine(self):
        line = self.commentEater.peek()
        indentation = indentLevel(line)
        if len(self.oldIndents) > 1 and indentation <= self.indentLevel:
            self.error("Inadequate indentation", line)
        self.setNewIndent(indentation)

    def nestBySpecificAmount(self, adjust):
        self.setNewIndent(self.indentLevel + adjust)
        
    def setNewIndent(self, indentLevel):
        self.oldIndents.append(self.indentLevel)
        self.indentLevel = indentLevel    

class YamlLoaderException(Exception):
    def __init__(self, *args):
        (self.msg, self.lineNum, self.line, self.filename) = args

    def __str__(self):
        msg = """\
%(msg)s:
near line %(lineNum)d:
%(line)s
""" % self.__dict__
        if self.filename:
            msg += "file: " + self.filename
        return msg

class NestedDocs(NestedText):
    def __init__(self, stream):
        self.filename = stream.filename
        NestedText.__init__(self,stream)
        line = NestedText.peek(self)
        self.sep = '---'
        if self.startsWithSep(line):
            self.eatenDocSep = NestedText.pop(self)
        else:
            self.eatenDocSep = self.sep

    def startsWithSep(self,line):
        if line and self.sep == line[:3]: return 1
        return 0

    def popDocSep(self):
        line = self.eatenDocSep
        self.eatenDocSep = None
        self.reset()
        return line

    def pop(self):
        if self.eatenDocSep is not None:
            raise "error"
        line = self.commentEater.peek()
        if line and self.startsWithSep(line):
            self.eatenDocSep = NestedText.pop(self)
            return None
        return NestedText.pop(self)

    def error(self, msg, line):
        raise YamlLoaderException(msg, self.lastLineRead(), line, self.filename)

def noLineFeed(s):
    while s[-1:] in ('\n', '\r'):
        s = s[:-1]
    return s
