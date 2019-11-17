***********************
Cobbler Direct Commands
***********************

.. _cobbler-check:

Check
#####

The check command is used to provide information to the user regarding possible issues with their installation. Many of
these checks are feature-based, and may not show up depending on the features you have enabled in Cobbler.

One of the more important things to remember about the check command is that the output contains suggestions, and not
absolutes. That is, the check output may always show up (for example, the SELinux check when it is enabled on the
system), or the suggested remedy is not required to make Cobbler function properly (for example, the firewall checks).
It is very important to evaluate each item in the listed output individually, and not be concerned with them unless you
are having definite problems with functionality.

**Example:**

.. code-block:: bash

    $ cobbler check
    The following are potential configuration items that you may want to fix:

    1 : SELinux is enabled. Please review the following wiki page for details on ensuring cobbler works correctly in your SELinux environment:
        https://github.com/cobbler/cobbler/wiki/Selinux
    2 : comment 'dists' on /etc/debmirror.conf for proper debian support
    3 : comment 'arches' on /etc/debmirror.conf for proper debian support
    4 : Dynamic settings changes are enabled, be sure you run "sed -i 's/^[[:space:]]\+/ /' /etc/cobbler/settings" to ensure the settings file is properly indented

    Restart cobblerd and then run 'cobbler sync' to apply changes.

.. _cobbler-sync:

Sync
####

The sync command is very important, though very often unnecessary for most situations. It's primary purpose is to force
a rewrite of all configuration files, distribution files in the TFTP root, and to restart managed services. So why is it
unnecessary? Because in most common situations (after an object is edited, for example), Cobbler executes what is known
as a "lite sync" which rewrites most critical files.

When is a full sync required? When you are using ``manage_dhcpd`` :ref:`manage-dhcp` with systems that use static
leases. In that case, a full sync is required to rewrite the ``dhcpd.conf`` file and to restart the dhcpd service.
Adding support for OMAPI is on the roadmap, which will hopefully relegate full syncs to troubleshooting situations.

**Example:** ``$ cobbler sync``

How Sync Works
==============

A full sync will perform the following actions:

1. Run pre-sync :ref:`triggers`
2. Clean the TFTP tree of any and all files
3. Re-copy boot loaders to the TFTP tree
4. Re-copy distribution files to the TFTP tree
    * This will attempt to hardlink files if possible
5. Rewrite the pxelinux.cfg/default file
6. Rewrite all other pxelinux.cfg files for systems
7. Rewrite all managed config files (DHCP, DNS, etc.) and restarts services
8. Cleans the "link cache"
9. Executes post-sync and change :ref:`triggers`

As noted above, this can take quite a bit of time if there are many distributions.

**See also:** :ref:`managing-services-with-cobbler`

Distro Signatures
#################

Prior to Cobbler 2.4.0, import modules for each supported distro were separate and customized for each specific
distribution. The values for breed and os-version were hard-coded into cobbler, so adding support for new distros or
newer versions of an already supported distro required code changes and a complete Cobbler upgrade.

Cobbler 2.4.0 introduces the concept of distro signatures to make adding support for newer distro versions without
requiring an upgrade to the rest of the system.

Distro Signatures File
======================

The distro signatures are stored in ``/var/lib/cobbler/distro_signatures.json``. As the extension indicates, this is a
JSON-formatted file, with the following structure:

.. code-block:: JSON

    {
        "breeds": {
            "<breed-name>": {
                "<os-version1>": {
                    "signatures": "...",
                    "default_kickstart":"..."
                }
            },
            "<breed-name>": {
                "<os-version1>": {
                    "signatures": "...",
                    "default_kickstart":"...",
                }
            }
        }
    }

This file is read in when cobblerd starts, and logs a message noting how many breeds and os-versions it has loaded:

.. code-block:: bash

    INFO | 9 breeds and 21 OS versions read from the signature file

CLI Commands
############

The signature CLI command has the following sub-commands:

