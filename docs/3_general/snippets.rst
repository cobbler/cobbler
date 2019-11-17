.. _snippets:

********
Snippets
********

Snippets are a way of reusing common blocks of code between kickstarts (though this also works on files other than
kickstart templates, but that's a sidenote). For instance, the default Cobbler installation has a snippet called
"``$SNIPPET('func_register_if_enabled')``" that can help set up the application called Func.

This means that every time that this SNIPPET text appears in a kickstart file it is replaced by the contents of
``/var/lib/cobbler/snippets/func_register_if_enabled``. This allows this block of text to be reused in every kickstart
template -- you may think of snippets, if you like, as templates for templates!

To review, the syntax looks like: ``SNIPPET::snippet_name_here``

Where the name following snippet corresponds to a file in ``/var/lib/cobbler/snippets`` with the same name.

Snippets are implemented using a Cheetah function. Although the legacy syntax ("``SNIPPET::snippet_name_here``") will
still work, the preferred syntax is: ``$SNIPPET('snippet_name_here')``

You can still use the legacy syntax if you prefer, but a small bit of functionality is lost compared to the new style.

Advanced Snippets
#################

If you want, you can use a snippet name across many templates, but have the snippet be different for specific profiles
and/or system objects. Basically this means you can override the snippet with different contents in certain cases.

An example of this is if you want to a snippet called "``partition_select``" slightly for a certain profile (or set of
profiles) but don't want to change the master template that they all share.

This could also be used to set up a package list -- for instance, you could store the base package list to install in
``/var/lib/cobbler/snippets/package_list``, but override it for certain profiles and systems. This would allow you to
ultimately create less kickstart templates and leverage the kickstart templating engine more by just editing the smaller
and more easily readable snippet files. These also help keep your kickstarts manageable and keep them from becoming too
long.

The resolution order for kickstart templating evaluation is to use the following paths in order, finding the first one
if it exists (``per_distro`` was added in cobbler 2.0).

* ``/var/lib/cobbler/snippets/per_system/$snippet_name/$system_name``
* ``/var/lib/cobbler/snippets/per_profile/$snippet_name/$profile_name``
* ``/var/lib/cobbler/snippets/per_distro/$snippet_name/$distro_name``
* ``/var/lib/cobbler/snippets/$snippet_name``

As with the rest of cobbler, systems override profiles as they are more specific, though if the system file did not
exist, it would use the profile file. As a general safeguard, always create the
``/var/lib/cobbler/snippets/$snippet_name`` file if you create the ``per_system`` and ``per_profile`` ones.

Subdirectories
##############

Snippets can be placed in subdirectories for better organization, and will follow the order of precedence listed above.
For example: ``/var/lib/cobbler/snippets/$subdirectory/$snippet_name``

This would be referenced in your kickstart template as ``$SNIPPET('$subdirectory/$snippet_name')``.

Replace the dollar sign names with the actual values, such as ... ``$SNIPPET('example.org/dostuff')``

Variable Snippet Names
######################

Sometimes it is useful to determine which snippet to include at render time. In Cobbler 1.2, this can be done by
omitting the quotes and using a template variable: ``$SNIPPET($my_snippet)``

Note that this DOES NOT work with the legacy syntax:

.. code-block:: bash

    #set my_snippet = 'foo'
    SNIPPET::$my_snippet

This will not behave as expected. We would like it to include a snippet named 'foo'; instead, it will search for a
snippet named ``$my_snippet``.

Cobbler SNIPPETs versus Cheetah #include
########################################

It seems that ``$SNIPPET`` and ``#include`` accomplish the same thing. In fact, ``$SNIPPET`` uses ``#include`` in its
implementation! While the two perform similar tasks, there are some important differences:

* ``$SNIPPET`` will search for profile and system-specific SNIPPETS (See Advanced Snippets)
* ``$SNIPPET`` will include the namespace of the snippet, so any functions ``#def``'ed in the snippet will be accessible
  to the main kickstart file. ``#include`` will not do this.

For example:

.. code-block:: bash

    my_snippet:

        #def myfunc()
        ...
        #end def

    my_kickstart:

        #include '/var/lib/cobbler/snippets/my_snippet'  ## UGH!
        $myfunc()

Will NOT work. However,

.. code-block:: bash

    my_kickstart:

        $SNIPPET('my_snippet') ## Much better!
        $myfunc()

Will work as expected. It will search for the snippet itself, and it will make sure ``myfunc()`` is callable from
``my_kickstart``.

Scoping issues
##############

Cobbler uses Cheetah to implement snippets, so variables in these snippets are subject to Cheetah's scoping rules
(except ``#def``'ed functions). Variables set inside a snippet cannot be accessed in the main kickstart file. For
example:

.. code-block:: bash

    my_snippet:

        #set dns1 = '192.168.0.1'

    my_kickstart:

        $SNIPPET('my_snippet')
        echo 'nameserver $dns1' >> /etc/resolv.conf

Will not work as expected. The variable ``$dns1`` is destroyed as soon as Cheetah finishes processing ``my_snippet``. To
fix this, use the 'global' modifier:

.. code-block:: bash

    my_snippet:

        #set global dns1 = '192.168.0.1'

Note that the 'global' modifier is not needed on ``#def`` directives. In fact, '``#def global``' is a syntax error in
Cheetah.

Recursive or Nested Snippets
############################

Cobbler Snippets can allow for nested snippets. For example:

.. code-block:: bash

    my_kickstart:

        Main content
        $SNIPPET('my_snippet')
        More main content

    my_snippet:

        Snippet content
        $SNIPPET('my_subsnippet')
        More snippet content

    my_subsnippet:

        Subsnippet content

Will yield:

.. code-block:: bash

    Main content
    Snippet content
    Subsnippet content
    More snippet content
    More main content

as expected.

Kickstart Snippet Cookbook
##########################

The rest of this page contains Snippets contributed by users of Cobbler that provide examples of usage and some quick
recipes that can be used/extended for your environment.

If you come up with any clever tricks, paste them here to share, and also share them with the cobbler mailing list so we
can talk about them.

Note that some of these rely on cobbler's `Cheetahtemplate <http://cheetahtemplate.org>`_ :ref:`kickstart-templating`
engine pretty heavily so they might be a little hard to read at first. Snippets can just be simple reusable blocks of
basic copy and paste text and can also be simple. Either way works depending on what you want to do.

.. note:: Content provided here is not part of Cobbler's "core" code so we may not be able to help you on the mailing
   list or IRC with snippets that aren't yet part of cobbler's core distribution. Cobbler does ship a few in
   ``/var/lib/cobbler/snippets`` that we can answer questions on, and in general, if you have a good idea, we'd love to
   work with you to get it shipped with Cobbler.

Adding an SSH key to authorized keys
====================================

.. code-block:: bash

    # Install Robin's public key for root user
    cd /root
    mkdir --mode=700 .ssh
    cat >> .ssh/authorized_keys << "PUBLIC_KEY"
    ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAtDHt4p16wtfUeyzyWBN7R1SXcnjq+R/ojQmiv8HOfYPNM48eCXYdCiNHD4tPCxuizLulqq1zG06B2OPVy9GXXtyXcAXLAQdGaZwDdKU6gHMUplUChSyDpXK6+afdkGimNYoWkQSjqPr9DF1YC4pyWRijxZGvun+yKIv1920wUmS1eqPfAmGYiVPY6ianctEx74PN0E9clenHsPipNDKlYGYeXDx2qewfG3YzJj6W02dCGSkNIaNNefQite3rQcOFHvAYDwzewKZmFSIdTo6nFqAVZtHi8ralyxzP2I7jo9NC5Q6Ivql+hWozlw+x6+zaA2KELcfqY2IMf+7VadtBww== robin@robinbowes.com
    PUBLIC_KEY
    chmod 600 .ssh/authorized_keys

Instructions for setup:

1.  Decide what to call your snippet. I'll use the name `publickey_root_robin`.
2.  Save your code in `/var/lib/cobbler/snippets/<snippet name>`
3.  Add your new snippet to your kickstart template, e.g.

.. code-block:: bash

    %post
    SNIPPET::publickey_root_robin
    $kickstart_done

Disk Configuration
==================

Contributed by: Matt Hyclak

This snippet makes use of if/else, getVar, and the ``split()`` function.

It provides some additional options for partitioning compared with the example shipped with Cobbler. If the disk you
want to partition is not sda, then simply set a ksmeta variable for the system (e.g.
``cobbler system edit --name=oldIDEbox --ksmeta="disk=hda"``)

.. code-block:: bash

    #set $hostname = $getVar('$hostname', None)
    #set $hostpart = $getVar('$hostpart', None)
    #set $disk = $getVar('$disk', 'sda')

    #if $hostname == None
    #set $vgname = "VolGroup00"
    #else
    #if $hostpart == None
    #set $hostpart = $hostname.split('.')[0]
    #set $vgname = $hostpart + '_sys'
    #end if
    #end if

    clearpart --drives=$disk --initlabel
    part /boot --fstype ext3 --size=200 --asprimary
    part swap --size=2000 --asprimary
    part pv.00 --size=100 --grow --asprimary
    volgroup $vgname pv.00
    logvol / --vgname=$vgname --size=16000 --name=sysroot --fstype ext3
    logvol /tmp --vgname=$vgname --size=4000 --name=tmp --fstype ext3
    logvol /var --vgname=$vgname --size=8000 --name=var --fstype ext3

    #if $hostpart == "bing"
    logvol /var/www --vgname=$vgname --size=16000 --name=www
    #else if $hostpart == "build32"
    logvol /var/fakedirectory --vgname=$vgname --size=123456789 --name=fake
    #end if

Another partitioning example
============================

Use software raid if there are more then one disk present (e.g.
``cobbler system edit --name=webServer --ksmeta="disks=sda,sdb"``)

Contributed by: Harry Hoffman

.. code-block:: bash

    #set disks = $getVar('$disks', 'sda')
    #set count = len($disks.split(','))

    #if $count >= 2
    part /boot --fstype ext3 --size=100 --asprimary --ondisk=${disks.split(',')[0]}
    part /boot2 --fstype ext3 --size=100 --asprimary --ondisk=${disks.split(',')[1]}
    part swap --size=1024 --asprimary --ondisk=${disks.split(',')[0]}
    part swap --size=1024 --asprimary --ondisk=${disks.split(',')[1]}

    part raid.10 --size=1 --grow --ondisk=${disks.split(',')[0]}
    part raid.11 --size=1 --grow --ondisk=${disks.split(',')[1]}
    raid pv.01 --fstype "physical volume (LVM)" --level=RAID1 --device=md0 raid.10 raid.11
    #else
    part /boot --fstype ext3 --size=100 --asprimary --ondisk=${disks.split(',')[0]}
    part swap --size=1024 --asprimary --ondisk=${disks.split(',')[0]}
    part pv.01 --size=1 --grow --ondisk=${disks.split(',')[0]}
    #end if

    volgroup internal_hd --pesize=32768 pv.01

    logvol / --name=slash --vgname=internal_hd --fstype ext3 --size=4096
    logvol /tmp --name=tmp --vgname=internal_hd --fstype ext3 --size=1024
    logvol /var --name=var --vgname=internal_hd --fstype ext3 --size=8192
    logvol /usr --name=usr --vgname=internal_hd --fstype ext3 --size=8192

Package Selection by hostname
=============================

Contributed by: Matt Hyclak

.. note:: Advanced Snippets in all recent versions of Cobbler make this unneccessary (this is an older snippet), but
   it's still a neat trick to learn some Cheetah skills.

This snippet makes use of if/else, getVar, the ``split()`` function, include, and try/except.

This snippet allows the administrator to create a file containing the package selection based on hostname and includes
it if possible, otherwise it fallse back to a default.

.. code-block:: bash

    #set $hostname = $getVar('$hostname', None)

    #if $hostname == None
    %packages
    @base
    #else
    #set $hostpart = $getVar('$hostpart', None)
    #if $hostpart == None
    #set $hostpart = $hostname.split('.')[0]
    #end if
    #set $sourcefile = "/var/lib/cobbler/packages/" + $hostpart

    %packages
    #try
      #include $sourcefile
    #except
    @base
    #end try
    #end if

Package Selection by profile name
=================================

Contributed by: Luc de Louw

This snippet add or removes packages depending on the profile name. Assuming you have profiles named rhel5, rhel5-test,
rhel4 and rhel4-test. You need to install packages depending if it a test system or not.

.. code-block:: bash

    #if 'test' in $profile_name
    #Test System selected, adding some more packages
    compat-gcc-32
    compat-gcc-32-c++
    compat-libstdc++-296
    compat-libstdc++-33.i386
    compat-libstdc++-33.x86_64
    libstdc++.i386
    libstdc++.x86_64

    #else
    #Non-test System detected, removing some packages
    -openmotif

    #end if

Add ``$SNIPPET('snippetname')`` at the ``%packages`` section in the kickstart template

Root Password Generation
========================

Contributed by: Matt Hyclak

This snippet makes use of if/else, getVar, and demonstrates how to import and use python modules directly.

This snippet generates a password from a pattern of the first 4 characters of the hostname + "andsomecommonpart",
creates an appropriate encrypted string with a random salt, and outputs the appropriate rootpw line. (mdehaan warns --
this snippet isn't secure as the variable 'hostname' can still be easily read from Cobbler XMLRPC, if systems have
access to it. Credentials are NOT required to read metadata variables like the hostname, and in this case, the hostname
isn't hard to guess either)

.. code-block:: bash

    #set $hostname = $getVar('$hostname', None)

    #if $hostname
    #set $distinct = $hostname[0:4]
    #set $rootpw = $distinct + "andsomecommonpart"

    #from crypt import crypt
    #from whrandom import choice
    #import string

    #set $salt_pop = string.letters + string.digits + '.' + '/'
    #set $salt = ''

    #for $i in range(8)
    #set $salt = $salt + choice($salt_pop)
    #end for

    #set $salt = '$1$' + $salt
    #set $encpass = crypt($rootpw, $salt)
    rootpw --iscrypted $encpass
    #end if

VMWare Detection
================

Contributed by: Matt Hyclak

This snippet makes use of if/else, getVar, and demonstrates how to make multiple comparisons in an if statement.

This snippet detects if the host is a VMWare guest, and adds a special kernel repository.

.. code-block:: bash

    #set $mac_address = $getVar('$mac_address', None)
    #if $mac_address
    #set $mac_prefix = $mac_address[0:8]

    #if $mac_prefix == "00:0c:29" or $mac_prefix == "00:05:69" or $mac_prefix == "00:50:56"

    cat << EOF >> /etc/yum.repos.d/vmware-kernels.repo
    [vmware-kernels]
    name=VMWare 100Hz Kernels
    baseurl=http://people.centos.org/~hughesjr/vmware-kernels/4/`uname -m`/
    enabled=1
    gpgcheck=0
    priority=2
    EOF

    yum -y install kernel

    #end if
    #end if

RHEL Installation Keys
======================

Contributed by: Wil Cooley

RHEL uses keys (also called *Installation Number*) to determine the appropriate packages to install. To fully automate a
RHEL installation, the kickstart needs a *key* option, either setting the key or explicitly skipping it.

This is not to be confused with :ref:`tips-for-rhn`, which includes registration instructions for RHN Hosted and
Satellite. Cobbler actually is happy with "``key --skip``" in most cases.

See also:

- [http://kbase.redhat.com/faq/FAQ\_103\_8967.shtm](http://kbase.redhat.com/faq/FAQ_103_8967.shtm)
- [http://www.redhat.com/docs/manuals/enterprise/RHEL-5-manual/Installation\_Guide-en-US/s1-kickstart2-options.html\#id3080516](http://www.redhat.com/docs/manuals/enterprise/RHEL-5-manual/Installation_Guide-en-US/s1-kickstart2-options.html#id3080516)

Add this to the kickstart template:

.. code-block:: bash

    # RHEL Install Key
    key $getVar('rhel_key', '--skip')

Then you can specify the key in the *ksmeta* system definition:

.. code-block:: bash

    # cobbler system edit --name=00:02:55:fa:6b:2b --ksmeta="rhel_key=xxx"

If *rhel\_key* is not specified, then it will fall back to *--skip*.

Configure Timezone Based on Hostname
====================================

Contributed by: `Jeff Schroeder <http://www.digitalprognosis.com>`_

This snipped will print the correct timezone line for your kickstart based on the system's hostname. It is highly
dependent on a consistent naming scheme and will have to be edited for each environment. Using multiple lines to set the
associative array seemed like the sanest way to do this to make adding and removing new locations easy.

.. code-block:: bash

    #if $getVar("system_name","") != ""
        #set foo = {}
        #set foo['nyc'] = 'America/New_York'
        #set foo['lax'] = 'America/Los_Angeles'
        #set foo['sin'] = 'Asia/Singapore'
        #set foo['tyo'] = 'Asia/Tokyo'
        #set foo['syd'] = 'Australia/Sydney'
        #set foo['dc'] = 'America/New_York'
        #set hostname = $getVar('system_name').split('.')
        #import re
    ## Work on hosts with funky hostnames like test001.lab01.lax07.int
        #if re.match('^lab', $hostname[1])
            #del $hostname[1]
        #end if

        #if $len($hostname) == 3  ## ie: ns1.lax07.int
            #set cluster = re.match('^[a-z]+', $hostname[1].lower()).group()

    timezone $foo[cluster]
        #else:
    # Could not autodetect hostname
    timezone --utc
        #end if
    #end if


Install HP Proliant Support Pack (PSP)
======================================

Contributed by: Dave Hatton

This snippet automatically installs the HP Proliant Support Pack (PSP). You may wish to adjust the location that the
tarball is downloaded and uncompressed to, and remove the install package after installation.

.. code-block:: bash

     mkdir -p /software

     /usr/bin/wget -O /software/psp-8.00.rhel5.x86_64.en.tar.gz http://@@server@@/cblr/localmirror/psp-8.00.rhel5.x86_64.en.tar.gz

     cd /software && /bin/tar -xzf psp-8.00.rhel5.x86_64.en.tar.gz


     /bin/cat >>/etc/rc3.d/S99install-hppsp <<EOF
    #!/bin/sh
    #This script will install the HP PSP
    #set -xv

     /bin/echo "Starting PSP Install: "
     cd /software/compaq/csp/linux && ./install800.sh --nui --silent

     /bin/rm -f $0

     exit 0
    EOF

     /bin/chmod 755 /etc/rc3.d/S99install-hppsp
