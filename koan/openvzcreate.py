"""
Virtualization installation functions.
Currently somewhat Xen/paravirt specific, will evolve later.

Copyright 2006-2008 Red Hat, Inc and Others.
Michael DeHaan <michael.dehaan AT gmail>

Original version based on virtguest-install
Jeremy Katz <katzj@redhat.com>
Option handling added by Andrew Puch <apuch@redhat.com>
Simplified for use as library by koan, Michael DeHaan <michael.dehaan AT gmail>

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

import utils
import virtinstall
import pprint
import os

def start_install(*args, **kwargs):
	# pprint.pprint(args)
	# pprint.pprint(kwargs)
	template = kwargs['profile_data']['profile_name']
	hostname = kwargs['profile_data']['hostname']
	ipadd = kwargs['profile_data']['ip_address_eth0']
	nameserver = kwargs['profile_data']['name_servers'][0]
	ksmeta = kwargs['profile_data']['ks_meta']
	CTID = 
	#CTID = 103
	confiname ='/etc/vz/conf/%d.conf' % CTID
	

	config = {
		
		'KMEMSIZE':"14372700:14790164",
		'LOCKEDPAGES':"2048:2048",
		'PRIVVMPAGES':"65536:69632",
		'SHMPAGES':"21504:21504",
		'NUMPROC':"240:240",
		'PHYSPAGES':"0:unlimited",
		'VMGUARPAGES':"33792:unlimited",
		'OOMGUARPAGES':"26112:unlimited",
		'NUMTCPSOCK':"360:360",
		'NUMFLOCK':"188:206",
		'NUMPTY':"16:16",
		'NUMSIGINFO':"256:256",
		'TCPSNDBUF':"1720320:2703360",
		'TCPRCVBUF':"1720320:2703360",
		'OTHERSOCKBUF':"1126080:2097152",
		'DGRAMRCVBUF':"262144:262144",
		'NUMOTHERSOCK':"120",
		'DCACHESIZE':"3409920:3624960",
		'NUMFILE':"9312:9312",
		'AVNUMPROC':"180:180",
		'NUMIPTENT':"128:128",

		# Disk quota parameters (in form of softlimit:hardlimit)
		'DISKSPACE':"2G:2.2G",
		'DISKINODES':"200000:220000",
		'QUOTATIME':"0",

		# CPU fair scheduler parameter
		'CPUUNITS':"1000",
		'VE_ROOT':"/vz/root/$VEID",
		'VE_PRIVATE':"/vz/private/$VEID",
		'ORIGIN_SAMPLE':"basic",
		'OSTEMPLATE':template,
		'NAME':kwargs['name'],
		'HOSTNAME':hostname,
		'IP_ADDRESS':ipadd,
		'NAMESERVER':nameserver,
	}
	f = open(confiname, 'w+')
	for x,y in config.items():
		f.write('%s="%s"\n' % (x,y))
	f.close()
	# import shlex
	import os
	
	cmd = '/usr/sbin/vzcfgvalidate %s' % confiname
	# print 
	
	if not os.system(cmd.strip()):
		#cmd = 'vzctl create %d --config=%d' %  (CTID, CTID)
		#print cmd
		os.system(cmd.strip())
