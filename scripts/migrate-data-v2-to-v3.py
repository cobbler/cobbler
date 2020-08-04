#!/usr/bin/python3

import os
import glob
import simplejson
import subprocess

import cobbler.api as capi


def serialize_item(collection, item):
    """
    Save a collection item to file system

    @param collection name
    @param item dictionary
    """

    filename = "/var/lib/cobbler/collections/%s/%s" % (collection, item['name'])

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    filename += ".json"
    fd = open(filename, "w+")
    data = simplejson.dumps(item, encoding="utf-8", sort_keys=sort_keys, indent=indent)
    fd.write(data)

    fd.close()

def deserialize_raw_old(collection_types):

    results = []

    all_files = glob.glob("/var/lib/cobbler/config/%s/*" % collection_types)

    for f in all_files:
        fd = open(f)
        json_data = fd.read()
        _dict = simplejson.loads(json_data, encoding='utf-8')
        results.append(_dict)
        fd.close()
    return results


def substitute_paths(value):
    if isinstance(value, list):
        new_value = []
        for item in value:
            new_value.append(substitute_paths(item))
        value = new_value
    elif isinstance(value, str):
        value = value.replace('/ks_mirror/','/distro_mirror/')
    return value

def transform_key(key, value):
    if key in transform:
        ret_value = transform[key](value)
    else:
        ret_value = value

    return substitute_paths(ret_value)

# Keys to add to various collections
add = {
  "distros": {
    "boot_loader": "grub",
  },
  "profiles": {
    "next_server": "<<inherit>>",
  },
  "systems": {
    "boot_loader": "<<inherit>>",
    "next_server": "<<inherit>>",
    "power_identity_file": "",
    "power_options": "",
    "serial_baud_rate": "",
    "serial_device": "",
  },
}

# Keys to remove
remove = [
  "ldap_enabled",
  "ldap_type",
  "monit_enabled",
  "redhat_management_server",
  "template_remote_kickstarts",
]

# Keys to rename
rename = {
  "kickstart": "autoinstall",
  "ks_meta": "autoinstall_meta",
}

# Keys to transform - use new key name if renamed
transform = {
  "autoinstall": os.path.basename,
}

# Convert the old collections to new collections
for old_type in ['distros.d','files.d','images.d','mgmtclasses.d','packages.d','profiles.d','repos.d','systems.d']:
    new_type = old_type[:-2]
    # Load old files
    old_collection = deserialize_raw_old(old_type)
    print("Processing %s:" % old_type)

    for old_item in old_collection:
        print("    Processing %s" % old_item['name'])
        new_item = {}
        for key in old_item:
            if key in remove:
                continue
            if key in rename:
                new_item[rename[key]] = transform_key(rename[key], old_item[key])
                continue
            new_item[key] = transform_key(key, old_item[key])

        if new_type in add:
            new_item.update(add[new_type])

        serialize_item(new_type, new_item)

path_rename = [
  ("/var/lib/cobbler/kickstarts", "/var/lib/cobbler/templates"),
  ("/var/www/cobbler/ks_mirror", "/var/www/cobbler/distro_mirror"),
]

# Copy paths
for old_path, new_path in path_rename:
    if os.path.isdir(old_path):
        subprocess.run(["cp", "-al", "%s/*" % old_path, "%s/" % new_path], shell=True)
