import time, re, string
from types import ListType, TupleType

PRIVATE_NOTICE = """
  This module is considered to be private implementation
  details and is subject to change.  Please only use the
  objects and methods exported to the top level yaml package.
"""

# 
# Time specific operations
#

_splitTime = re.compile('\-|\s|T|t|:|\.|Z')
matchTime = re.compile(\
          '\d+-\d+-\d+([\s|T|t]\d+:\d+:\d+.\d+(Z|(\s?[\-|\+]\d+:\d+)))?')

def _parseTime(val):
    if not matchTime.match(val): raise ValueError(val)
    tpl = _splitTime.split(val)
    if not(tpl): raise ValueError(val)
    siz = len(tpl)
    sec = 0
    if 3 == siz:
       tpl += [0,0,0,0,0,-1]
    elif 7 == siz:
       tpl.append(0)
       tpl.append(-1)
    elif 8 == siz:
       if len(tpl.pop()) > 0: raise ValueError(val)
       tpl.append(0)
       tpl.append(-1)
    elif 9 == siz or 10 == siz:
       mn = int(tpl.pop())
       hr = int(tpl.pop())
       sec = (hr*60+mn)*60
       if val.find("+") > -1: sec = -sec
       if 10 == siz: tpl.pop()
       tpl.append(0)
       tpl.append(-1)
    else:
       raise ValueError(val)
    idx = 0
    while idx < 9:
       tpl[idx] = int(tpl[idx])
       idx += 1
    if tpl[1] < 1 or tpl[1] > 12: raise ValueError(val)
    if tpl[2] < 1 or tpl[2] > 31: raise ValueError(val)
    if tpl[3] > 24: raise ValueError(val)
    if tpl[4] > 61: raise ValueError(val)
    if tpl[5] > 61: raise ValueError(val)
    if tpl[0] > 2038:
        #TODO: Truncation warning
        tpl = (2038,1,18,0,0,0,0,0,-1)
    tpl = tuple(tpl)
    ret = time.mktime(tpl)
    ret = time.localtime(ret+sec)
    ret = ret[:8] + (0,)
    return ret


class _timestamp:
    def __init__(self,val=None):
        if not val:
           self.__tval = time.gmtime()
        else:
           typ = type(val)
           if ListType == typ:
               self.__tval = tuple(val)
           elif TupleType == typ:
               self.__tval = val
           else:
               self.__tval = _parseTime(val)
           if 9 != len(self.__tval): raise ValueError
    def __getitem__(self,idx): return self.__tval[idx]
    def __len__(self): return 9
    def strftime(self,format): return time.strftime(format,self.__tval)
    def mktime(self):          return time.mktime(self.__tval)
    def asctime(self):  return time.asctime(self.__tval)
    def isotime(self):  
        return "%04d-%02d-%02dT%02d:%02d:%02d.00Z" % self.__tval[:6]
    def __repr__(self): return "yaml.timestamp('%s')" % self.isotime()    
    def __str__(self):  return self.isotime()
    def to_yaml_implicit(self): return self.isotime()
    def __hash__(self): return hash(self.__tval[:6]) 
    def __cmp__(self,other): 
        try:
            return cmp(self.__tval[:6],other.__tval[:6])
        except AttributeError:
            return -1

try: # inherit from mx.DateTime functionality if available
    from mx import DateTime
    class timestamp(_timestamp):
        def __init__(self,val=None):
            _timestamp.__init__(self,val)
            self.__mxdt = DateTime.mktime(self.__tval)
        def __getattr__(self, name):
              return getattr(self.__mxdt, name)
except:
    class timestamp(_timestamp): pass
        


def unquote(expr):
    """
        summary: >
           Simply returns the unquoted string, and the
           length of the quoted string token at the 
           beginning of the expression.
    """
    tok = expr[0]
    if "'" == tok: 
        idx = 1
        odd = 0
        ret = ""
        while idx < len(expr):
            chr = expr[idx]
            if "'" == chr:
                if odd: ret += chr
                odd = not odd
            else:
                if odd:
                    tok = expr[:idx]
                    break
                ret += chr
            idx += 1
        if "'" == tok: tok = expr
        return (ret,len(tok))
    if '"' == tok:
        idx = 1
        esc = 0
        while idx < len(expr):
            chr = expr[idx]
            if '"' == chr and not esc:
                tok = expr[:idx] + '"'
                break
            if '\\' == chr and not esc: esc = 1
            else: esc = 0
            idx += 1
        if '"' == tok:
            raise SyntaxError("unmatched quote: " + expr)
        ret = eval(tok)  #TODO: find better way to unquote
        return (ret,len(tok))
    return (expr,len(expr))
