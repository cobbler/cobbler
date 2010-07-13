"""
Monit integration configuration class.

Copyright 2010 Kelsey Hightower
Kelsey Hightower <kelsey.hightower@gmail.com>

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

module for starting Monit service management on RedHat based systems.
"""

import subprocess

class ConfigureMonit:

    def configure(self):
        """
        Configure Monit by ensuring the service is up and 
        running and the configuration is reload. 
        """
        print "- Configuring Monit"

        p = subprocess.Popen(['/sbin/service', 'monit', 'status'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out, err = p.communicate()
        # Service is up and running.
        if p.returncode == 0:
            status = "Success: Monit running"
            subprocess.call(['/usr/bin/monit', 'reload'])
        # Error while checking status, report failure.
        elif p.returncode == 1:
            print "  Starting %s failed: %s" % ('monit', err.strip('\n'))
            status = "Error: Failed to start monit"
        # Service is not running, try and start it.
        elif p.returncode == 3:
            s = subprocess.Popen(['/sbin/service', 'monit', 'start'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            start_out, start_err = s.communicate()
            if s.returncode == 0:
                print "  %s out of sync.. %s" % ('monit', start_out.strip('\n'))
                status = "Running: Monit has been started"
            elif s.returncode == 1:
                print "-  Starting %s failed: %s" % ('monit', err.strip('\n'))
                print start_out
                print start_err
                status = "Error: Failed to start monit"
            else:
                print "  Starting %s failed: %s" % ('monit', start_err)
                status = "Error: Failed to start monit"
        else:
            print "  Starting %s failed: %s" % ('monit', start_err)
            status = "Error: Failed to start monit"
            
        return status