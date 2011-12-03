#!/usr/bin/python

"""
Quick test script to read the cobbler configurations and touch and mkdir -p any files
neccessary to trivially debug another user's configuration even if the distros don't exist yet
Intended for basic support questions only. Not for production use.

Copyright 2008-2009, Red Hat, Inc and Others
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

import glob
import cobbler.yaml as camel
import os.path
import os

for f in glob.glob("/var/lib/cobbler/config/distros.d/*"):

   fh = open(f)
   data = fh.read()
   fh.close()

   d = camel.load(data).next()

   k = d["kernel"]
   i = d["initrd"]
   dir = os.path.dirname(k)
 
   if not os.path.exists(dir):
       os.system("mkdir -p %s" % dir)

   os.system("touch %s" % k)
   os.system("touch %s" % i)


