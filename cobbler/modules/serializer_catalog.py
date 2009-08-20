"""
Serializer code for cobbler.
As of 8/2009, this is the "best" serializer option.
It uses multiple files in /var/lib/cobbler/config/distros.d, profiles.d, etc
And JSON, when possible, and YAML, when not.
It is particularly fast, especially when using JSON.   YAML, not so much.
It also knows how to upgrade the old "single file" configs to .d versions.

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import distutils.sysconfig
import os
import sys
import glob
import traceback
import yaml # PyYAML
import simplejson
import exceptions

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

from utils import _
import utils
from cexceptions import *
import os

def can_use_json():
    version = sys.version[:3]
    version = float(version)
    return (version > 2.3)

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "serializer"

def serialize_item(obj, item):

    if item.name is None or item.name == "":
       raise exceptions.RuntimeError("name unset for object!")

    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    datastruct = item.to_datastruct()

    jsonable = can_use_json()

    if jsonable:

        # avoid using JSON on python 2.3 where we can encounter
        # unicode problems with simplejson pre 2.0

        if os.path.exists(filename):
            print "upgrading yaml file to json: %s" % filename
            os.remove(filename)
        filename = filename + ".json"
        datastruct = item.to_datastruct()
        fd = open(filename,"w+")
        data = simplejson.dumps(datastruct, encoding="utf-8")
        #data = data.encode('utf-8')
        fd.write(data)

    else:

        if os.path.exists(filename + ".json"):
            print "downgrading json file back to yaml: %s" % filename
            os.remove(filename + ".json")
        datastruct = item.to_datastruct()
        fd = open(filename,"w+")
        data = yaml.dump(datastruct)
        fd.write(data)

    fd.close()
    return True

def serialize_delete(obj, item):
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(),item.name)
    filename2 = filename + ".json"
    if os.path.exists(filename):
        os.remove(filename)
    if os.path.exists(filename2):
        os.remove(filename2)
    return True

def deserialize_item_raw(collection_type, item_name):
    # this new fn is not really implemented performantly in this module.
    # yet.
    filename = "/var/lib/cobbler/config/%ss.d/%s" % (collection_type,item_name)
    filename2 = filename + ".json"
    if os.path.exists(filename): 
        fd = open(filename)
        data = fd.read()
        return yaml.load(data)
    elif os.path.exists(filename2):
        fd = open(filename2)
        data = fd.read()
        return simplejson.loads(data, encoding="utf-8")
    else: 
        return None  


def serialize(obj):
    """
    Save an object to disk.  Object must "implement" Serializable.
    FIXME: Return False on access/permission errors.
    This should NOT be used by API if serialize_item is available.
    """
    ctype = obj.collection_type()
    if ctype == "settings":
        return True
    for x in obj:
        serialize_item(obj,x)
    return True

def deserialize_raw(collection_type):
    old_filename = "/var/lib/cobbler/%ss" % collection_type
    if collection_type == "settings":
         fd = open("/etc/cobbler/settings")
         datastruct = yaml.load(fd.read())
         fd.close()
         return datastruct
    elif os.path.exists(old_filename):
         # for use in migration from serializer_yaml to serializer_catalog (yaml/json)
         fd = open(old_filename)
         datastruct = yaml.load(fd.read())
         fd.close()
         return datastruct
    else:
         results = []
         all_files = glob.glob("/var/lib/cobbler/config/%ss.d/*" % collection_type)
         all_files = filter_upgrade_duplicates(all_files)
         for f in all_files:
             fd = open(f)
             ydata = fd.read()
             # ydata = ydata.decode()
             if f.endswith(".json"):
                 datastruct = simplejson.loads(ydata, encoding='utf-8')
             else:
                 datastruct = yaml.load(ydata)
             results.append(datastruct)
             fd.close()
         return results    

def filter_upgrade_duplicates(file_list):
    """
    In a set of files, some ending with .json, some not, return
    the list of files with the .json ones taking priority over
    the ones that are not.
    """
    bases = {}
    for f in file_list:
       basekey = f.replace(".json","")
       if f.endswith(".json"):
           bases[basekey] = f
       else:
           lookup = bases.get(basekey,"")
           if not lookup.endswith(".json"):
              bases[basekey] = f
    return bases.values()

def deserialize(obj,topological=True):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.  
    """
    old_filename = "/var/lib/cobbler/%ss" % obj.collection_type()
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
       datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    if os.path.exists(old_filename):
       # we loaded it in from the old filename, so now migrate to new fmt
       sys.stderr.write("auto-removing old config format: %s\n" % old_filename)
       serialize(obj)
       os.remove(old_filename)
    return True

def __depth_cmp(item1, item2):
    d1 = item1.get("depth",1)
    d2 = item2.get("depth",1)
    return cmp(d1,d2)

if __name__ == "__main__":
    print deserialize_item_raw("distro","D1")

