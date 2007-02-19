#!/usr/bin/env python
# $Id: Filters.py,v 1.28 2006/06/16 20:15:24 hierro Exp $
"""Filters for the #filter directive; output filters Cheetah's $placeholders .

Filters may now be used standalone, for debugging or for use outside Cheetah.
Class DummyTemplate, instance _dummyTemplateObj and class NoDefault exist only
for this, to provide a default argument for the filter constructors (which
would otherwise require a real template object).  

The default filter is now RawOrEncodedUnicode.  Please use this as a base class instead of Filter because it handles non-ASCII characters better.

Meta-Data
================================================================================
Author: Tavis Rudd <tavis@damnsimple.com>
Version: $Revision: 1.28 $
Start Date: 2001/08/01
Last Revision Date: $Date: 2006/06/16 20:15:24 $
"""
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.28 $"[11:-2]

from StringIO import StringIO # not cStringIO because of unicode support

# Additional entities WebSafe knows how to transform.  No need to include
# '<', '>' or '&' since those will have been done already.
webSafeEntities = {' ': '&nbsp;', '"': '&quot;'}

class Error(Exception):
    pass

class NoDefault:
    pass


class DummyTemplate:
    """Fake template class to allow filters to be used standalone.

    This is provides only the level of Template compatibility required by the
    standard filters.  Namely, the get-settings interface works but there are
    no settings.  Other aspects of Template are not implemented.
    """
    def setting(self, name, default=NoDefault):
        if default is NoDefault:
            raise KeyError(name)
        else:
            return default

    def settings(self):
        return {}

_dummyTemplateObj = DummyTemplate()


##################################################
## BASE CLASS

class Filter(object):
    """A baseclass for the Cheetah Filters."""
    
    def __init__(self, templateObj=_dummyTemplateObj):
        """Setup a ref to the templateObj.  Subclasses should call this method.
        """
        if hasattr(templateObj, 'setting'):
            self.setting = templateObj.setting
        else:
            self.setting = lambda k: None

        if hasattr(templateObj, 'settings'):
            self.settings = templateObj.settings
        else:
            self.settings = lambda: {}

    def generateAutoArgs(self):
        
        """This hook allows the filters to generate an arg-list that will be
        appended to the arg-list of a $placeholder tag when it is being
        translated into Python code during the template compilation process. See
        the 'Pager' filter class for an example."""
        
        return ''
        
    def filter(self, val, **kw):
        
        """Reimplement this method if you  want more advanced filterting."""
        
        return str(val)


##################################################
## ENHANCED FILTERS

#####
class ReplaceNone(Filter):
    def filter(self, val, **kw):
        
        """Replace None with an empty string.  Reimplement this method if you
        want more advanced filterting."""
        
        if val is None:
            return ''
        return str(val)
#####
class EncodeUnicode(Filter):
    def filter(self, val,
               encoding='utf8',
               str=str, type=type, unicodeType=type(u''),
               **kw):
        """Encode Unicode strings, by default in UTF-8.

        >>> import Cheetah.Template
        >>> t = Cheetah.Template.Template('''
        ... $myvar
        ... ${myvar, encoding='utf16'}
        ... ''', searchList=[{'myvar': u'Asni\xe8res'}],
        ... filter='EncodeUnicode')
        >>> print t
        """
        if type(val)==unicodeType:
            filtered = val.encode(encoding)
        elif val is None:
            filtered = ''
        else:
            filtered = str(val)
        return filtered

class RawOrEncodedUnicode(Filter):
    def filter(self, val,
               #encoding='utf8',
               encoding=None,
               str=str, type=type, unicodeType=type(u''),
               **kw):
        """Pass Unicode strings through unmolested, unless an encoding is specified.
        """
        if type(val)==unicodeType:
            if encoding:
                filtered = val.encode(encoding)
            else:
                filtered = val
        elif val is None:
            filtered = ''
        else:
            filtered = str(val)
        return filtered

#####
class MaxLen(RawOrEncodedUnicode):
    def filter(self, val, **kw):
        """Replace None with '' and cut off at maxlen."""
        
    	output = super(MaxLen, self).filter(val, **kw)
        if kw.has_key('maxlen') and len(output) > kw['maxlen']:
            return output[:kw['maxlen']]
        return output


