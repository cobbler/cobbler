"""
Downloads bootloader content for all arches for when the user doesn't want to supply their own.

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

import os
import urlgrabber
import clogger

class ContentDownloader:

   def __init__(self,config,logger=None):
       """
       Constructor
       """
       self.config   = config
       self.settings = config.settings()
       if logger is None:
           logger       = clogger.Logger()
       self.logger      = logger


   def run(self,force=False):
       """
       This action used to download the bootloaders from fedorapeople.org,
       however these files are now available from yum in the cobbler-loaders
       package so you should use that instead.
       """

       self.logger.info("The 'cobbler get-loaders' command has been obsoleted with 'yum install cobbler-loaders' in this version of cobbler. Please use 'yum install cobbler-loaders' instead.")
       return False

