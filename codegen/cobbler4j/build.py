"""
Generates cobbler.jar, for interfacing with Cobbler XMLRPC from Java-land.
This script writes most of the code so maintaince remains as small as possible.

Michael DeHaan <mdehaan@redhat.com>

May Guido have mercy on your application.
"""

import Cheetah.Template     as Template
import cobbler.item_distro  as cobbler_distro
import cobbler.item_profile as cobbler_profile
import cobbler.item_system  as cobbler_system
import cobbler.item_repo    as cobbler_repo
import cobbler.item_image   as cobbler_image
import os.path

# FIXME: make this also do Ruby
# FIXME: network object handling is quasi-special

# Define what files we need to template out dynamically
# FIXME: also do this for XMLPC
OBJECT_MAP = [
   [ "Distro.tmpl",  cobbler_distro.FIELDS ],
   [ "Profile.tmpl", cobbler_profile.FIELDS ],
   [ "System.tmpl",  cobbler_system.FIELDS ],
   [ "Repo.tmpl",    cobbler_repo.FIELDS ],
   [ "Image.tmpl",   cobbler_image.FIELDS ],
]

# Define what variables to expose in all templates
COMMON_VARS = {
   "Rev" : "2.0.X",  # artifact of spacewalk, removable
}

# Define what a java setter looks like
# NOTE: python templating here, not Cheetah
SET_FUNCTION = """
    /**
     * %{tooltip}s
     * @param %{var_name}s input value
     */

    public void set%{up_var_name}s(str %{var_name}s) {
        modify(%{field_name}, %{var_name});
    }
"""

# Define what a java getter looks like
# NOTE: python templating here, not Cheetah
GET_FUNCTION = """
   FIXME
"""

def camelize(field_name):
   """
   Given a string "something_like_this", return "somethingLikeThis"
   """
   assert type(field_name) == type("")
   result = ""
   tokens = field_name.split("_","")
   for (ct, val) in enumerate(tokens):
      if ct == 0:
         result = val
      else:
         result += val.title()
   return tokens

def get_java_setter(field_name, tooltip):
   """
   For a given field name, return the java code for setting that field.
   """
   print tooltip
   assert type(field_name) == type("")
   assert type(tooltip) == type("")
   camel = camelize(field_name)
   return SET_FUNCTION % {
       "var_name"    : camel,
       "up_var_name" : camel.title(),
       "field_name"  : field_name,
       "tooltip"     : tool_tip
   }

def get_setters_from_fields(field_struct):
   """
   Given a list of fields, return the code for all the setters.
   """
   assert type(field_struct) == type([])
   results = ""
   for field in field_struct:
       (field_name, default, subobject_default, tooltip, is_hidden, is_editable, values) = field

       if is_editable and not is_hidden:
          setter = get_java_setter(field_name, tooltip)
          results += setter
   return results 

def get_getters_from_fields(field_struct):
   """
   Given a list of fields, return the code for all the getters.
   """
   # FIXME: implement this
   assert type(field_struct) == type([])
   return ""

def get_vars_from_fields(field_struct):
   """
   Given a cobbler field structure, return the template data we need to template out a given object.
   """
   assert type(field_struct) == type([])
   return {
       "getters" : get_getters_from_fields(field_struct),
       "setters" : get_setters_from_fields(field_struct)
   }

def main():
   """
   Kick out the Jams.  I mean, the jars.  Kick em out.
   """
   generate_main_classes()
   generate_object_classes()

def slurp(filename):
   """
   Return the contents of a file.
   """
   assert type(filename) == type("")
   assert os.path.exists(filename)
   fd = open(filename)
   data = fd.read()
   fd.close()
   return data

def template_to_disk(infile, vars, outfile):
   """
   Given a cheetah template and a dict of variables, write the templatized version to disk.
   """
   assert type(infile) == type("")
   print infile
   assert os.path.exists(infile)
   assert type(vars) == type({})
   assert type(outfile) == type("")
   source_data = slurp(infile)
   vars.update(COMMON_VARS)
   template = Template.Template(
       source=source_data, 
       errorCatcher="Echo", 
       searchList=[vars]
   )
   out_data = str(template)
   fd = open(outfile, "w+")
   fd.write(out_data)
   fd.close()


def templatize_from_vars(filename, vars):
   """
   Given a source template and some variables, write out the java equivalent.
   """
   assert type(filename) == type("")
   assert type(vars) == type({})
   filename2 = filename.replace(".tmpl",".java")
   template_to_disk(filename, vars, filename2)

def templatize_from_fields(filename, field_struct):
   """
   Given a source template and a field structure, write out the java code for it.
   """
   assert type(filename) == type("")
   assert type(field_struct) == type([])
   vars = get_vars_from_fields(field_struct)
   return templatize_from_vars(filename, vars)

def generate_main_classes():
   """
   For classes that are not cobbler-object-tree related, template out the corresponding Java code.
   """
   pass

def generate_object_classes():
   """
   For classes that ARE cobbler-object tree related, template out the corresponding Java code.
   """
   for items in OBJECT_MAP:
       templatize_from_fields(items[0], items[1])

if __name__ == "__main__":
   """
   For those about to generate java-code from Python, we salute you.
   """
   main()