.. code-block:: bash

    $ cobbler signature --help
    usage
    =====
    cobbler signature report
    cobbler signature update

cobbler signature report
========================

This command prints out a report of the currently loaded signatures and os-versions.

.. code-block:: bash

    $ cobbler signature report
    Currently loaded signatures:
    debian:
        squeeze
    freebsd:
        8.2
        8.3
        9.0
    generic:
        (none)
    redhat:
        fedora16
        fedora17
        fedora18
        rhel4
        rhel5
        rhel6
    suse:
        opensuse11.2
        opensuse11.3
        opensuse11.4
        opensuse12.1
        opensuse12.2
    ubuntu:
        oneiric
        precise
        quantal
    unix:
        (none)
    vmware:
        esx4
        esxi4
        esxi5
    windows:
        (none)

    9 breeds with 21 total signatures loaded

An optional ``--name`` parameter can be specified to limit the report to one breed:

.. code-block:: bash

    $ cobbler signature report --name=ubuntu
    Currently loaded signatures:
    ubuntu:
        oneiric
        precise
        quantal

    Breed 'ubuntu' has 3 total signatures

cobbler signature update
========================

This command will cause Cobbler to go and fetch the latest distro signature file from
http://cobbler.github.con/signatures/latest.json, and load the
signatures in that file. This file will be tested first, to ensure it is formatted correctly.

.. code-block:: bash

    cobbler signature update
    task started: 2012-11-21_222926_sigupdate
    task started (id=Updating Signatures, time=Wed Nov 21 22:29:26 2012)
    Successfully got file from http://cobbler.github.com/signatures/latest.json
    *** TASK COMPLETE ***

This command currently takes no options.

.. _cobbler-import:

Import
######

The purpose of ``cobbler import`` is to  set up a network install server for one or more distributions. This mirrors
content based on a DVD image, an ISO file, a tree on a mounted filesystem, an external rsync mirror or SSH location.

.. code-block:: bash

    $ cobbler import --path=/path/to/distro --name=F12

This example shows the two required arguments for import: ``--path`` and ``--name``.

Alternative set-up from existing filesystem
===========================================

_(<b>Note:</b> the description of "--available-as" is probably inadequate.)_

What if you don't want to mirror the install content on your install server? Say you already have the trees from all
your DVDs and/or CDs extracted on a Filer mounted over NFS somewhere. This works too, with the addition of one more
argument:

.. code-block:: bash

    cobbler import --path=/path/where/filer/is/mounted --name=filer \
      --available-as=nfs://nfsserver.example.org:/is/mounted/here

The above command will set up cobbler automatically using all of the above distros (stored on the remote filer) -- but
will keep the trees on NFS. This saves disk space on the Cobbler server. As you add more distros over time to the filer,
you can keep running the above commands to add them to Cobbler.

Importing Trees
===============

_(**Note:** this topic was imported from "Advanced Topics", and needs to be more properly integrated into this
document.)_

_(**Note:** the description of "--available-as" is probably inadequate.)_


Cobbler can auto-add distributions and profiles from remote sources, whether this is a filesystem path or an rsync
mirror. This can save a lot of time when setting up a new provisioning environment. Import is a feature that many users
will want to take advantage of, and is very simple to use.

After an import is run, cobbler will try to detect the distribution type and automatically assign kickstarts. By
default, it will provision the system by erasing the hard drive, setting up eth0 for dhcp, and using a default password
of "cobbler". If this is undesirable, edit the kickstart files in ``/var/lib/cobbler/kickstarts`` to do something else
or change the kickstart setting after cobbler creates the profile.

Mirrored content is saved automatically in ``/var/www/cobbler/ks_mirror``.

* Example 1: ``cobbler import --path=rsync://mirrorserver.example.com/path/ --name=fedora --arch=x86``
* Example 2: ``cobbler import --path=root@192.168.1.10:/stuff --name=bar``
* Example 3: ``cobbler import --path=/mnt/dvd --name=baz --arch=x86_64``
* Example 4: ``cobbler import --path=/path/to/stuff --name=glorp``
* Example 5: ``cobbler import --path=/path/where/filer/is/mounted --name=anyname --available-as=nfs://nfs.example.org:/where/mounted/``

