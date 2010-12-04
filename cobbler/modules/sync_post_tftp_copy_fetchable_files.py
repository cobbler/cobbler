import distutils.sysconfig
import sys
import os.path
import shutil
import traceback
import cexceptions
import cobbler.templar as templar
import cobbler.module_loader as module_loader
import cobbler.utils as utils

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

def register():
   # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
   # the return of this method indicates the trigger type
   return "/var/lib/cobbler/triggers/sync/post/*"

def run(api,args,logger):
   settings = api.settings()

   for distro in api.distros():
      # collapse the object down to a rendered datastructure
      # the second argument set to false means we don't collapse hashes/arrays into a flat string
      target = utils.blender(api, False, distro)

      # Create metadata for the templar function
      # Right now, just using img_path, but adding more
      # cobbler variables here would probably be good
      metadata = {}
      metadata["img_path"] = os.path.join("/tftpboot/images",distro.name)

      # Create the templar instance
      templater = templar.Templar()

      # Loop through the hash of fetchable files,
      # executing a cp for each one
      for file in target["fetchable_files"].keys():
        file_dst = templater.render(file,metadata,None)
        try:
          shutil.copyfile(target["fetchable_files"][file], file_dst)
          api.log("copied file %s to %s for %s" % (target["fetchable_files"][file],file_dst,distro.name))
        except:
          logger.error("failed to copy file %s to %s for %s" % (target["fetchable_files"][file],file_dst,distro.name))
          return 1

   return 0
