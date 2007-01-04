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
import os.path
import glob
import time
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
 
        files = {} # keep up with xfer'd files by IP addr
        
        # gather stats from logfiles, allowing for rotations in the log file ...
        last_recorded_time = 0
        time_collisions = 0

        filelist = glob.glob("/var/log/cobbler/kicklog/*")
        for fullname in filelist:
            fname = os.path.basename(fullname)

            # open it if it's there
            logfile = open(fullname, "r")
 
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
        
               if not files.has_key(ip):
                  files[ip] = {} # hash of access times and filenames
 
               # keep track of when IP addresses's finish.  Right now, we don't
               # care much about profile or system name but can get this later.

               # we are storing times in a hash, and this prevents them from colliding
               # which would break the filecount and possibly the state check
               logtime = float(epoch)
               if int(logtime) == last_recorded_time:
                   time_collisions = time_collisions + 1
               else:
                   time_collisions = 0
               logtime = logtime + (0.001 * time_collisions)

               if filepath.find("/cobbler_track/") == -1:
                  # it's a regular cobbler path, not a cobbler_track one, so ignore it.
                  # the logger doesn't need to log these anyway, but it might in the future.
                  # this is just an extra safeguard.
                  pass
               elif filepath.find("?system_done") != -1:             
                  files[ip][logtime] = "DONE"
               elif filepath.find("?profile_done") != -1:
                  files[ip][logtime] = "DONE"
               else:
                  files[ip][logtime] = filepath

               last_recorded_time = int(logtime) 

               # FIXME: calculate start times for each IP as defined as earliest file
               # requested after each stop time, or the first file requested if no
               # stop time.

            logfile.close()


        # report on the data found in all of the files, aggregated.

        self.generate_report(files)
        return True

     #-----------------------------------------

    def generate_report(self,files):
        """
        Given the information about transferred files and kickstart finish times, attempt
        to produce a report that most describes the state of the system.

        FIXME: just text for now, but should pay attention to self.mode and possibly offer
        a HTML or XML or YAML version for other apps.  Not all, just some alternatives.
        """
        

        # find all machines that have logged kickstart activity
        ips = files.keys()
        ips.sort()

        # FIXME: print the header
        header = ("Address", "State", "Started", "Last Request", "Seconds", "File Count")
        print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % header
 
        # for each machine
        for ip in ips:

           # sort the access times
           rtimes = files[ip].keys()
           rtimes.sort()

           # variables for calculating kickstart state
           last_request_time = 0
           last_start_time = 0
           last_done_time = 0
           files_counter = 0
           install_state = "norecord"

           # for each request time the machine has made
           for rtime in rtimes:

               rtime = rtime
               fname = files[ip][rtime]

               if fname != "DONE":
                   # process kickstart done state
                   if install_state == "done" or install_state == "norecord":
                       files_counter = 0
                       last_start_time = rtime
                   install_state = "notdone"
                   last_request_time = rtime 
                   files_counter = files_counter + 1
               else:       
                   # kickstart finished
                   install_state = "done"
                   last_request_time = rtime
                   last_done_time = rtime

           # calculate elapsed time for kickstart
           elapsed_time = 0
           if install_state != "norecord":
               elapsed_time = int(last_request_time - last_start_time)

           # FIXME: IP to MAC mapping where cobbler knows about it would be nice.

           display_start = time.asctime(time.localtime(last_start_time))
           display_last  = time.asctime(time.localtime(last_request_time))
 
           # print the status for this IP address
           print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % (ip, install_state, display_start, display_last, elapsed_time, files_counter)               
 
        # print "%s" % files



