# Michael DeHaan <mdehaan@redhat.com>

import syck  # PySyck 0.61 or greater, not syck-python 0.55
import errno
import os

import utils

def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    Will create intermediate paths if it can.  Returns True on Success,
    False on permission errors.
    """
    filename = obj.filename()
    try:
        fd = open(filename,"w+")
    except IOError, ioe:
        basename = os.path.basename(filename)
        if not os.path.exists(basename):
           try:
               os.makedirs(basename)
           except:
               raise CobblerException("need_perms", basename)
               return False
        try:
           fd = open(filename,"w+")
        except:
           raise CobblerException("need_perms", filename)
           return False
    datastruct = obj.to_datastruct()
    encoded = syck.dump(datastruct)
    fd.write(encoded)
    fd.close()
    return True

def deserialize(obj):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  Returns True assuming
    files could be read and contained decent YAML.  Otherwise returns
    False.
    """
    filename = obj.filename()
    try:
        fd = open(filename,"r")
    except IOError, ioe:
        # if it doesn't exist, that's cool -- it's not a bug until we try
        # to write the file and can't create it.
        if not os.path.exists(filename):
            return True
        else:
            raise CobblerException("need_perms",obj.filename())
    data = fd.read()
    datastruct = syck.load(data)
    if type(datastruct) == str:
        # PySyck returns strings when it chokes on data
        # it doesn't really throw exceptions
        raise CobblerException("parse_error",filename)
    fd.close()
    obj.from_datastruct(datastruct)
    return True
 

