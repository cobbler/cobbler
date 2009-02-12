#!/usr/bin/python

# (c) 2008-2009
# Jeff Schroeder <jeffschroeder@computer.org>
# Michael DeHaan <mdehaan@redhat.com>
#
# License: GPLv2+


# Post install trigger for cobbler to
# send out a pretty email report that
# contains target information.

import smtplib
import xmlrpclib
import cobbler.yaml as yaml
import sys
import cobbler.templar as templar

server = xmlrpclib.Server("http://127.0.0.1:25151")
print "ping"
print server.ping()
print "pong"
settings = server.get_settings()

# go no further if this feature is turned off
if not settings["build_reporting_enabled"]:
    print "not enabled"
    sys.exit(0)

objtype = sys.argv[1] # "target" or "profile"
name    = sys.argv[2] # name of target or profile
boot_ip = sys.argv[3] # ip or "?"

if objtype == "system":
    target = server.get_system_for_koan(name,True)
    profile = target.get("profile","")
else:
    target = server.get_profile_for_koan(name,True)
    profile = target.get("name","")

if target == {}:
    print "failure looking up target"
    sys.exit(1)

to_addr = settings.get("build_reporting_email","")
if to_addr == "":
    print "no email address configured"
    sys.exit(2)

# add the ability to specify an MTA for servers that don't run their own
smtp_server = settings.get("build_reporting_smtp_server","")
if smtp_server == "":
    smtp_server = "localhost"

# use a custom from address or fall back to a reasonable default
from_addr = settings.get("build_reporting_sender","")
if from_addr == "":
    from_addr = "cobbler@%s" % settings["server"]

subject = settings.get("build_reporting_subject","")
if subject == "":
    subject = '[Cobbler] install complete '

data = yaml.dump(target)

to_addr = ", ".join(to_addr)
metadata = {
   "from_addr" : from_addr,
   "to_addr"   : to_addr,
   "subject"   : subject,
   "boot_ip"   : boot_ip
}
metadata.update(target)

input_template = open("/etc/cobbler/reporting/build_report_email.template")
input_data = input_template.read()
input_template.close()

message = templar.Templar().render(input_data, metadata, None)
# for debug, call
# print message

# Send the mail
# FIXME: on error, return non-zero
server_handle = smtplib.SMTP(smtp_server)
server_handle.sendmail(from_addr, to_addr, message)
server_handle.quit()


