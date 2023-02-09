#!/usr/bin/python3

import argparse
import os
import glob
import simplejson
import subprocess

import cobbler.api as capi

from cobbler.settings.migrations.V3_3_0 import backup_dir


COBBLER_COLLECTION_PATH = "/var/lib/cobbler/collections/"
COBBLER_TEMPLATES_PATH = "/var/lib/cobbler/templates"

OLD_COBBLER_TEMPLATES_PATH = "/var/lib/cobbler/kickstarts"
OLD_RHN_TEMPLATES_PATH = "/var/lib/rhn/kickstarts"
OLD_AUTOINSTALL_TEMPLATES_PATH = "/var/lib/cobbler/autoinstall_templates"

TEMPLATES_PATHS = [
    COBBLER_TEMPLATES_PATH,
    OLD_COBBLER_TEMPLATES_PATH,
    OLD_RHN_TEMPLATES_PATH,
    OLD_AUTOINSTALL_TEMPLATES_PATH,
]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--noapi",
    action="store_true",
    help="Do not try to connect to Cobbler API",
    default=False,
)
parser.add_argument(
    "--noconfigs",
    action="store_true",
    help="Do not use use old config.d collections dir schema",
    default=False,
)
parser.add_argument(
    "-c",
    "--collections-path",
    help="Path to Cobbler collections to migrate",
    default="/var/lib/cobbler/config/",
)
parser.add_argument(
    "--only-fix-autoinstall",
    action="store_true",
    help="Run migration of collections only for autoinstall attribute (Implies: --noapi --noconfigs)",
    default=False,
)

args = parser.parse_args()
if args.only_fix_autoinstall:
    args.noapi = True
    args.noconfigs = True


def serialize_item(collection, item):
    """
    Save a collection item to file system

    @param collection name
    @param item dictionary
    """

    filename = os.path.join(
        COBBLER_COLLECTION_PATH, "%s/%s" % (collection, item["name"])
    )

    if not args.noapi and capi.CobblerAPI().settings().serializer_pretty_json:
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

    all_files = glob.glob(
        os.path.join(args.collections_path, "%s/*" % collection_types)
    )

    for f in all_files:
        fd = open(f)
        json_data = fd.read()
        _dict = simplejson.loads(json_data, encoding="utf-8")
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
        value = value.replace("/ks_mirror/", "/distro_mirror/")
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


