import new
import re

class DefaultResolver:
    def resolveType(self, data, typestring):
        match = re.match('!!(.*?)\.(.*)', typestring)
        if not match:
            raise "Invalid private type specifier"
        (modname, classname) = match.groups()
        return makeClass(modname, classname, data)

def makeClass(module, classname, dict):
    exec('import %s' % (module))
    klass = eval('%s.%s' % (module, classname))
    obj = new.instance(klass) 
    if hasMethod(obj, 'from_yaml'):
        return obj.from_yaml(dict)
    obj.__dict__ = dict
    return obj

def hasMethod(object, method_name):
    try:    
        klass = object.__class__
    except:
        return 0
    if not hasattr(klass, method_name):
        return 0
    method = getattr(klass, method_name)
    if not callable(method):
        return 0
    return 1

def isDictionary(data):
    return isinstance(data, dict)

try:
    isDictionary({})
except:
    def isDictionary(data): return type(data) == type({}) # XXX python 2.1
    
if __name__ == '__main__':
    print isDictionary({'foo': 'bar'})
    try:
        print isDictionary(dict())
        from ordered_dict import OrderedDict
        print isDictionary(OrderedDict())
    except:
        pass
