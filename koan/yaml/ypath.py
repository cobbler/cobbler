from types import ListType, StringType, IntType, DictType, InstanceType
import re
from urllib import quote
from timestamp import unquote

noTarget = object()

def escape(node):
    """
        summary: >
            This function escapes a given key so that it
            may appear within a ypath.  URI style escaping
            is used so that ypath expressions can be a 
            valid URI expression.
    """
    typ = type(node)
    if typ is IntType: return str(node)
    if typ is StringType: 
        return quote(node,'')
    raise ValueError("TODO: Support more than just string and integer keys.")

class context:
    """
        summary: >
            A ypath visit context through a YAML rooted graph.
            This is implemented as a 3-tuple including the parent
            node, the current key/index and the value.  This is
            an immutable object so it can be cached.
        properties: 
            key:    mapping key or index within the parent collection
            value:  current value within the parent's range
            parent: the parent context
            root:   the very top of the yaml graph
            path:   a tuple of the domain keys
        notes: >
            The context class doesn't yet handle going down the
            domain side of the tree... 
    """         
    def __init__(self,parent,key,value):
        """
            args:
                parent: parent context (or None if this is the root)
                key:    mapping key or index for this context
                value:  value of current location...
        """
        self.parent = parent
        self.key    = key
        self.value  = value
        if parent: 
            assert parent.__class__ is self.__class__
            self.path = parent.path + (escape(key),)
            self.root = parent.root
        else:      
            assert not key
            self.path = tuple()
            self.root = self
    def __setattr__(self,attname,attval):
        if attname in ('parent','key','value'):
            if self.__dict__.get(attname):
                 raise ValueError("context is read-only")
        self.__dict__[attname] = attval
    def __hash__(self): return hash(self.path)
    def __cmp__(self,other):   
        try:
            return cmp(self.path,other.path)
        except AttributeError:
            return -1
    def __str__(self):
        if self.path:
            return "/".join(('',)+self.path)
        else:
            return '/'

def to_context(target):
    if type(target) is InstanceType:
        if target.__class__ is context:
            return target
    return context(None,None,target)

def context_test():
    lst = ['value']
    map = {'key':lst}
    x = context(None,None,map)
    y = context(x,'key',lst)
    z = context(y,0,'value')
    assert ('key',) == y.path
    assert 'key'    == y.key
    assert lst      == y.value
    assert x        == y.parent
    assert x        == y.root
    assert 0        == z.key
    assert 'value'  == z.value
    assert y        == z.parent
    assert x        == z.root 
    assert hash(x)  
    assert hash(y)
    assert hash(z)
    assert '/' == str(x)
    assert '/key' == str(y)
    assert '/key/0' == str(z)

class null_seg:
    """
        summary: >
            This is the simplest path segment, it
            doesn't return any results and doesn't
            depend upon its context.  It also happens to 
            be the base class which all segments derive.
    """
    def __iter__(self): 
        return self
    def next_null(self):
        raise StopIteration
    def bind(self,cntx):  
        """
            summary: >
                The bind function is called whenever
                the parent context has changed.
        """
        assert(cntx.__class__ is context)
        self.cntx = cntx
    def apply(self,target):
        self.bind(to_context(target))
        return iter(self)
    def exists(self,cntx):
        try:
            self.bind(cntx)
            self.next()
            return 1
        except StopIteration:
            return 0
    next = next_null
 
class self_seg(null_seg):
    """
        summary: >
            This path segment returns the context
            node exactly once.
    """
    def __str__(self): return '.'
    def next_self(self):
        self.next = self.next_null
        return self.cntx
    def bind(self,cntx):
        null_seg.bind(self,cntx)
        self.next = self.next_self

class root_seg(self_seg):
    def __str__(self): return '/'
    def bind(self,cntx):  
        self_seg.bind(self,cntx.root)

class parent_seg(self_seg):
    def __str__(self): return '..'
    def bind(self,cntx):
        if cntx.parent: cntx = cntx.parent
        self_seg.bind(self,cntx)

