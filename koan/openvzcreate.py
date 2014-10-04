"""
OpenVZ container-type virtualization installation functions.

Copyright 2012 Artem Kanarev <kanarev AT tncc.ru>, Sergey Podushkin <psv AT tncc.ru>

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

from __future__ import print_function

import os
from cexceptions import OVZCreateException


def start_install(*args, **kwargs):
    # check for Openvz tools presence
    # can be this apps installed in some other place?
    vzcfgvalidate = '/usr/sbin/vzcfgvalidate'
    vzctl = '/usr/sbin/vzctl'
    if not os.path.exists(vzcfgvalidate) or not os.path.exists(vzctl):
        raise OVZCreateException(
            "Cannot find %s and/or %s! Are OpenVZ tools installed?" %
            (vzcfgvalidate, vzctl)
        )

    # params, that can be defined/redefined through ks_meta
    keys_for_meta = [
        'KMEMSIZE',  # "14372700:14790164",
        'LOCKEDPAGES',  # "2048:2048",
        'PRIVVMPAGES',  # "65536:69632",
        'SHMPAGES',     # "21504:21504",
        'NUMPROC',      # "240:240",
        'VMGUARPAGES',  # "33792:unlimited",
        'OOMGUARPAGES',  # "26112:unlimited",
        'NUMTCPSOCK',   # "360:360",
        'NUMFLOCK',     # "188:206",
        'NUMPTY',       # "16:16",
        'NUMSIGINFO',   # "256:256",
        'TCPSNDBUF',    # "1720320:2703360",
        'TCPRCVBUF',    # "1720320:2703360",
        'OTHERSOCKBUF',  # "1126080:2097152",
        'DGRAMRCVBUF',  # "262144:262144",
        'NUMOTHERSOCK',  # "120",
        'DCACHESIZE',   # "3409920:3624960",
        'NUMFILE',      # "9312:9312",
        'AVNUMPROC',    # "180:180",
        'NUMIPTENT',    # "128:128",
        'DISKINODES',   # "200000:220000",
        'QUOTATIME',    # "0",
        'VE_ROOT',      # "/vz/root/$VEID",
        'VE_PRIVATE',   # "/vz/private/$VEID",
        'SWAPPAGES',    # "0:1G",
        'ONBOOT',       # "yes"
    ]

    sysname = kwargs['name']
    autoinst = kwargs['profile_data']['autoinst']
    # we use it for --ostemplate parameter
    template = kwargs['profile_data']['breed']
    hostname = kwargs['profile_data']['hostname']
    ipadd = kwargs['profile_data']['ip_address_eth0']
    nameserver = kwargs['profile_data']['name_servers'][0]
    diskspace = kwargs['profile_data']['virt_file_size']
    physpages = kwargs['profile_data']['virt_ram']
    cpus = kwargs['profile_data']['virt_cpus']
    onboot = kwargs['profile_data']['virt_auto_boot']

    # we get [0,1] ot [False,True] and have to map it to [no,yes]
    onboot = 'yes' if onboot == '1' or onboot else 'no'
    CTID = None
    vz_meta = {}

    # get all vz_ parameters from ks_meta
    for item in kwargs['profile_data']['ks_meta'].split():
        var = item.split('=')
        if var[0].startswith('vz_'):
            vz_meta[var[0].replace('vz_', '').upper()] = var[1]

    if 'CTID' in vz_meta and vz_meta['CTID']:
        try:
            CTID = int(vz_meta['CTID'])
            del vz_meta['CTID']
        except ValueError:
            print("Invalid CTID in ks_meta. Exiting...")
            return 1
    else:
        raise OVZCreateException(
            'Mandatory "vz_ctid" parameter not found in ks_meta!')

    confiname = '/etc/vz/conf/%d.conf' % CTID

    # this is the minimal config. we can define additional parameters or
    # override some of them in ks_meta
    min_config = {
        'PHYSPAGES': "0:%sM" % physpages,
        'SWAPPAGES': "0:1G",
        'DISKSPACE': "%sG:%sG" % (diskspace, diskspace),
        'DISKINODES': "200000:220000",
        'QUOTATIME': "0",
        'CPUUNITS': "1000",
        'CPUS': cpus,
        'VE_ROOT': "/vz/root/$VEID",
        'VE_PRIVATE': "/vz/private/$VEID",
        'OSTEMPLATE': template,
        'NAME': sysname,
        'HOSTNAME': hostname,
        'IP_ADDRESS': ipadd,
        'NAMESERVER': nameserver,
    }

    # merge with override
    full_config = dict(
        [
            (k, vz_meta[k] if k in vz_meta and k in keys_for_meta else min_config[k])
            for k in set(min_config.keys() + vz_meta.keys())]
    )

    # write config file for container
    f = open(confiname, 'w+')
    for key, val in full_config.items():
        f.write('%s="%s"\n' % (key, val))
    f.close()

    # validate the config file
    cmd = '%s %s' % (vzcfgvalidate, confiname)
    if not os.system(cmd.strip()):
        # now install the container tree
        cmd = '/usr/bin/ovz-install %s %s %s' % (
            sysname,
            autoinst,
            full_config['VE_PRIVATE'].replace('$VEID', '%d' % CTID)
        )
        if not os.system(cmd.strip()):
            # if everything fine, start the container
            cmd = '%s start %s' % (vzctl, CTID)
            if os.system(cmd.strip()):
                raise OVZCreateException("Start container %s failed" % CTID)
        else:
            raise OVZCreateException("Container creation %s failed" % CTID)
    else:
        raise OVZCreateException(
            "Container %s config file is not valid" %
            CTID)