Once imported, run a ``cobbler list`` or ``cobbler report`` to see what you've added.

By default, the rsync operations will exclude content of certain architectures, debug RPMs, and ISO images -- to change
what is excluded during an import, see ``/etc/cobbler/rsync.exclude``.

Note that all of the import commands will mirror install tree content into ``/var/www/cobbler`` unless a network
accessible location is given with ``--available-as``. ``--available-as`` will be primarily used when importing distros
stored on an external NAS box, or potentially on another partition on the same machine that is already accessible via
``http://`` or ``ftp://``.

For import methods using rsync, additional flags can be passed to rsync with the option ``--rsync-flags``.

Should you want to force the usage of a specific cobbler kickstart template for all profiles created by an import, you
can feed the option ``--kickstart`` to import, to bypass the built-in kickstart auto-detection.

Kickstarts
==========

Kickstarts are answer files that script the installation of the OS. Well, for Fedora and Red Hat based distributions it
is called kickstart. We also support other distributions that have similar answer files, but let's just use kickstart as
an example for now. The kickstarts automatically assigned above will install physical machines (or virtual machines --
we'll get to that later) with a default password of "cobbler" (don't worry, you can change these defaults) and a really
basic set of packages. For something more complicated, you may wish to edit the default kickstarts in
`/var/lib/cobbler/kickstarts`. You could also use cobbler to assign them new kickstart files. These files are actually
[Kickstart Templates](Kickstart Templating), a level beyond regular kickstarts that can make advanced customizations
easier to achieve. We'll talk more about that later as well.

Associated server set-up
========================

Firewall
********

Depending on your usage, you will probably need to make sure iptables is configured to allow access to the right
services. Here's an example configuration:

.. code-block:: bash

    # Firewall configuration written by system-config-securitylevel
    # Manual customization of this file is not recommended.
    *filter
    :INPUT ACCEPT [0:0]
    :FORWARD ACCEPT [0:0]
    :OUTPUT ACCEPT [0:0]

    -A INPUT -p icmp --icmp-type any -j ACCEPT
    -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # LOCALHOST
    -A INPUT -i lo -j ACCEPT

    # SSH
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
    # DNS - TCP/UDP
    -A INPUT -m state --state NEW -m udp -p udp --dport 53 -j ACCEPT
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 53 -j ACCEPT
    # DHCP
    -A INPUT -m state --state NEW -m udp -p udp --dport 68 -j ACCEPT
    # TFTP - TCP/UDP
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 69 -j ACCEPT
    -A INPUT -m state --state NEW -m udp -p udp --dport 69 -j ACCEPT
    # NTP
    -A INPUT -m state --state NEW -m udp -p udp --dport 123 -j ACCEPT
    # HTTP/HTTPS
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT
    # Syslog for cobbler
    -A INPUT -m state --state NEW -m udp -p udp --dport 25150 -j ACCEPT
    # Koan XMLRPC ports
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 25151 -j ACCEPT
    -A INPUT -m state --state NEW -m tcp -p tcp --dport 25152 -j ACCEPT

    #-A INPUT -j LOG
    -A INPUT -j REJECT --reject-with icmp-host-prohibited

    COMMIT

Adapt this to your own environment.

SELinux
*******

Most likely you are using SELinux since it has been in the Linux mainline since 2.6, as a result you'll need to allow
network access from the Apache web server.

.. code-block:: bash

    setsebool -P httpd_can_network_connect true

Services
********

Depending on whether you are running DHCP and DNS on the same box, you will want to enable various services:

.. code-block:: bash

    /sbin/service httpd start
    /sbin/service dhcpd start
    /sbin/service xinetd start
    /sbin/service cobblerd start

    /sbin/chkconfig httpd on
    /sbin/chkconfig dhcpd on
    /sbin/chkconfig xinetd on
    /sbin/chkconfig tftp on
    /sbin/chkconfig cobblerd on

