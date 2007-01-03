"""
Reports on kickstart activity by examining the logs in
/var/log/cobbler.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
#import re
import cobbler_msg

class BootStatusReport:

    def __init__(self,config,mode):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.mode     = mode

   # -------------------------------------------------------

    def run(self):
        """
        Calculate and print a kickstart-status report.
        For kickstart trees not in /var/lib/cobbler (or a symlink off of there)
        tracking will be incomplete.  This should be noted in the docs.
        """
 
        done  = {} # keep track of finish times by IP addr
        files = {} # keep up with xfer'd files by IP addr
        
        # gather stats from logfiles, allowing for rotations in the log file ...
        for i in range(0,6):
 
            # figure out what logfile to open
            j = ""
            if i != 0:
               j = "%s" % (i-1)
            fname = "/var/log/cobbler/cobbler%s.log" % j
 
            # open it if it's there
            if not os.path.exists(fname):
                print "no such file: %s" % fname
                break
            logfile = open(fname, "r")
 
            # each line in the file corresponds to an accessed file
            while(True):
               data = logfile.readline()
               if data is None or data == "":
                   break

               # fields are tab delimited
               # (1) seconds since 1970, in decimal
               # (2) ASCII date for humans
               # (3) IP address of requester
               # (4) HTTP request line
       
               (epoch, strdate, ip, request) = data.split("\t")
              
               # HTTP request line is essentially space delimited
               # (1) method, which should always be GET
               # (2) filename, which is relative from server root
               # (3) protocol, such as HTTP/1.1
       
               (method, filepath, protocol) = request.split(" ")

               # make room in the nested datastructures for report info
        
               if not done.has_key(ip):
                  done[ip] = []  # list of kickstart finish times
               if not files.has_key(ip):
                  files[ip] = {} # hash of access times and filenames
 
               # keep track of when IP addresses's finish.  Right now, we don't
               # care much about profile or system name but can get this later.

               if filepath.find("/cobbler_track/") != -1:
                  # it's a regular cobbler path, not a cobbler_track one, so ignore it.
                  # the logger doesn't need to log these anyway, but it might in the future.
                  # this is just an extra safeguard.
                  pass
               if filepath.find("?system_done") != -1:             
                  done[ip].append(epoch)
               elif filepath.find("?profile_done") != -1:
                  done[ip].append(epoch)
               else:
                  files[ip][epoch] = filepath
 
               # FIXME: calculate start times for each IP as defined as earliest file
               # requested after each stop time, or the first file requested if no
               # stop time.

            logfile.close()


        # report on the data found in all of the files, aggregated.

        self.generate_report(files,done)
        return True

     #-----------------------------------------

    def generate_report(self,files,done):
        """
        Given the information about transferred files and kickstart finish times, attempt
        to produce a report that most describes the state of the system.

        FIXME: just text for now, but should pay attention to self.mode and possibly offer
        a HTML or XML or YAML version for other apps.  Not all, just some alternatives.
        """
        print "%s" % files
        print "%s" % done



