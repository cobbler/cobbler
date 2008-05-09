"""
koan = kickstart over a network
general usage functions

Copyright 2006-2008 Red Hat, Inc.
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import random
import os
import traceback
import tempfile
import urllib2
import opt_parse  # importing this for backwards compat with 2.2
import exceptions
import sub_process
import time
import shutil
import errno
import re
import sys
import xmlrpclib
import string
import re
import glob
import socket

def setupLogging(appname, debug=False):
    """
    set up logging ... code borrowed/adapted from virt-manager
    """
    import logging
    import logging.handlers
    vi_dir = os.path.expanduser("~/.koan")
    if not os.access(vi_dir,os.W_OK):
        try:
            os.mkdir(vi_dir)
        except IOError, e:
            raise RuntimeError, "Could not create %d directory: " % vi_dir, e

    dateFormat = "%a, %d %b %Y %H:%M:%S"
    fileFormat = "[%(asctime)s " + appname + " %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamFormat = "%(asctime)s %(levelname)-8s %(message)s"
    filename = os.path.join(vi_dir, appname + ".log")

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    fileHandler = logging.handlers.RotatingFileHandler(filename, "a",
                                                       1024*1024, 5)

    fileHandler.setFormatter(logging.Formatter(fileFormat,
                                               dateFormat))
    rootLogger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(logging.Formatter(streamFormat,
                                                 dateFormat))
    if debug:
        streamHandler.setLevel(logging.DEBUG)
    else:
        streamHandler.setLevel(logging.ERROR)
    rootLogger.addHandler(streamHandler)


def urlread(url):
    """
    to support more distributions, implement (roughly) some 
    parts of urlread and urlgrab from urlgrabber, in ways that
    are less cool and less efficient.
    """
    print "- reading URL: %s" % url
    if url is None or url == "":
        raise InfoException, "invalid URL: %s" % url

    elif url.startswith("nfs"):
        try:
            ndir  = os.path.dirname(url[6:])
            nfile = os.path.basename(url[6:])
            nfsdir = tempfile.mkdtemp(prefix="koan_nfs",dir="/tmp")
            nfsfile = os.path.join(nfsdir,nfile)
            cmd = ["mount","-t","nfs","-o","ro", ndir, nfsdir]
            subprocess_call(cmd)
            fd = open(nfsfile)
            data = fd.read()
            fd.close()
            cmd = ["umount",nfsdir]
            subprocess_call(cmd)
            return data
        except:
            raise InfoException, "Couldn't mount and read URL: %s" % url
          
    elif url.startswith("http") or url.startswith("ftp"):
        try:
            fd = urllib2.urlopen(url)
            data = fd.read()
            fd.close()
            return data
        except:
            raise InfoException, "Couldn't download: %s" % url
    elif url.startswith("file"):
        try:
            fd = open(url[5:])
            data = fd.read()
            fd.close()
            return data
        except:
            raise InfoException, "Couldn't read file from URL: %s" % url
              
    else:
        raise InfoException, "Unhandled URL protocol: %s" % url

def urlgrab(url,saveto):
    """
    like urlread, but saves contents to disk.
    see comments for urlread as to why it's this way.
    """
    data = urlread(url)
    fd = open(saveto, "w+")
    fd.write(data)
    fd.close()

def subprocess_call(cmd,ignore_rc=False):
    """
    Wrapper around subprocess.call(...)
    """
    print "- %s" % cmd
    rc = sub_process.call(cmd)
    if rc != 0 and not ignore_rc:
        raise InfoException, "command failed (%s)" % rc
    return rc


def input_string_or_hash(options,delim=","):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options is None:
        return {}
    elif type(options) == list:
        raise CX(_("No idea what to do with list: %s") % options)
    elif type(options) == str:
        new_dict = {}
        tokens = options.split(delim)
        for t in tokens:
            tokens2 = t.split("=")
            if len(tokens2) == 1 and tokens2[0] != '':
                new_dict[tokens2[0]] = None
            elif len(tokens2) == 2 and tokens2[0] != '':
                new_dict[tokens2[0]] = tokens2[1]
            else:
                return {}
        new_dict.pop('', None)
        return new_dict
    elif type(options) == dict:
        options.pop('',None)
        return options
    else:
        raise CX(_("invalid input type"))


