"""
Running small pieces of cobbler sync when certain actions are taken,
such that we don't need a time consuming sync when adding new
systems if nothing has changed for systems that have already 
been created.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""


import os
import os.path
import shutil
import time
import yaml # Howell-Clark version
import sub_process
import sys

import utils
import action_sync
import cobbler_msg
import cexceptions
import traceback
import errno


class BootLiteSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.verbose     = True
        self.config      = config
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.sync_module = BootSync() 

    def add_single_distro(name):
        # generate YAML file in distros/$name in webdir
        # copy image files to images/$name in webdir:
        #    filenames: initrd.img and vmlinuz
        # same for tftpboot/images/$name
        pass

    def remove_single_distro(name):
        # delete distro YAML file in distros/$name in webdir
        # delete contents of images/$name directory in webdir
        # delete contents of images/$name in tftpboot
        pass

    def add_single_profile(name):
        # rebuild profile_list YAML file in webdir
        # add profiles/$name YAML file in webdir
        # generate kickstart for kickstarts/$name/ks.cfg in webdir
        pass
    
    def remove_single_profile(name)
        # rebuild profile_list YAML file in webdir
        # delete profiles/$name file in webdir
        # delete contents on kickstarts/$name directory in webdir
        pass
    
    def add_single_system(name):
        # rebuild system_list file in webdir
        # create system YAML file in systems/$name in webdir
        # create kickstarts_sys/$name/ks.cfg in webdir
        # create pxelinux.cfg/$foo where $foo is either the *encoded* IP
        #    or the MAC or default
        pass

    def remove_single_system(name):
        # rebuild system_list file in webdir
        # delete system YAML file in systems/$name in webdir
        # delete contents of kickstarts_sys/$name in webdir
        # delete pxelinux.cfg/$foo where $foo is either the *encoded* IP
        #   or the MAC or default        
        pass