class wild_seg(null_seg):
    """
        summary: >
            The wild segment simply loops through
            all of the sub-contexts for a given object.
            If there aren't any children, this isn't an
            error it just doesn't return anything.
    """
    def __str__(self): return '*'
    def next_wild(self):
        key = self.keys.next()
        return context(self.cntx,key,self.values[key])
    def bind(self,cntx):  
        null_seg.bind(self,cntx)
        typ = type(cntx.value)
        if typ is ListType:
            self.keys   = iter(xrange(0,len(cntx.value)))
            self.values = cntx.value
            self.next   = self.next_wild
            return
        if typ is DictType:
            self.keys   = iter(cntx.value)
            self.values = cntx.value
            self.next   = self.next_wild
            return 
        self.next = self.next_null

class trav_seg(null_seg):
    """
        summary: >
            This is a recursive traversal of the range, preorder.
            It is a recursive combination of self and wild.
    """
    def __str__(self): return '/'
    def next(self): 
        while 1:
            (cntx,seg) = self.stk[-1]
            if not seg:
                seg = wild_seg()
                seg.bind(cntx)
                self.stk[-1] = (cntx,seg)
                return cntx
            try:
                cntx = seg.next()
                self.stk.append((cntx,None))
            except StopIteration:
                self.stk.pop()
                if not(self.stk):
                    self.next = self.next_null
                    raise StopIteration

    def bind(self,cntx):
        null_seg.bind(self,cntx)
        self.stk = [(cntx,None)]

class match_seg(self_seg):
    """
        summary: >
            Matches a particular key within the
            current context.  Kinda boring.
    """
    def __str__(self): return str(self.key)
    def __init__(self,key):
        #TODO: Do better implicit typing
        try:
           key = int(key)
        except: pass
        self.key = key
    def bind(self,cntx):
        try: 
            mtch = cntx.value[self.key]
            cntx = context(cntx,self.key,mtch)
            self_seg.bind(self,cntx)
        except:
            null_seg.bind(self,cntx)
        
class conn_seg(null_seg):
    """
        summary: >
            When two segments are connected via a slash,
            this is a composite.  For each context of the
            parent, it binds the child, and returns each
            context of the child.
    """
    def __str__(self): 
        if self.parent.__class__ == root_seg:  
            return "/%s" % self.child
        return "%s/%s" % (self.parent, self.child)
    def __init__(self,parent,child):
        self.parent = parent
        self.child  = child
    def next(self):
        while 1:
            try:
                return self.child.next()
            except StopIteration:
                cntx = self.parent.next()
                self.child.bind(cntx)
 
    def bind(self,cntx):
        null_seg.bind(self,cntx)
        self.parent.bind(cntx)
        try:
            cntx = self.parent.next()
        except StopIteration: 
            return
        self.child.bind(cntx)


class pred_seg(null_seg):
    def __str__(self): return "%s[%s]" % (self.parent, self.filter)
    def __init__(self,parent,filter):
        self.parent = parent
        self.filter = filter
    def next(self):
        while 1:
            ret = self.parent.next()
            if self.filter.exists(ret):
                return ret
    def bind(self,cntx):
        null_seg.bind(self,cntx)
        self.parent.bind(cntx)

class or_seg(null_seg):
    def __str__(self): return "%s|%s" % (self.lhs,self.rhs)
    def __init__(self,lhs,rhs):
        self.rhs = rhs
        self.lhs = lhs
        self.unq = {}
    def next(self):
        seg = self.lhs
        try:
            nxt = seg.next()
            self.unq[nxt] = nxt
            return nxt
        except StopIteration: pass
        seg = self.rhs
        while 1:
            nxt = seg.next()
            if self.unq.get(nxt,None): 
                continue  
            return nxt
    def bind(self,cntx):
        null_seg.bind(self,cntx)
        self.lhs.bind(cntx)
        self.rhs.bind(cntx)

class scalar:
    def __init__(self,val):  
        self.val = val
    def __str__(self): 
        return str(self.val)
    def value(self): 
        return self.val

class equal_pred: 
    def exists_true(self,cntx): return 1
    def exists_false(self,cntx): return 0
    def exists_scalar(self,cntx):
        self.rhs.bind(cntx)
        try:
            while 1:
                cntx = self.rhs.next()
                if str(cntx.value) == self.lhs:  #TODO: Remove type hack
                     return 1
        except StopIteration: pass
        return 0
    def exists_segment(self,cntx):
        raise NotImplementedError()
    def __init__(self,lhs,rhs):
        if lhs.__class__ == scalar:
            if rhs.__class__ == scalar:
                if rhs.value() == lhs.value():
                    self.exists = self.exists_true
                else:
                    self.exists = self.exists_false
            else:
                self.exists = self.exists_scalar
        else:
            if rhs.__class__ == scalar:
                (lhs,rhs) = (rhs,lhs)
                self.exists = self.exists_scalar
            else:
                self.exists = self.exists_segment
        self.lhs = str(lhs.value())  #TODO: Remove type hack
        self.rhs = rhs
 
