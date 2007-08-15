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
import api as cobbler_api

from rhpl.translate import _, N_, textdomain, utf8


class BootStatusReport:

    def __init__(self,config,mode):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.mode     = mode

    # -------------------------------------------------------

    def scan_apache_logfiles(self):
        results = {}
        files = [ "/var/log/httpd/access_log" ] 
        for x in range(1,4):
           consider = "/var/log/httpd/access_log.%s" % x
           if os.path.exists(consider):
               files.append(consider)
        for fname in files:
           fh = open(fname)
           data = fh.readline()
           while (data is not None and data != ""):
               data = fh.readline()
               tokens = data.split(None)
               if len(tokens) < 6:
                   continue
               ip    = tokens[0]
               stime  = tokens[3].replace("[","")
               req   = tokens[6]        
               if req.find("/cblr") == -1:
                   continue
               ttime = time.strptime(stime,"%d/%b/%Y:%H:%M:%S")
               itime = time.mktime(ttime)
               if not results.has_key(ip):
                   results[ip] = {}
               results[ip][itime] = req

        return results

    # -------------------------------------------------------

    def scan_syslog_logfiles(self):
        
        # find all of the logged IP addrs
        filelist = glob.glob("/var/log/cobbler/syslog/*")
        filelist.sort()
        results = {}

        for fullname in filelist:
            #fname = os.path.basename(fullname)    
            logfile = open(fullname, "r")
            # for each line in the file...
            data = logfile.readline()
            while(data is not None and data != ""):
                data = logfile.readline()

                try:
                    (epoch, strdate, ip, request) = data.split("\t", 3)
                    epoch = float(epoch)
                except:
                    continue
 
                if not results.has_key(ip):
                    results[ip] = {}
                results[ip][epoch] = request

        return results

    # -------------------------------------------------------

    def run(self):
        """
        Calculate and print a kickstart-status report.
        For kickstart trees not in /var/lib/cobbler (or a symlink off of there)
        tracking will be incomplete.  This should be noted in the docs.
        """

        api = cobbler_api.BootAPI()

        apache_results = self.scan_apache_logfiles()
        syslog_results = self.scan_syslog_logfiles()
        ips = apache_results.keys()
        ips.sort()
        ips2 = syslog_results.keys()
        ips2.sort()

        ips.extend(ips2)
        ip_printed = {}

        last_recorded_time = 0
        time_collisions = 0
        
        #header = ("Name", "State", "Started", "Last Request", "Seconds", "Log Entries")
        print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % (
           _("Name"),
           _("State"),
           _("Last Request"),
           _("Started"),
           _("Seconds"),
           _("Log Entries")
        )

        
        for ip in ips:
            if ip_printed.has_key(ip):
                continue
            ip_printed[ip] = 1
            entries = {} # hash of access times and messages
            if apache_results.has_key(ip):
                times = apache_results[ip].keys()
                for logtime in times:
                    request = apache_results[ip][logtime] 
                    if request.find("?system_done") != -1:             
                        entries[logtime] = "DONE"
                    elif request.find("?profile_done") != -1:
                        entries[logtime] = "DONE"
                    else:
                        entries[logtime] = "1" # don't really care what the filename was

            if syslog_results.has_key(ip):
                times = syslog_results[ip].keys()
                for logtime in times:
                    request = syslog_results[ip][logtime]
                    if request.find("methodcomplete") != -1:
                        entries[logtime] = "DONE"
                    elif request.find("Method =") != -1:
                        entries[logtime] = "START"
                    else:
                        entries[logtime] = "1"

            name = api.systems().find(ip_address=ip).name
            self.generate_report(entries,name)


        return True

     #-----------------------------------------

    def generate_report(self,entries,name):
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

        if len(rtimes) == 0:
            print _("%s: ?") % name
            return

        # for each request time the machine has made
        for rtime in rtimes:

            rtime = rtime
            fname = entries[rtime]

            if fname == "START":
               install_state = "installing"
               last_start_time = rtime
               last_request_time = rtime
               fcount = 0
            elif fname == "DONE":
               # kickstart finished
               last_done_time = rtime
               install_state = "done"
            else:
               install_state = "?"
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

        if display_start.find(" 1969") != -1:
            display_start = "?"
            elapsed_time  = "?"   
  
        # print the status line for this IP address
        print "%-20s | %-15s | %-25s | %-25s | %-10s | %-6s" % (
            name, 
            install_state, 
            display_start, 
            display_last, 
            elapsed_time, 
            fcount
        )           
 