def _fix_autoinstall(path):
    # Absolute path, we need to calculate the relative path against its template dir
    # Examples seen:
    #   - "" (empty string)
    #   - <<inherit>>
    #   - /upload/something.cfg
    #   - upload/something.cfg
    #   - /var/lib/rhn/kickstarts/upload/something.cfg
    #   - /var/lib/cobbler/kickstarts/upload/something.cfg
    #   - /var/lib/cobbler/autoinstall_templates/default.ks
    #

    # Empty string found. Nothing to do.
    if not path:
        return path

    # Absolute path found
    if os.path.isabs(path):
        for tp in TEMPLATES_PATHS:
            if path.startswith(tp):
                # Migrate absolute path to relative path.
                # Example: /var/lib/cobbler/kickstarts/upload/something.cfg -> upload/something.cfg
                new_path = os.path.relpath(path, tp)
                print(
                    "       * Migrate absolute autoinstall path: {} to {}".format(
                        path, new_path
                    )
                )
                return new_path

            # Wrong absolute path found - maybe this is actually a relative path
            # where we need to remove the initial slash.
            # We check first if file would exist on the template paths to validate the migration
            # Example: /upload/something.cfg -> upload/something.cfg
            elif os.path.isfile(os.path.join(tp, path.lstrip("/"))):
                return path.lstrip("/")

        # Absolute path outside of expected template paths.
        # We do not migrate the content and warn user.
        print(
            "       * ERROR: Migrate absolute autoinstall path: {} was not possible. "
            "Cannot find file.".format(path)
        )
        print(
            "       * Please fix 'autoinstall' attribute for this collection manually."
        )
        return path

    # Here the value is already relative path. It might be wrong and we need to fix it
    else:
        for tp in TEMPLATES_PATHS:
            if os.path.isfile(os.path.join(tp, path)):
                # The value is correct, nothing to do
                return path

        # Here, it means the file is not found, probably wrong and we need to
        # figure out where the file is really located.
        # In case we find a collision, so different possible candidates
        # then we raise an error and do nothing.
        items_found = []
        new_path = None
        for tp in TEMPLATES_PATHS:
            for curdir, subdirs, files in os.walk(tp):
                if os.path.basename(path) in files:
                    # We fix the wrong value and set the correct one
                    # in case there is not collisions
                    # Example: something.cfg -> upload/something.cfg
                    # Example: foobar/something.cfg -> upload/something.cfg
                    items_found.append(os.path.join(curdir, os.path.basename(path)))
                    if not new_path:
                        new_path = os.path.relpath(
                            os.path.join(curdir, os.path.basename(path)), tp
                        )

        # Collisions in names -> raise error and do nothing
        if len(items_found) > 1:
            print(
                "       * ERROR: Migrate relative autoinstall: {} was not possible as"
                "there are multiple candidates for this file.".format(path)
            )
            for item in items_found:
                print("       -- {}".format(item))
            print(
                "       * Please fix 'autoinstall' attribute manually for this collection. "
                "Put a path which is relative to /var/lib/cobbler/templates"
            )
            return path
        # Template file found and no collisions -> return the fixed value
        elif new_path:
            print(
                "       * Fixed wrong value for autoinstall path: {} to {}".format(
                    path, new_path
                )
            )
            return new_path

        # At this point, we didn't find the template
        # so we return same value and do not migrate it
        if path != "<<inherit>>":
            print(
                "       * ERROR: Migrate relative autoinstall: {} was not possible. "
                "Cannot find file.".format(path)
            )
            print(
                "       * Please fix 'autoinstall' attribute for this collection manually."
            )
        return path


# Keys to transform - use new key name if renamed
transform = {
    "autoinstall": _fix_autoinstall,
}

# Create a backup of stored collections before performing migration
print("Creating a backup of %s" % args.collections_path)
backup_dir(args.collections_path)

# Convert the old collections to new collections
for old_type in [
    "distros.d",
    "files.d",
    "images.d",
    "mgmtclasses.d",
    "packages.d",
    "profiles.d",
    "repos.d",
    "systems.d",
]:
    new_type = old_type[:-2]

    # Bypass old collection.d folder schema
    if args.noconfigs:
        old_type = new_type

    # Load old files
    old_collection = deserialize_raw_old(old_type)
    print("Processing %s:" % old_type)

    for old_item in old_collection:
        print("    Processing %s" % old_item["name"])
        new_item = {}
        for key in old_item:
            if not args.only_fix_autoinstall:
                if key in remove:
                    continue
                if key in rename:
                    new_item[rename[key]] = transform_key(rename[key], old_item[key])
                    continue
            new_item[key] = transform_key(key, old_item[key])

        if not args.only_fix_autoinstall:
            if new_type in add:
                new_item.update(add[new_type])

            # Switch "virtio26" and "generic26" OS version to "generic" distro breed
            if new_item.get("os_version") in ["generic26", "virtio26"]:
                new_item["breed"] = "generic"

        serialize_item(new_type, new_item)

path_rename = [
    (OLD_AUTOINSTALL_TEMPLATES_PATH, COBBLER_TEMPLATES_PATH),
    (OLD_RHN_TEMPLATES_PATH, COBBLER_TEMPLATES_PATH),
    (OLD_COBBLER_TEMPLATES_PATH, COBBLER_TEMPLATES_PATH),
    ("/var/www/cobbler/ks_mirror", "/var/www/cobbler/distro_mirror"),
]

# Copy paths
for old_path, new_path in path_rename:
    if os.path.isdir(old_path):
        subprocess.run("cp -al %s/* %s/" % (old_path, new_path), shell=True)