This command ``cobbler check`` should inform you of most of this.

Using the server
================

PXE
***

PXE for network installation of "bare metal" machines is straightforward.  You need to set up DHCP:

* If the DHCP server is somewhere else, not on the Cobbler server, its administrator should set its ``next-server`` to
  specify your cobbler server.
* If you run DHCP locally and want Cobbler manage it for you, set ``manage_dhcp`` to 1 in ``/etc/cobbler/settings``,
  edit ``/etc/cobbler/dhcp.template`` to change some defaults, and re-run ``cobbler sync``. See :ref:`manage-dhcp` for
  further details.

Once you get PXE set up, all of the bare-metal compatible profiles will, by name, show up in PXE menus when the machines
network boot. Type "menu" at the prompt and choose one from the list. Or just don't do anything and the machine will
default through to local booting. (Some Xen paravirt profiles will not show up, because you cannot install these on
physical machines -- this is intended)

Should you want to pin a particular system to install a particular profile the next time it reboots, just run:

.. code-block:: bash

        cobbler system add --name=example --mac=$mac-address --profile=$profile-name

Then the above machine will boot directly to the profile of choice without bringing up the menu. Don't forget to read
the manpage docs as there are more options for customization and control available. There are also lots of useful
settings described in ``/etc/cobbler/settings`` that you will want to read over.

Reinstallation
**************

Should you have a system you want to install that Fedora 12 on (instead of whatever it is running now), right now, you
can do this:

.. code-block:: bash

    yum install koan
    koan --server=bootserver.example.com --list=profiles
    koan --replace-self --server=bootserver.example.com --profile=F12-i386
    /sbin/reboot

The system will install the new operating system after rebooting, hands off, no interaction required.

Notice in the above example "F12-i386" is just one of the boring default profiles cobbler created for you. You can also
create your own, for instance "F12-webservers" or "F12-appserver" -- whatever you would like to automate.

Virtualization
**************

Want to install a virtual guest instead (perhaps Xen or KVM)? No problem.

.. code-block:: bash

    yum install koan
    koan --server=bootserver.example.com --virt --virt-type=xenpv --profile=F12-i386-xen

Done.

You can also use KVM or other virtualization methods. These are covered elsewhere on the Wiki. Some distributions have
Xen specific profiles you need to use, though this is merged back together starting with Fedora 12.

.. _reposync:

Reposync
########

Yum repository management is an optional feature, and is not required to provision through cobbler. However, if cobbler
is configured to mirror certain repositories, it can then be used to associate profiles with those repositories. Systems
installed under those profiles will then be autoconfigured to use these repository mirrors in ``/etc/yum.repos.d``, and
if supported (Fedora Core 6 and later) these repositories can be leveraged even within Anaconda. This can be useful if
(A) you have a large install base, (B) you want fast installation and upgrades for your systems, or (C) have some extra
software not in a standard repository but want provisioned systems to know about that repository.

Make sure there is plenty of space in cobbler’s webdir, which defaults to ``/var/www/cobbler``.

.. code-block:: bash

    $ cobbler reposync [--tries=N] [--no-fail]

Cobbler reposync is the command to use to update repos as configured with ``cobbler repo add``. Mirroring can take a
long time, and usage of cobbler reposync prior to usage is needed to ensure provisioned systems have the files they need
to actually use the mirrored repositories. If you just add repos and never run ``cobbler reposync``, the repos will
never be mirrored. This is probably a command you would want to put on a crontab, though the frequency of that crontab
and where the output goes is left up to the systems administrator.

For those familiar with yum’s reposync, cobbler’s reposync is (in most uses) a wrapper around the yum command. Please
use ``cobbler reposync`` to update cobbler mirrors, as yum’s reposync does not perform all required steps. Also cobbler
adds support for rsync and SSH locations, where as yum’s reposync only supports what yum supports (http/ftp).

If you ever want to update a certain repository you can run:

