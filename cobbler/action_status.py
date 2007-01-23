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
 
        last_recorded_time = 0
        time_collisions = 0

        # find all of the logged IP addrs
        filelist = glob.glob("/var/log/cobbler/kicklog/*")
        filelist.sort()
        
        header = ("Address", "State", "Started", "Last Request", "Seconds", "Log Entries")
        print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % header

        for fullname in filelist:
            fname = os.path.basename(fullname)               # access times log
            fullname2 = "/var/log/cobbler/syslog/%s" % fname # remote syslog
               
            entries = {} # hash of access times and messages
            ip = None

            # both types of log files must be intertwingled (TM)

            for openme in [ fullname, fullname2 ]:

                # it's possible syslog never hit the server, that's ok.
                if not os.path.exists(openme):
                    continue
                
                logfile = open(openme, "r")
                data = "..."
                
                # for each line in the file...
                while(data is not None and data != ""):
                    data = logfile.readline()

                    # fields are tab delimited
                    # (1) seconds since 1970, in decimal
                    # (2) ASCII date for humans
                    # (3) IP address of requester
                    # (4) HTTP request line
      
                    try: 
                        (epoch, strdate, ip, request) = data.split("\t", 3)
                    except:
                        continue

                    # HTTP request line is essentially space delimited
                    # (1) method, which should always be GET
                    # (2) filename, which is relative from server root
                    # (3) protocol, such as HTTP/1.1
       
                    # time collision voodoo
                    # we are storing times in a hash, and this prevents them from colliding
                    # which would break the filecount and possibly the state check
                    
                    logtime = float(epoch)
                    if int(logtime) == last_recorded_time:
                        time_collisions = time_collisions + 1
                    else:
                        time_collisions = 0
                    logtime = logtime + (0.001 * time_collisions)

                    # to make the report generation a bit easier, flag what we think are start/end points

                    if request.find("?system_done") != -1:             
                        entries[logtime] = "DONE:%s" % request
                    elif request.find("?profile_done") != -1:
                        entries[logtime] = "DONE:%s" % request
                    elif request.find("Method =") != -1:
                        entries[logtime] = "START:%s" % request
                    else:
                        entries[logtime] = "1" # don't really care what the filename was

                    last_recorded_time = int(logtime) 

                    # FIXME: calculate start times for each IP as defined as earliest file
                    # requested after each stop time, or the first file requested if no
                    # stop time.

                logfile.close()

            # print the report line for this IP addr

            self.generate_report(entries,ip)

        return True

     #-----------------------------------------

    def generate_report(self,entries,ip):
        """
        Given the information about transferred files and kickstart finish times, attempt
        to produce a report that most describes the state of the system.
        """
        
        # sort the access times
        rtimes = entries.keys()
        rtimes.sort()

        # variables for calculating kickstart state
        last_request_time = 0
        last_start_time = 0
        last_done_time = 0
        fcount = 0

        # for each request time the machine has made
        for rtime in rtimes:

            rtime = rtime
            fname = entries[rtime]

            if fname.startswith("START:"):
               install_state = "installing"
               last_start_time = rtime
               last_request_time = rtime
               fcount = 0
            elif fname.startswith("DONE"):       
               # kickstart finished
               last_request_time = rtime
               last_done_time = rtime
               install_state = "done"
            else:
               install_state = "installing"
               last_request_time = rtime
            fcount = fcount + 1

        # calculate elapsed time for kickstart
        elapsed_time = 0
        if install_state == "done":
           elapsed_time = int(last_done_time - last_start_time)
        else:
           elapsed_time = int(last_request_time - last_start_time)

        # FIXME: IP to MAC mapping where cobbler knows about it would be nice.
        display_start = time.asctime(time.localtime(last_start_time))
        display_last  = time.asctime(time.localtime(last_request_time))
 
        # print the status line for this IP address
        print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % (ip, install_state, display_start, display_last, elapsed_time, fcount)               
 
