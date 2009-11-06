"""
Python standard logging doesn't super-intelligent and won't expose filehandles,
which we want.  So we're not using it.

Copyright 2009, Red Hat, Inc
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

try:
    import subprocess as sub_process
except:
    import sub_process
import time
import os

ERROR   = "ERROR"
WARNING = "WARNING"
DEBUG   = "DEBUG"
INFO    = "INFO"

class Logger:

   def __init__(self, logfile="/var/log/cobbler/cobbler.log"):
      self.logfile = None

      # Main logfile is append mode, other logfiles not.
      if not os.path.exists(logfile):
         self.logfile = open(logfile, "a")
         sub_process.call("chown apache %s" % logfile, shell=True)
         self.logfile.close()

      try:
         if logfile.find("tasks") != -1:
            self.logfile = open(logfile, "w+")
         else:
            self.logfile = open(logfile, "a")
      except IOError:
          # You likely don't have write access, this logger will just print 
          # things to stdout.
          pass

      

   def warning(self, msg):
      self.__write(WARNING, msg)

   def error(self, msg):
      self.__write(ERROR, msg)

   def debug(self, msg):
      self.__write(DEBUG, msg)

   def info(self, msg):
      self.__write(INFO, msg)

   def flat(self, msg):
      self.__write(None, msg)

   def __write(self, level, msg):

      if level is not None:
         msg = "%s - %s | %s" % (time.asctime(), level, msg)

      if self.logfile is not None:
         self.logfile.write(msg)
         self.logfile.write("\n")
         self.logfile.flush()
      else:
         print(msg)
 
   def handle(self):
      return self.logfile

   def close(self):
      self.logfile.close()


 
