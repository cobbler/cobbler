"""
Cobbler's file-based object serializer.
As of 9/2014, this is Cobbler's default serializer and the most stable one.
It uses multiple JSON files in /var/lib/cobbler/collections/distros, profiles, etc

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
import exceptions
import os
import sys
import glob
import simplejson
import yaml

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


def serialize_item(collection, item):
    """
    Save a collection item to file system

    @param Collection collection collection
    @param Item item collection item
    """

    if item.name is None or item.name == "":
        raise exceptions.RuntimeError("name unset for item!")

    # FIXME: Need a better way to support collections/items
    # appending an 's' does not work in all cases
    if collection.collection_type() in ['mgmtclass']:
        filename = "/var/lib/cobbler/collections/%ses/%s" % (collection.collection_type(), item.name)
    else:
        filename = "/var/lib/cobbler/collections/%ss/%s" % (collection.collection_type(), item.name)

    _dict = item.to_dict()

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    filename += ".json"
    _dict = item.to_dict()
    fd = open(filename, "w+")
    data = simplejson.dumps(_dict, encoding="utf-8", sort_keys=sort_keys, indent=indent)
    fd.write(data)

    fd.close()


def serialize_delete(collection, item):
    """
    Delete a collection item from file system

    @param Collection collection collection
    @param Item item collection item
    """

    # FIXME: Need a better way to support collections/items
    # appending an 's' does not work in all cases
    if collection.collection_type() in ['mgmtclass']:
        filename = "/var/lib/cobbler/collections/%ses/%s" % (collection.collection_type(), item.name)
    else:
        filename = "/var/lib/cobbler/collections/%ss/%s" % (collection.collection_type(), item.name)

    filename += ".json"
    if os.path.exists(filename):
        os.remove(filename)


def serialize(collection):
    """
    Save a collection to file system

    @param Collection collection collection
    """

    # do not serialize settings
    ctype = collection.collection_type()
    if ctype != "settings":
        for x in collection:
            serialize_item(collection, x)


def deserialize_raw(collection_type):

    # FIXME: code to load settings file should not be replicated in all
    #   serializer subclasses
    if collection_type == "settings":
        fd = open("/etc/cobbler/settings")
        _dict = yaml.safe_load(fd.read())
        fd.close()

        # include support
        for ival in _dict.get("include", []):
            for ifile in glob.glob(ival):
                with open(ifile, 'r') as fd:
                    _dict.update(yaml.safe_load(fd.read()))

        return _dict
    else:
        results = []
        # FIXME: Need a better way to support collections/items
        # appending an 's' does not work in all cases
        if collection_type in ['mgmtclass']:
            all_files = glob.glob("/var/lib/cobbler/collections/%ses/*" % collection_type)
        else:
            all_files = glob.glob("/var/lib/cobbler/collections/%ss/*" % collection_type)

        for f in all_files:
            fd = open(f)
            json_data = fd.read()
            _dict = simplejson.loads(json_data, encoding='utf-8')
            results.append(_dict)
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
        basekey = f.replace(".json", "")
        if f.endswith(".json"):
            bases[basekey] = f
        else:
            lookup = bases.get(basekey, "")
            if not lookup.endswith(".json"):
                bases[basekey] = f
    return bases.values()


def deserialize(collection, topological=True):
    """
    Load a collection from file system

    @param Collection collection collection
    @param bool topological
    """

    datastruct = deserialize_raw(collection.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(__depth_cmp)
    if type(datastruct) == dict:
        collection.from_dict(datastruct)
    elif type(datastruct) == list:
        collection.from_list(datastruct)


def __depth_cmp(item1, item2):
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)

# EOF