.. code-block:: bash

    $ cobbler reposync --only="reponame1" ...

When updating repos by name, a repo will be updated even if it is set to be not updated during a regular reposync
operation (ex: ``cobbler repo edit --name=reponame1 --keep-updated=0``).

Note that if a cobbler import provides enough information to use the boot server as a yum mirror for core packages,
cobbler can set up kickstarts to use the cobbler server as a mirror instead of the outside world. If this feature is
desirable, it can be turned on by setting ``yum_post_install_mirror`` to ``1`` in ``/etc/cobbler/settings`` (and running
``cobbler sync``). You should not use this feature if machines are provisioned on a different VLAN/network than
production, or if you are provisioning laptops that will want to acquire updates on multiple networks.

The flags ``--tries=N`` (for example, ``--tries=3``) and ``--no-fail`` should likely be used when putting reposync on a
crontab. They ensure network glitches in one repo can be retried and also that a failure to synchronize one repo does
not stop other repositories from being synchronized.

.. _buildiso:

Build ISO
#########

Often an environment cannot support PXE because of either (A) an unfortunate lack of control over DHCP configurations
(i.e. another group owns DHCP and won't give you a next-server entry), or (B) you are using static IPs only.

This is easily solved: ``cobbler buildiso``

What this command does is to copy all distro kernel/initrds onto a boot CD image and generate a menu for the ISO that is
essentially equivalent to the PXE menu provided to net-installing machines via Cobbler.

By default, the boot CD menu will include all profiles and systems, you can force it to display a list of
profiles/systems in concern with the following.

Cobbler versions >= 2.2.0:

.. code-block:: bash

    # cobbler buildiso --systems="system1 system2 system3"
    # cobbler buildiso --profiles="profile1 profile2 profile3"

Cobbler versions < 2.2.0:

.. code-block:: bash

    # cobbler buildiso --systems="system1,system2,system3"
    # cobbler buildiso --profiles="profile1,profile2,profile3"

If you need to install into a lab (or other environment) that does not have network access to the cobbler server, you
can also copy a full distribution tree plus profile and system records onto a disk image:

.. code-block:: bash

    # cobbler buildiso --standalone --distro="distro1"

.. _command-line-search:

Command Line Search
###################

line search can be used to ask questions about your cobbler configuration, rather than just having to run
``cobbler list`` or ``cobbler report`` and scanning through the results. (The :ref:`web-interface` also supports
search/filtering, for those that want to use it, though that is not documented on this page)

Command line search works on all distro/profile/system/and repo objects.

.. code-block:: bash

    cobbler distro find --help
    cobbler profile find --help
    cobbler system find --help
    cobbler repo find --help

.. note:: Some of these examples are kind of arbitrary. I'm sure you can think of some more real world examples.

Examples
========

Find what system record has a given mac address.

.. code-block:: bash

    cobbler system find --mac=AA:BB:CC:DD:EE:FF

If anything is using a certain kernel, delete that object and all it's children (profiles, systems, etc).

.. code-block:: bash

    cobbler distro find --kernel=/path/to/kernel | xargs -n1 --replace cobbler distro remove --name={} --recursive

What profiles use the repo "epel-5-i386-testing" ?

.. code-block:: bash

    cobbler profile find --repos=epel-5-i386-testing

Which profiles are owned by neo AND mranderson?

.. code-block:: bash

    cobbler profile find --owners="neo,mranderson"
    # lists need to be comma delimited, like this, with no unneeded spaces

What systems are set to pass the kernel argument "color=red" ?

.. code-block:: bash

   cobbler system find --kopts="color=red"

What systems are set to pass the kernel argument "color=red" and "number=5" ?

.. code-block:: bash

    cobbler system find --kopts="color=red number=5"
    # space delimited key value pairs
    # key1=value1 key2 key3=value3

What systems set the kickstart metadata variable of foo to the value 'bar' ?

.. code-block:: bash

    cobbler system find --ksmeta="foo=bar"
    # space delimited key value pairs again

What systems are set to netboot disabled?

.. code-block:: bash

    cobbler system find --netboot-enabled=0
    # note, this also accepts 'false', or 'no'

For all systems that are assigned to profile "foo" that are set to netboot disabled, enable them.

.. code-block:: bash

    cobbler system find --profile=foo --netboot-enabled=0 | xargs -n1 --replace cobbler system edit --name={} --netboot-enabled=1
    # demonstrates an "AND" query combined with xargs usage.

A Note About Types And Wildcards
================================

Though the cobbler objects behind the scenes store data in various different formats (booleans, hashes, lists, strings),
it all works fom the command line as text.

If multiple terms are specified to one argument, the search is an "AND" search.

If multiple parameters are specified, the search is still an "AND" search.

The find command understands patterns such as "\*" and "?". This is supported using Python's fnmatch.

To learn more: ``pydoc fnmatch.fnmatch``

All systems starting with the string foo: ``cobbler system find --name="foo*"``

This is rather useful when combined with xargs. This is a rather tame example, reporting on all systems starting with
"TEST".

.. code-block:: bash

    cobbler system find --name="TEST*" | xargs -n1 --replace cobbler system report --name={}

By extension, you could use this to toggle the ``--netboot-enabled`` systems of machines with certain hostnames, mac
addresses, and so forth, or perform other kinds of wholesale edits (for instance, deletes, or assigning profiles with
certain names to new distros when upgrading them from F8 to F9, for instance).

API Usage
=========

All of this functionality is also exposed through the API

.. code-block:: python

    #!/usr/bin/python
    import cobbler.api as capi
    api_handle = capi.BootAPI()
    matches = api_handle.find_profile(name="TEST*",return_list=True)
    print matches

You will find uses of ``.find()`` throughout the cobbler code that make use of this behavior.

.. _replication:

Replication
###########

.. code-block:: bash

    cobbler replicate --help

Replication works by downloading the configuration from one cobbler server into another. It is useful for Highly
Available setups, disaster recovery, support of multiple geographies, or for load balancing.

.. code-block:: bash

    cobbler replicate --master=master.example.org

With the default arguments, only distribution and profile metadata are synchronized. Without any of the other sync flags
(described below) it is assumed data backing these objects (such as kernels/initrds, etc) are already accessible. Don't
worry though, cobbler can help move those over too.

Transferring More Than Just Metadata
====================================

Cobbler can transfer mirrored trees, packages, snippets, kickstart templates, and triggers as well. To do this, just use
the appropriate flags with cobbler replicate.

.. code-block:: bash

    [root@localhost mdehaan]# cobbler replicate --help
    Usage: cobbler [options]

    Options:
      -h, --help            show this help message and exit
      --master=MASTER       Cobbler server to replicate from.
      --distros=PATTERN     pattern of distros  to replicate
      --profiles=PATTERN    pattern of profiles to replicate
      --systems=PATTERN     pattern of systems to replicate
      --repos=PATTERN       pattern of repos to replicate
      --image=PATTERN       pattern of images to replicate
      --omit-data           do not rsync data
      --prune               remove objects (of all types) not found on the master

Setup
=====

On each replica-to-be cobbler server, just install cobbler as normal, and make sure ``/etc/cobbler/settings`` and
``/etc/cobbler/modules.conf`` are appropriate. Use ``cobbler check`` to spot check your work. Cobbler replicate will not
configure these files, and you may want different site-specific settings for variables in these files. That's fine, as
cobbler replicate will respect these.

How It Works
============

Metadata is transferred over Cobbler XMLRPC, so you'll need to have the Cobbler XMLRPC endpoint accessible --
``http://servername:80/cobbler\_api``. This is the read only API so no authentication is
required. This is possible because this is a user-initiated pull operation, not a push operation.

Files are transferred either by rsync (over ssh) or scp, so you will probably want to use ssh-agent prior to kicking off
the replicate command, or otherwise use authorized\_keys on the remote host to save typing.

Limitations
===========

It is perfectly fine to sync data bi-directionally, though keep in mind metadata being synced is not timestamped with
the time of the last edit (this may be a nice future extension), so the latest sync "wins". Cobbler replicate is,
generally, designed to have a "master" concept, so it is probably not desirable yet to do bi-directional syncing.

Common Use Cases
================

High Availability / Disaster Recovery
*************************************

A remote cobbler server periodically replicates from the master to keep an active installation.

Load Balancing
**************

Similar to the HA/Disaster Recovery case, consider using a :ref:`triggers` to notify the other server to pull new
metadata when commands are issued.

Multiple Geographies
********************

Several remote servers pull from the master, either triggered by a :ref:`triggers` on the central server, or otherwise
on daily cron. This allows for establishing install mirrors that are closer and therefore faster and less bandwidth
hungry. The admin can choose whether or not system records should be centrally managed. It may be desirable to just
centrally provide the distributions and profiles and keep the system records on each seperate cobbler server, however,
there is nothing to say all records can't be kept centrally as well. (Choose one or the other, don't do a mixture of
both.)