matchSegment = re.compile(r"""^(\w+|/|\.|\*|\"|\')""")

def parse_segment(expr):
    """
        Segments occur between the slashes...
    """
    mtch = matchSegment.search(expr)
    if not(mtch): return (None,expr)
    tok = mtch.group(); siz = len(tok)
    if   '/' == tok: return (trav_seg(),expr)
    elif '.' == tok: 
        if len(expr) > 1 and '.' == expr[1]:
            seg = parent_seg()
            siz = 2
        else: 
            seg = self_seg()
    elif '*' == tok: seg = wild_seg()
    elif '"' == tok or "'" == tok:
        (cur,siz) = unquote(expr)
        seg = match_seg(cur)
    else:
        seg = match_seg(tok)
    return (seg,expr[siz:])

matchTerm = re.compile(r"""^(\w+|/|\.|\(|\"|\')""")

def parse_term(expr):
    mtch = matchTerm.search(expr)
    if not(mtch): return (None,expr)
    tok = mtch.group(); siz = len(tok)
    if '/' == tok or '.' == tok:
        return parse(expr)
    if '(' == tok:
        (term,expr) = parse_predicate(expr)
        assert ')' == expr[0]
        return (term,expr[1:])
    elif '"' == tok or "'" == tok:
        (val,siz) = unquote(expr)
    else:
        val = tok; siz = len(tok)
    return (scalar(val),expr[siz:])

def parse_predicate(expr):
    (term,expr) = parse_term(expr)
    if not term: raise SyntaxError("term expected: '%s'" % expr)
    tok = expr[0]
    if '=' == tok:
        (rhs,expr) = parse_term(expr[1:])
        return (equal_pred(term,rhs),expr)
    if '(' == tok:
        raise "No functions allowed... yet!"
    if ']' == tok or ')' == tok:
        if term.__class__ is scalar:
            term = match_seg(str(term))
        return (term,expr)
    raise SyntaxError("ypath: expecting operator '%s'" % expr)

def parse_start(expr):
    """
        Initial checking on the expression, and 
        determine if it is relative or absolute.
    """
    if type(expr) != StringType or len(expr) < 1: 
        raise TypeError("string required: " + repr(expr))
    if '/' == expr[0]:
        ypth = root_seg()
    else:
        ypth = self_seg()
        expr = '/' + expr
    return (ypth,expr)

def parse(expr):
    """
        This the parser entry point, the top level node
        is always a root or self segment.  The self isn't
        strictly necessary, but it keeps things simple.
    """
    (ypth,expr) = parse_start(expr)
    while expr:
        tok = expr[0]
        if '/' == tok:
            (child, expr) = parse_segment(expr[1:])    
            if child: ypth = conn_seg(ypth,child)
            continue
        if '[' == tok:
            (filter, expr) = parse_predicate(expr[1:])
            assert ']' == expr[0]
            expr = expr[1:]
            ypth = pred_seg(ypth,filter)
            continue
        if '|' == tok:
            (rhs, expr) = parse(expr[1:])
            ypth = or_seg(ypth,rhs)
            continue
        if '(' == tok:
            (child,expr) = parse(expr[1:])
            assert ')' == expr[0]
            expr = expr[1:]
            ypth = conn_seg(ypth,child)
            continue
        break
    return (ypth,expr)

class convert_to_value(null_seg):
    def __init__(self,itr):
        self.itr = itr
    def next(self):
        return self.itr.next().value
    def bind(self,cntx):
        self.itr.bind(cntx)

def ypath(expr,target=noTarget,cntx=0):
    (ret,expr) = parse(expr)
    if expr: raise SyntaxError("ypath parse error `%s`" % expr)
    if not cntx: ret = convert_to_value(ret)
    if target is noTarget: return ret
    return ret.apply(target)
