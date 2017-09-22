"""
Generates cobbler.jar, for interfacing with Cobbler XMLRPC from Java-land.
This script writes most of the code so maintaince remains as small as possible.

Michael DeHaan <mdehaan@redhat.com>

May Guido have mercy on your application.
"""

# Force to build from the Python modules in this source checkout,
# not what's installed on the system.
import sys
sys.path.insert(0, "../")

import os.path
import commands

import Cheetah.Template     as Template

import cobbler.item_distro  as cobbler_distro
import cobbler.item_profile as cobbler_profile
import cobbler.item_system  as cobbler_system
import cobbler.item_repo    as cobbler_repo
import cobbler.item_image   as cobbler_image

AUTOGEN_PATH = "src/main/java/org/fedorahosted/cobbler/autogen/"

# FIXME: make this also do Ruby
# FIXME: network object handling is quasi-special

# Define what files we need to template out dynamically
# FIXME: also do this for XMLPC
OBJECT_MAP = [
   [ "Distro",  "Distro",  cobbler_distro.FIELDS  ],
   [ "Profile", "Profile", cobbler_profile.FIELDS ],
   [ "System",  "SystemRecord",  cobbler_system.FIELDS  ],
   [ "Repo",    "Repo",    cobbler_repo.FIELDS    ],
   [ "Image",   "Image",   cobbler_image.FIELDS   ],
]

# Define what variables to expose in all templates
COMMON_VARS = {
   "Rev" : "2.0.X",  # artifact of spacewalk, removable
}

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
   out_data = template.respond()
   fd = open(outfile, "w+")
   fd.write(out_data)
   fd.close()


def templatize_from_vars(objname, jclass, vars):
   """
   Given a source template and some variables, write out the java equivalent.
   """
   assert type(objname) == type("")
   assert type(vars) == type({})
   if objname is not None:
      vars.update({
          "JavaObjectType"      : jclass,
          "CobblerObjectType"   : objname.upper()
      })
   filename1 = "object_base.tmpl"
   filename2 = "%s%s.java" % (AUTOGEN_PATH, jclass)
   commands.getstatusoutput("mkdir -p %s" % AUTOGEN_PATH)
   print "TEMPLATING %s to %s" % (filename1, filename2)
   template_to_disk(filename1, vars, filename2)

def templatize_from_fields(objname, jclass, field_struct):
   """
   Given a source template and a field structure, write out the java code for it.
   """
   assert type(objname) == type("")
   assert type(jclass) == type("")
   assert type(field_struct) == type([])
   vars = { "fields" : field_struct }
   return templatize_from_vars(objname, jclass, vars)

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
       templatize_from_fields(items[0], items[1], items[2])

if __name__ == "__main__":
   """
   For those about to generate java-code from Python, we salute you.
   """
   main()