Validate Kickstart
##################

ACL Setup
#########

Cobbler contains an "aclsetup" command for automation of setting up file system acls (i.e. setfacl) on directories that
cobbler needs to read and write to.

Using File System ACLs
======================

Usage of this command allows the administrator to grant access to other users without granting them the ability to run
cobbler as root.

.. code-block:: bash

    $ cobbler aclsetup --help
    Usage: cobbler aclsetup  [ARGS]

    Options:
      -h, --help            show this help message and exit
      --adduser=ADDUSER     give acls to this user
      --addgroup=ADDGROUP   give acls to this group
      --removeuser=REMOVEUSER
                            remove acls from this user
      --removegroup=REMOVEGROUP
                            remove acls from this group

Example:

.. code-block:: bash

    $ cobbler aclsetup --adduser=timmy

The above example gives timmy access to run cobbler commands.

Note that aclsetup does grant access to configure all of ``/etc/cobbler``, ``/var/www/cobbler``, and
``/var/lib/cobbler``, so it is still rather powerful in terms of the access it grants (though somewhat less so than
providing root).

A user with acls can, for instance, edit cobbler triggers which are later run by cobblerd (as root). In this event,
cobbler access (either sudo or aclsetup) should not be granted to users you do not trust completely. This should not be
a major problem as in giving them access to configure future aspects of your network (via the provisioning server) they
are already being granted fairly broad rights.

