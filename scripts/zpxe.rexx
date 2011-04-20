/* zPXE: REXX PXE Client for System z
 
zPXE is a PXE client used with Cobbler.  It must be run under
z/VM.  zPXE uses TFTP to first download a list of profiles,
then a specific kernel, initial RAMdisk, and PARM file.  These
files are then punched to start the install process.
 
zPXE does not require a writeable 191 A disk.  Files are
downloaded to a temporary disk (VDISK).
 
zPXE can also IPL a DASD disk by default.  You can specify the
default dasd in ZPXE CONF, as well as the hostname of the Cobbler
server.
---
 
Copyright 2006-2009, Red Hat, Inc
Brad Hinson <bhinson@redhat.com>
 
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
*/
 
 
/* Defaults */
 
server = ''                           /* define server in ZPXE CONF */
iplDisk = 100                   /* overridden by value in ZPXE CONF */
profilelist = PROFILE LIST T    /* VDISK will be defined as T later */
profiledetail = PROFILE DETAIL T
zpxeparm = ZPXE PARM T
zpxeconf = ZPXE CONF T
config = ZPXE CONF
 
/* For translating strings to lowercase */
upper = xrange('A', 'Z')
lower = xrange('a', 'z')
 
/* Query user ID.  This is used later to determine:
     1. Whether a user-specific PXE profile exists.
     2. Whether user is disconnected. If so, IPL the default disk.
*/
'pipe cp query' userid() '| var user'
parse value user with id . dsc .
userid = translate(id, lower, upper)

/* Useful settings normally found in PROFILE EXEC */
'cp set run on'
'cp set pf11 retrieve forward'
'cp set pf12 retrieve'

/* Make it possible to interrupt zPXE and to enter CMS even with a
   specific user profile present
*/
if (dsc <> 'DSC') then do                      /* user is connected */
  say ''
  say 'Enter a non-blank character and ENTER (or two ENTERs) within 10'
  say ' seconds to interrupt zPXE.'
  'WAKEUP +00:10 (CONS'
  /* Check for interrupt */
  if rc = 6 then do
    say 'Interrupt: entering CMS.'
    pull                                             /* Clear Stack */
    exit
  end
end
 
/* Check for config file */
if lines(config) > 0 then do
  inputline = linein(config)    /* first line is server hostname/IP */
  parse var inputline . server .
  inputline = linein(config)     /* second line is DASD disk to IPL */
  parse var inputline . iplDisk .
  if lines(config) > 0 then do
    inputline = linein(config)    /* third line is name of system in cobbler */
    parse var inputline . userid .
  end
end
 
/* Define temporary disk (VDISK) to store files */
'set vdisk syslim infinite'
'set vdisk userlim infinite'
'detach ffff'                             /* detach ffff if present */
'define vfb-512 as ffff blk 200000' /* 512 byte block size =~ 100 MB */
queue '1'
queue 'tmpdsk'
'format ffff t'                     /* format VDISK as file mode t */
 
/* Link TCPMAINT disk for access to TFTP */
'link tcpmaint 592 592 rr'
'access 592 e'
 
 
/* Check whether a user-specific PXE profile exists.
   If so, proceed with this.  Otherwise, continue and
   show the system-wide profile menu.
*/
call GetTFTP '/s390x/s_'userid 'profile.detail.t'
 
if lines(profiledetail) > 0 then do
 
  /* Get user PARM and CONF containing network info */
  call GetTFTP '/s390x/s_'userid'_parm' 'zpxe.parm.t'
  call GetTFTP '/s390x/s_'userid'_conf' 'zpxe.conf.t'
 
  vmfclear                                          /* clear screen */
  call CheckServer                             /* print server name */
  say 'Profile 'userid' found'
  say ''
 
  bootRc = ParseSystemRecord()        /* parse file for boot action */
  if bootRc = 0 then
    'cp ipl' iplDisk                           /* boot default DASD */
  else do
    call DownloadBinaries             /* download kernel and initrd */
    say 'Starting install...'
    say ''
    call PunchFiles                 /* punch files to begin install */
    exit
    end /* if bootRc = 0 */
 
end /* if user-specific profile found */
 
 
/* Download initial profile list */
call GetTFTP '/s390x/profile_list' 'profile.list.t'
 
vmfclear                                            /* clear screen */
call CheckServer                               /* print server name */
 
say 'zPXE MENU'                                        /* show menu */
say '---------'
 
count = 0
do while lines(profilelist) > 0     /* display one profile per line */
  count = count + 1
  inputline = linein(profilelist)
  parse var inputline profile.count
  say count'. 'profile.count
end
 
if (count = 0) then
  say '** Error connecting to server: no profiles found **'
 
