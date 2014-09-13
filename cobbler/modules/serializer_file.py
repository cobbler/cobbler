"""
Cobbler's file-based object serializer.
As of 9/2014, this is Cobbler's default serializer and the most stable one.
It uses multiple JSON files in /var/lib/cobbler/config/distros.d, profiles.d, etc

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import yaml
import simplejson
import exceptions

plib = distutils.sysconfig.get_python_lib()
mod_path = "%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cobbler.api as capi



def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "serializer"


def what():
    """
    Module identification function
    """
    return "serializer/file"


def serialize_item(obj, item):

    if item.name is None or item.name == "":
        raise exceptions.RuntimeError("name unset for object!")

    # FIXME: Need a better way to support collections/items
    # appending an 's' does not work in all cases
    if obj.collection_type() in ['mgmtclass']:
        filename = "/var/lib/cobbler/config/%ses.d/%s" % (obj.collection_type(), item.name)
    else:
        filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(), item.name)

    datastruct = item.to_datastruct()

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    filename += ".json"
    datastruct = item.to_datastruct()
    fd = open(filename, "w+")
    data = simplejson.dumps(datastruct, encoding="utf-8", sort_keys=sort_keys, indent=indent)
    fd.write(data)

    fd.close()
    return True


def serialize_delete(obj, item):
    # FIXME: Need a better way to support collections/items
    # appending an 's' does not work in all cases
    if obj.collection_type() in ['mgmtclass']:
        filename = "/var/lib/cobbler/config/%ses.d/%s" % (obj.collection_type(), item.name)
    else:
        filename = "/var/lib/cobbler/config/%ss.d/%s" % (obj.collection_type(), item.name)

    filename += ".json"
    if os.path.exists(filename):
        os.remove(filename)
    return True


def deserialize_item_raw(collection_type, item_name):
    # this new fn is not really implemented performantly in this module.
    # yet.

    # FIXME: Need a better way to support collections/items
    # appending an 's' does not work in all cases
    if item_name in ['mgmtclass']:
        filename = "/var/lib/cobbler/config/%ses.d/%s" % (collection_type(), item_name)
    else:
        filename = "/var/lib/cobbler/config/%ss.d/%s" % (collection_type, item_name)

    filename += ".json"
    if os.path.exists(filename):
        fd = open(filename)
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
        serialize_item(obj, x)
    return True


def deserialize_raw(collection_type):
    if collection_type == "settings":
        fd = open("/etc/cobbler/settings")
        datastruct = yaml.safe_load(fd.read())
        fd.close()

        # include support
        for ival in datastruct.get("include", []):
            for ifile in glob.glob(ival):
                with open(ifile, 'r') as fd:
                    datastruct.update(yaml.safe_load(fd.read()))

        return datastruct
    else:
        results = []
        # FIXME: Need a better way to support collections/items
        # appending an 's' does not work in all cases
        if collection_type in ['mgmtclass']:
            all_files = glob.glob("/var/lib/cobbler/config/%ses.d/*" % collection_type)
        else:
            all_files = glob.glob("/var/lib/cobbler/config/%ss.d/*" % collection_type)

        for f in all_files:
            fd = open(f)
            json_data = fd.read()
            datastruct = simplejson.loads(json_data, encoding='utf-8')
            results.append(datastruct)
            fd.close()
        return results


def deserialize(obj, topological=True):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.
    """
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    return True


def __depth_cmp(item1, item2):
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)


if __name__ == "__main__":
    print deserialize_item_raw("distro", "D1")