It is at least nicer than running "sudo" all of the time if you were going to grant a user "no password" sudo access to
cobbler.

Dynamic Settings
################

The CLI command for dynamic settings has two sub-commands:

.. code-block:: bash

    $ cobbler setting --help
    usage
    =====
    cobbler setting edit
    cobbler setting report

cobbler setting edit
====================

This command allows you to modify a setting on the fly. It takes affect immediately, however depending on the setting
you change, a ``cobbler sync`` may be required afterwards in order for the change to be fully applied.

This syntax of this command is as follows:

.. code-block:: bash

    $ cobbler setting edit --name=option --value=value

As with other cobbler primitives, settings that are array-based should be space-separated while hashes should be a
space-separated list of ``key=value`` pairs.

cobbler setting report
======================

This command prints a report of the current settings. The syntax of this command is as follows:

.. code-block:: bash

    $ cobbler setting report [--name=option]

The list of settings can be limited to a single setting by specifying the --name option.

Version
#######

The Cobbler version command is very simple, and provides a little more detailed information about your installation.

**Example:**

.. code-block:: bash

    $ cobbler version
    Cobbler 2.4.0
      source: ?, ?
      build time: Sun Nov 25 11:45:24 2012

The first piece of information is the version. The second line includes information regarding the associated commit for
this version. In official releases, this should correspond to the commit for which the build was tagged in git. The
final line is the build time, which could be the time the RPM was built, or when the "make" command was run when
installing from source.

All of this information is useful when asking for help, so be sure to provide it when opening trouble tickets.