#####
class Pager(RawOrEncodedUnicode):
    def __init__(self, templateObj=_dummyTemplateObj):
        Filter.__init__(self, templateObj)
        self._IDcounter = 0
        
    def buildQString(self,varsDict, updateDict):
        finalDict = varsDict.copy()
        finalDict.update(updateDict)
        qString = '?'
        for key, val in finalDict.items():
            qString += str(key) + '=' + str(val) + '&'
        return qString

    def generateAutoArgs(self):
        ID = str(self._IDcounter)
        self._IDcounter += 1
        return ', trans=trans, ID=' + ID
    
    def filter(self, val, **kw):
        """Replace None with '' and cut off at maxlen."""
    	output = super(Pager, self).filter(val, **kw)
        if kw.has_key('trans') and kw['trans']:
            ID = kw['ID']
            marker = kw.get('marker', '<split>')
            req = kw['trans'].request()
            URI = req.environ()['SCRIPT_NAME'] + req.environ()['PATH_INFO']
            queryVar = 'pager' + str(ID) + '_page'
            fields = req.fields()
            page = int(fields.get( queryVar, 1))
            pages = output.split(marker)
            output = pages[page-1]
            output += '<BR>'
            if page > 1:
                output +='<A HREF="' + URI + self.buildQString(fields, {queryVar:max(page-1,1)}) + \
                          '">Previous Page</A>&nbsp;&nbsp;&nbsp;'
            if page < len(pages):
                output += '<A HREF="' + URI + self.buildQString(
                    fields,
                    {queryVar:
                     min(page+1,len(pages))}) + \
                     '">Next Page</A>' 

            return output
        return output


#####
class WebSafe(RawOrEncodedUnicode):
    """Escape HTML entities in $placeholders.
    """
    def filter(self, val, **kw):
    	s = super(WebSafe, self).filter(val, **kw)
        # These substitutions are copied from cgi.escape().
        s = s.replace("&", "&amp;") # Must be done first!
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        # Process the additional transformations if any.
        if kw.has_key('also'):
            also = kw['also']
            entities = webSafeEntities   # Global variable.
            for k in also:
                if entities.has_key(k):
                    v = entities[k]
                else:
                    v = "&#%s;" % ord(k)
                s = s.replace(k, v)
        # Return the puppy.
        return s


#####
class Strip(RawOrEncodedUnicode):
    """Strip leading/trailing whitespace but preserve newlines.

    This filter goes through the value line by line, removing leading and
    trailing whitespace on each line.  It does not strip newlines, so every
    input line corresponds to one output line, with its trailing newline intact.

    We do not use val.split('\n') because that would squeeze out consecutive
    blank lines.  Instead, we search for each newline individually.  This
    makes us unable to use the fast C .split method, but it makes the filter
    much more widely useful.

    This filter is intended to be usable both with the #filter directive and
    with the proposed #sed directive (which has not been ratified yet.)
    """
    def filter(self, val, **kw):
    	s = super(Strip, self).filter(val, **kw)
        result = []
        start = 0   # The current line will be s[start:end].
        while 1: # Loop through each line.
            end = s.find('\n', start)  # Find next newline.
            if end == -1:  # If no more newlines.
                break
            chunk = s[start:end].strip()
            result.append(chunk)
            result.append('\n')
            start = end + 1
        # Write the unfinished portion after the last newline, if any.
        chunk = s[start:].strip()
        result.append(chunk)
        return "".join(result)

#####
class StripSqueeze(RawOrEncodedUnicode):
    """Canonicalizes every chunk of whitespace to a single space.

    Strips leading/trailing whitespace.  Removes all newlines, so multi-line
    input is joined into one ling line with NO trailing newline.
    """
    def filter(self, val, **kw):
    	s = super(StripSqueeze, self).filter(val, **kw)
        s = s.split()
        return " ".join(s)
    
##################################################
## MAIN ROUTINE -- testing
    
def test():
    s1 = "abc <=> &"
    s2 = "   asdf  \n\t  1  2    3\n"
    print "WebSafe INPUT:", `s1`
    print "      WebSafe:", `WebSafe().filter(s1)`
    
    print
    print " Strip INPUT:", `s2`
    print "       Strip:", `Strip().filter(s2)`
    print "StripSqueeze:", `StripSqueeze().filter(s2)`

    print "Unicode:", `EncodeUnicode().filter(u'aoeu12345\u1234')`
    
if __name__ == "__main__":  test()
    
# vim: shiftwidth=4 tabstop=4 expandtab
