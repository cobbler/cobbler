"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

import exceptions
import fnmatch
import pprint

from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX
from cobbler.utils import _

# the fields has controls what data elements are part of each object.  To add a new field, just add a new
# entry to the list following some conventions to be described later.  You must also add a method called
# set_$fieldname.  Do not write a method called get_$fieldname, that will not be called.
#
# name | default | subobject default | display name | editable? | tooltip | values ? | type
#
# name -- what the filed should be called.   For the command line, underscores will be replaced with
#         a hyphen programatically, so use underscores to seperate things that are seperate words
#
# default value -- when a new object is created, what is the default value for this field?
#
# subobject default -- this applies ONLY to subprofiles, and is most always set to <<inherit>>.  If this
#                      is not item_profile.py it does not matter.
#
# display name -- how the field shows up in the web application and the "cobbler report" command
#
# editable -- should the field be editable in the CLI and web app?  Almost always yes unless
#                it is an internalism.  Fields that are not editable are "hidden"
#
# tooltip -- the caption to be shown in the web app or in "commandname --help" in the CLI
#
# values -- for fields that have a limited set of valid options and those options are always fixed
#           (such as architecture type), the list of valid options goes in this field.
#
# type -- the type of the field.  Used to determine which HTML form widget is used in the web interface
#
#
# the order in which the fields appear in the web application (for all non-hidden
# fields) is defined in field_ui_info.py. The CLI sorts fields alphabetically.
#
# field_ui_info.py also contains a set of "Groups" that describe what other fields
# are associated with what other fields.  This affects color coding and other
# display hints.  If you add a field, please edit field_ui_info.py carefully to match.
#
# additional:  see field_ui_info.py for some display hints.  By default, in the
# web app, all fields are text fields unless field_ui_info.py lists the field in
# one of those dictionaries.
#
# hidden fields should not be added without just cause, explanations about these are:
#
#   ctime, mtime -- times the object was modified, used internally by cobbler for API purposes
#   uid -- also used for some external API purposes
#   source_repos -- an artifiact of import, this is too complicated to explain on IRC so we just hide it
#                   for RHEL split repos, this is a list of each of them in the install tree, used to generate
#                   repo lines in the automatic installation file to allow installation of x>=RHEL5.  Otherwise unimportant.
#   depth -- used for "cobbler list" to print the tree, makes it easier to load objects from disk also
#   tree_build_time -- loaded from import, this is not useful to many folks so we just hide it.  Avail over API.
#
# so to add new fields
#   (A) understand the above
#   (B) add a field below
#   (C) add a set_fieldname method
#   (D) if field must be viewable/editable via web UI, add a entry in
#       corresponding *_UI_FIELDS_MAPPING dictionary in field_ui_info.py.
#       If field must not be displayed in a text field in web UI, also add
#       an entry in corresponding USES_* list in field_ui_info.py.
#
# in general the set_field_name method should raise exceptions on invalid fields, always.   There are adtl
# validation fields in is_valid to check to see that two seperate fields do not conflict, but in general
# design issues that require this should be avoided forever more, and there are few exceptions.  Cobbler
# must operate as normal with the default value for all fields and not choke on the default values.