count = count + 1
say count'. Exit to CMS shell [IPL CMS]'
say ''
say ''
say 'Enter Choice -->'
say 'or press <Enter> to boot from disk [DASD 'iplDisk']'
 
/* Check if user is disconnected, indicating
   logon by XAUTOLOG.  In this case, IPL the
   default disk.
*/
if (dsc = 'DSC') then do                    /* user is disconnected */
  say 'User disconnected.  Booting from DASD 'iplDisk'...'
  'cp ipl' iplDisk
  end
else do                            /* user is interactive -> prompt */
  parse upper pull answer .
  select
    when (answer = count)
    then do
      say 'Exiting to CMS shell...'
      exit
      end
    when (answer = '')                            /* IPL by default */
    then do
      say 'Booting from DASD 'iplDisk'...'
      'cp ipl' iplDisk
      end
    when (answer < 0) | (answer > count)         /* invalid respone */
    then do
      say 'Invalid choice, exiting to CMS shell.'
      exit
    end
    when (answer > 0) & (answer < count)          /* valid response */
    then do
      call GetTFTP '/s390x/p_'profile.answer 'profile.detail.t'
 
      /* get profile-based PARM and CONF files */
      call GetTFTP '/s390x/p_'profile.answer'_parm' 'zpxe.parm.t'
      call GetTFTP '/s390x/p_'profile.answer'_conf' 'zpxe.conf.t'
 
      vmfclear                                      /* clear screen */
      say 'Using profile 'answer' ['profile.answer']'
      say ''
      call DownloadBinaries           /* download kernel and initrd */
 
      say 'Starting install...'
      say ''
 
      call PunchFiles
 
    end /* valid answer */
    otherwise
      say 'Invalid choice, exiting to CMS shell.'
      exit
  end /* Select */
end
exit
 
 
/* Procedure CheckServer
   Print error message if server is not defined.  Otherwise
   show server name
*/
CheckServer:
 
  if server = '' then
    say '** Error: No host defined in ZPXE.CONF **'
  else say 'Connected to server 'server
  say ''
 
return 0 /* CheckServer */
 
 
/* Procedure GetTFTP
   Use CMS TFTP client to download files
     path: remote file location
     filename: local file name
     transfermode [optional]: 'ascii' or 'octet'
*/
GetTFTP:
 
  parse arg path filename transfermode
 
  if transfermode <> '' then
    queue 'mode' transfermode
  queue 'get 'path filename
  queue 'quit'
 
  'set cmstype ht'                          /* suppress tftp output */
  tftp server
  'set cmstype rt'
 
return 0 /* GetTFTP */
 
 
/* Procedure DownloadBinaries
   Download kernel and initial RAMdisk.  Convert both
   to fixed record length 80.
*/
DownloadBinaries:
 
  inputline = linein(profiledetail)         /* first line is kernel */
  parse var inputline kernelpath
  say 'Downloading kernel ['kernelpath']...'
  call GetTFTP kernelpath 'kernel.img.t' octet
 
  inputline = linein(profiledetail)        /* second line is initrd */
  parse var inputline initrdpath
  say 'Downloading initrd ['initrdpath']...'
  call GetTFTP initrdpath 'initrd.img.t' octet
 
  inputline = linein(profiledetail)  /* third line is ks kernel arg */
  parse var inputline ksline
  call lineout zpxeparm, ksline       /* add ks line to end of parm */
  call lineout zpxeparm                               /* close file */
 
  /* convert to fixed record length */
  'pipe < KERNEL IMG T | fblock 80 00 | > KERNEL IMG T'
  'pipe < INITRD IMG T | fblock 80 00 | > INITRD IMG T'
 
return 0 /* DownloadBinaries */
 
 
/* Procedure PunchFiles
   Punch the kernel, initial RAMdisk, and PARM file.
   Then IPL to start the install process.
*/
PunchFiles:
 
  'spool punch *'
  'close reader'
  'purge reader all'                       /* clear reader contents */
  'punch kernel img t (noh'                         /* punch kernel */
  'punch zpxe parm t (noh'                       /* punch PARM file */
  'punch initrd img t (noh'                         /* punch initrd */
  'change reader all keep'                  /* keep files in reader */
  'ipl 00c clear'                                 /* IPL the reader */
 
return 0 /* PunchFiles */
 
 
/* Procedure ParseSystemRecord
   Open system record file to look for local boot flag.
   Return 0 if local flag found (guest will IPL default DASD).
   Return 1 otherwise (guest will download kernel/initrd and install).
*/
ParseSystemRecord:
 
  inputline = linein(profiledetail)               /* get first line */
  parse var inputline systemaction .
  call lineout profiledetail                          /* close file */
 
  if systemaction = 'local' then
    return 0
  else
    return 1
 
/* End ParseSystemRecord */