class Item(object):
    """
    An Item is a serializable thing that can appear in a Collection
    """

    TYPE_NAME = "generic"

    def __init__(self, collection_mgr, is_subobject=False):
        """
        Constructor.  Requires a back reference to the CollectionManager object.

        NOTE: is_subobject is used for objects that allow inheritance in their trees.  This
        inheritance refers to conceptual inheritance, not Python inheritance.  Objects created
        with is_subobject need to call their set_parent() method immediately after creation
        and pass in a value of an object of the same type.  Currently this is only supported
        for profiles.  Subobjects blend their data with their parent objects and only require
        a valid parent name and a name for themselves, so other required options can be
        gathered from items further up the cobbler tree.

                           distro
                               profile
                                    profile  <-- created with is_subobject=True
                                         system   <-- created as normal

        For consistancy, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.
        """

        self.collection_mgr = collection_mgr
        self.settings = self.collection_mgr._settings
        self.clear(is_subobject)        # reset behavior differs for inheritance cases
        self.parent = ''                # all objects by default are not subobjects
        self.children = {}              # caching for performance reasons, not serialized
        self.log_func = self.collection_mgr.api.log
        self.ctime = 0                  # to be filled in by collection class
        self.mtime = 0                  # to be filled in by collection class
        self.uid = ""                   # to be filled in by collection class
        self.kernel_options = None
        self.kernel_options_post = None
        self.autoinstall_meta = None
        self.fetchable_files = None
        self.boot_files = None
        self.template_files = None
        self.name = None
        self.last_cached_mtime = 0
        self.cached_dict = ""

    def __find_compare(self, from_search, from_obj):

        if isinstance(from_obj, basestring):
            # FIXME: fnmatch is only used for string to string comparisions
            # which should cover most major usage, if not, this deserves fixing
            if fnmatch.fnmatch(from_obj.lower(), from_search.lower()):
                return True
            else:
                return False
        else:
            if isinstance(from_search, basestring):
                if isinstance(from_obj, list):
                    from_search = utils.input_string_or_list(from_search)
                    for x in from_search:
                        if x not in from_obj:
                            return False
                    return True
                if isinstance(from_obj, dict):
                    (junk, from_search) = utils.input_string_or_dict(from_search, allow_multiples=True)
                    for x in from_search.keys():
                        y = from_search[x]
                        if x not in from_obj:
                            return False
                        if not (y == from_obj[x]):
                            return False
                    return True
                if isinstance(from_obj, bool):
                    if from_search.lower() in ["true", "1", "y", "yes"]:
                        inp = True
                    else:
                        inp = False
                    if inp == from_obj:
                        return True
                    return False

            raise CX(_("find cannot compare type: %s") % type(from_obj))

    def get_fields(self):
        """
        Get serializable fields
        Must be defined in any subclass
        """
        raise exceptions.NotImplementedError()

    def clear(self, is_subobject=False):
        """
        Reset this object.
        """
        utils.clear_from_fields(self, self.get_fields(), is_subobject=is_subobject)

    def make_clone(self):
        """
        Must be defined in any subclass
        """
        raise exceptions.NotImplementedError

    def from_dict(self, _dict):
        """
        Modify this object to take on values in seed_data
        """
        utils.from_dict_from_fields(self, _dict, self.get_fields())

    def to_dict(self):
        return utils.to_dict_from_fields(self, self.get_fields())

    def to_string(self):
        return utils.to_string_from_fields(self, self.get_fields())

    def get_setter_methods(self):
        return utils.get_setter_methods_from_fields(self, self.get_fields())

    def set_uid(self, uid):
        self.uid = uid

    def get_children(self, sorted=True):
        """
        Get direct children of this object.
        """
        keys = self.children.keys()
        if sorted:
            keys.sort()
        results = []
        for k in keys:
            results.append(self.children[k])
        return results

    def get_descendants(self, sort=False):
        """
        Get objects that depend on this object, i.e. those that
        would be affected by a cascading delete, etc.
        With sort=True the list will be a walk of the tree,
        e.g., distro -> [profile, sys, sys, profile, sys, sys]
        """
        results = []
        kids = self.get_children(sorted=sort)
        if not sort:
            results.extend(kids)
        for kid in kids:
            if sort:
                results.append(kid)
            grandkids = kid.get_descendants(sort=sort)
            results.extend(grandkids)
        return results

    def get_parent(self):
        """
        For objects with a tree relationship, what's the parent object?
        """
        return None

    def get_conceptual_parent(self):
        """
        The parent may just be a superclass for something like a
        subprofile.  Get the first parent of a different type.
        """
        mtype = type(self)
        parent = self.get_parent()
        while parent is not None:
            ptype = type(parent)
            if mtype != ptype:
                self.conceptual_parent = parent
                return parent
            parent = parent.get_parent()
        return None

    def set_name(self, name):
        """
        Set the objects name.

        @param: str name (object name string)
        @returns: True or CX
        """
        self.name = validate.object_name(name, self.parent)

    def set_comment(self, comment):
        if comment is None:
            comment = ""
        self.comment = comment

    def set_owners(self, data):
        """
        The owners field is a comment unless using an authz module that pays attention to it,
        like authz_ownership, which ships with Cobbler but is off by default.
        """
        self.owners = utils.input_string_or_list(data)

    def set_kernel_options(self, options):
        """
        Kernel options are a space delimited list,
        like 'a=b c=d e=f g h i=j' or a dict.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise CX(_("invalid kernel options"))
        else:
            self.kernel_options = value

    def set_kernel_options_post(self, options):
        """
        Post kernel options are a space delimited list,
        like 'a=b c=d e=f g h i=j' or a dict.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            raise CX(_("invalid post kernel options"))
        else:
            self.kernel_options_post = value

    def set_autoinstall_meta(self, options):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system
        to preprocess automatic installation template files
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=True)
        if not success:
            return False
        else:
            self.autoinstall_meta = value

    def set_mgmt_classes(self, mgmt_classes):
        """
        Assigns a list of configuration management classes that can be assigned
        to any object, such as those used by Puppet's external_nodes feature.
        """
        mgmt_classes_split = utils.input_string_or_list(mgmt_classes)
        self.mgmt_classes = utils.input_string_or_list(mgmt_classes_split)

    def set_mgmt_parameters(self, mgmt_parameters):
        """
        A YAML string which can be assigned to any object, this is used by
        Puppet's external_nodes feature.
        """
        if mgmt_parameters == "<<inherit>>":
            self.mgmt_parameters = mgmt_parameters
        else:
            import yaml
            data = yaml.safe_load(mgmt_parameters)
            if type(data) is not dict:
                raise CX(_("Input YAML in Puppet Parameter field must evaluate to a dictionary."))
            self.mgmt_parameters = data

    def set_template_files(self, template_files):
        """
        A comma seperated list of source=destination templates
        that should be generated during a sync.
        """
        (success, value) = utils.input_string_or_dict(template_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.template_files = value

    def set_boot_files(self, boot_files):
        """
        A comma seperated list of req_name=source_file_path
        that should be fetchable via tftp
        """
        (success, value) = utils.input_string_or_dict(boot_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.boot_files = value

    def set_fetchable_files(self, fetchable_files):
        """
        A comma seperated list of virt_name=path_to_template
        that should be fetchable via tftp or a webserver
        """
        (success, value) = utils.input_string_or_dict(fetchable_files, allow_multiples=False)
        if not success:
            return False
        else:
            self.fetchable_files = value

    def sort_key(self, sort_fields=[]):
        data = self.to_dict()
        return [data.get(x, "") for x in sort_fields]

    def find_match(self, kwargs, no_errors=False):
        # used by find() method in collection.py
        data = self.to_dict()
        for (key, value) in kwargs.iteritems():
            # Allow ~ to negate the compare
            if value is not None and value.startswith("~"):
                res = not self.find_match_single_key(data, key, value[1:], no_errors)
            else:
                res = self.find_match_single_key(data, key, value, no_errors)
            if not res:
                return False

        return True

    def find_match_single_key(self, data, key, value, no_errors=False):
        # special case for systems
        key_found_already = False
        if "interfaces" in data:
            if key in ["mac_address", "ip_address", "netmask", "virt_bridge",
                       "dhcp_tag", "dns_name", "static_routes", "interface_type",
                       "interface_master", "bonding_opts", "bridge_opts"]:
                key_found_already = True
                for (name, interface) in data["interfaces"].iteritems():
                    if value is not None and key in interface:
                        if self.__find_compare(interface[key], value):
                            return True

        if key not in data:
            if not key_found_already:
                if not no_errors:
                    # FIXME: removed for 2.0 code, shouldn't cause any problems to not have an exception here?
                    # raise CX(_("searching for field that does not exist: %s" % key))
                    return False
            else:
                if value is not None:       # FIXME: new?
                    return False

        if value is None:
            return True
        else:
            return self.__find_compare(value, data[key])

    def dump_vars(self, data, format=True):
        raw = utils.blender(self.collection_mgr.api, False, self)
        if format:
            return pprint.pformat(raw)
        else:
            return raw

    def set_depth(self, depth):
        self.depth = depth

    def set_ctime(self, ctime):
        self.ctime = ctime

    def set_mtime(self, mtime):
        self.mtime = mtime

    def set_parent(self, parent):
        self.parent = parent

    def check_if_valid(self):
        """
        Raise exceptions if the object state is inconsistent
        """
        if self.name is None or self.name == "":
            raise CX("Name is required")

# EOF
