******************
Cobbler Primitives
******************

Primitives are the building blocks Cobbler uses to represent builds, as outlined in the "How We Model Things" section of
the :ref:`Introduction to Cobbler <about>`_ page. These objects are generally loosely related, though the
distro/profile/system relation is somewhat more strict.

This section covers the creation and use of these objects, as well as how they relate to each other - including the
methodology by which attributes are inherited from parent objects.

Standard Rules
##############

Cobbler has a standard set of rules for manipulating primitive field values and, in the case of
distros/profiles/systems, how those values are inherited from parents to children.

Inheritance of Values
=====================

Inheritance of values is based on the field type.

* For regular fields and arrays, the value will only be inherited if the field is set to ``<<inherit>>``.
  Since distros and other objects like repos do not have a parent, these values are inherited from the defaults in
  :ref:`settings`. If the field is specifically set to an empty string, no value will be inherited.
* For hashes, the values from the parent will always be inherited and blended with the child values. If the parent and
  child have the same key, the child's values will win an override the parent's.

Array Fields
============

Some fields in Cobbler (for example, the ``--name-servers`` field) are stored as arrays. These arrays are always
considered arrays of strings, and are always specified in Cobbler as a space-separated list when using add/edit.

**Example:**

.. code-block:: bash

    $ cobbler [object] edit --name=foo --field="a b c d"

Hash Fields (key=value)
=======================

Other fields in Cobbler (for example, the --ksmeta field) are stored as hashes - that is a list of key=value pairs. As
with arrays, both the keys and values are always interpreted as strings.

Preserving Values When Editing
******************************

By default, any time a hash field is manipulated during an edit, the contents of the field are replaced completely with
the new values specified during the edit.

**Example:**

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --ksmeta="e=f"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'e': 'f'}

To preserve the contents of these fields, --in-place should be specified:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --in-place --ksmeta="e=f"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd', 'e': 'f'}

Removing Values
***************

To remove a single value from the hash, use the '~' (tilde) character along with --in-place:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --in-place --ksmeta='~a'
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'c': 'd'}

Suppressing Values
******************

You can also suppress values from being used, by specifying the '-' character in front of the key name:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --in-place --ksmeta='-a'
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'-a': 'b', 'c': 'd'}

In this case, the key=value pair will be ignored when the field is accessed.

Keys Without Values
*******************

You can always specify keys without a value:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a b c"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': '~', 'c': '~', 'b': '~'}

<div class="alert alert-info alert-block">**Note:** While valid syntax, this could cause problems for some fields where
Cobbler expects a value (for example, --template-files).</div>

Keys With Multiple Values
*************************

It is also possible to specify multiple values for the same key. In this situation, Cobbler will convert the value
portion to an array:

.. code-block:: bash

    $ cobbler distro edit --name=foo --in-place --ksmeta="a=b a=c a=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': ['b', 'c', 'd']}

.. note:: You must specify ``--in-place`` for this to work. By default the behavior will result in a single value, with
   the last specified value being the winner.

Standard Primitive Sub-commands
###############################

All primitive objects support the following standard sub-commands:

List
====

The list command simply prints out an alphabetically sorted list of all objects.

**Example:**

.. code-block:: bash

    $ cobbler distro list
       centos6.3-x86_64
       debian6.0.5-x86_64
       f17-x86_64
       f18-beta6-x86_64
       opensuse12.2-i386
       opensuse12.2-x86_64
       opensuse12.2-xen-i386
       opensuse12.2-xen-x86_64
       sl6.2-i386
       sl6.2-x86_64
       ubuntu-12.10-i386
       ubuntu-12.10-x86_64

The list command is actually available as a top-level command as well, in which case it will iterate through every
object type and list everything currently stored in your Cobbler database.

Report
======

The report command prints a formatted report of each objects configuration. The optional ``--name`` argument can be used
to limit the output to a single object, otherwise a report will be printed out for every object (if you have a lot of
objects in a given category, this can be somewhat slow).

As with the list command, the report command is also available as a top-level command, in which case it will print a
report for every object that is stored in your Cobbler database.

Remove
======

The remove command uses only the ``--name`` option.

.. note:: Removing an object will also remove any child objects (profiles, sub-profiles and/or systems). Prior versions
   of Cobbler required an additional ``--recursive`` option to enable this behavior, but it has become the default in
   recent versions so use remove with caution.

**Example:**

.. code-block:: bash

    $ cobbler [object] remove --name=foo

Copy/Rename
===========

The copy and rename commands work similarly, with both requiring a ``--name`` and ``--newname`` options.

**Example:**

.. code-block:: bash

    $ cobbler [object] copy --name=foo --newname=bar
    # or
    $ cobbler [object] rename --name=foo --newname=bar

Find
====

The find command allows you to search for objects based on object attributes.

Please refer to the :ref:`command-line-search` section for more details regarding the find sub-command.

Dumpvars (Debugging)
====================

The dumpvars command is intended to be used for debugging purposes, and for those writing snippets. In general, it is
not required for day-to-day use.

Cobbler Objects
###############

Distros
=======

The first step towards installing systems with Cobbler is to add a distribution record to cobbler’s configuration.

The distro command has the following sub-commands:

.. code-block:: bash

    $ cobbler distro --help
    usage
    =====
    cobbler distro add
    cobbler distro copy
    cobbler distro edit
    cobbler distro find
    cobbler distro list
    cobbler distro remove
    cobbler distro rename
    cobbler distro report

Add/Edit Options
****************

In general, it’s really a lot easier to follow the import workflow -- it only requires waiting for the mirror content to
be copied and/or scanned. Imported mirrors also save time during install since they don’t have to hit external
installation sources. Please read the :ref:`cobbler-import` documentation for more details.

If you want to be explicit with distribution definition, however, here’s how it works:

**Example:**

.. code-block:: bash

    $ cobbler distro add --name=string --kernel=path --initrd=path [options]

--name (required)
+++++++++++++++++

A string identifying the distribution, this should be something like "rhel4".

--kernel (required)
+++++++++++++++++++

An absolute filesystem path to a kernel image.

--initrd (required)
+++++++++++++++++++

An absolute filesystem path to a initrd image.

--arch
++++++

Sets the architecture for the PXE bootloader and also controls how koan’s ``--replace-self`` option will operate.

The default setting (’standard’) will use pxelinux. Set to ’ia64’ to use elilo. ’ppc’ and ’ppc64’ use yaboot. ’s390x’ is
not PXEable, but koan supports it for reinstalls.

’x86’ and ’x86_64’ effectively do the same thing as standard.

If you perform a cobbler import, the arch field will be auto-assigned.

--boot-files
++++++++++++

This option is used to specify additional files that should be copied to the TFTP directory for the distro so that they
can be fetched during earlier stages of the installation. Some distributions (for example, VMware ESXi) require this
option to function correctly.

--breed
+++++++

Controls how various physical and virtual parameters, including kernel arguments for automatic installation, are to be
treated. Defaults to "redhat", which is a suitable value for Fedora and CentOS as well. It means anything redhat based.

There is limited experimental support for specifying "debian", "ubuntu", or "suse", which treats the kickstart file as a
different format and changes the kernel arguments appropriately. Support for other types of distributions is possible in
the future. See the Wiki for the latest information about support for these distributions.

The file used for the answer file, regardless of the breed setting, is the value used for ``--kickstart`` when creating
the profile. In other words, if another distro calls their answer file something other than a "kickstart", the kickstart
parameter still governs where that answer file is.

--clobber
+++++++++

This option allows "add" to overwrite an existing distro with the same name, so use it with caution.

--comment
+++++++++

An optional comment to associate with this distro.

--fetchable-files
+++++++++++++++++

This option is used to specify a list of key=value files that can be fetched via the python based TFTP server. The
"value" portion of the name is the path/name they will be available as via TFTP.

Please see the :ref:`managing-tftp` section for more details on using the python-based TFTP server.

--in-place
++++++++++

By default, any modifications to key=value fields (ksmeta, kopts, etc.) do no preserve the contents.

Example:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --ksmeta="e=f"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'e': 'f'}


To preserve the contents of these fields, ``--in-place`` should be specified:

.. code-block:: bash

    $ cobbler distro edit --name=foo --ksmeta="a=b c=d"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd'}
    $ cobbler distro edit --name=foo --in-place --ksmeta="e=f"
    $ cobbler distro report --name=foo | grep "Kickstart Meta"
    Kickstart Metadata             : {'a': 'b', 'c': 'd', 'e': 'f'}

--kopts
+++++++

Sets kernel command-line arguments that the distro, and profiles/systems dependant on it, will use during
installation only. This field is a hash field, and accepts a set of key=value pairs:

Example:

.. code-block:: bash

    --kopts="console=tty0 console=ttyS0,8,n,1 noapic"

--kopts-post
++++++++++++

This is just like ``--kopts``, though it governs kernel options on the installed OS, as opposed to kernel options fed to
the installer. This requires some special snippets to be found in your kickstart template to work correctly.

--ksmeta
++++++++

   <p>This is an advanced feature that sets variables available for use in templates. This field is a hash field, and accepts a set of key=value pairs:</p>
   <p><b>Example:</b></p>
{% highlight bash %}
--ksmeta="foo=bar baz=3 asdf"
{% endhighlight %}
   <p>See the section on [Kickstart Templating]({% link manuals/2.8.0/3/5_-_Kickstart_Templating.md %}) for further
   information.</p>
  </td>
 </tr>

--mgmt-classes
++++++++++++++

  <td>
   <p>Management classes that should be associated with this distro for use with configuration management systems.</p>
   <p>Please see the [Configuration Management]({% link manuals/2.8.0/4/3_-_Configuration_Management.md %}) section for
   more details on integrating Cobbler with configuration management systems.</p>
  </td>
 </tr>

--os-version
++++++++++++

  <td>Generally this field can be ignored. It is intended to alter some hardware setup for virtualized instances when
  provisioning guests with koan. The valid options for --os-version vary depending on what is specified for --breed. If
  you specify an invalid option, the error message will contain a list of valid os versions that can be used. If you do
  not know the os version or it does not appear in the list, omitting this argument or using "other" should be perfectly
  fine. Largely this is needed to support older distributions in virtualized settings, such as "rhel2.1", one of the OS
  choices if the breed is set to "redhat". If you do not encounter any problems with virtualized instances, this option
  can be safely ignored.</td>
 </tr>

--owners
++++++++

   <p>The value for --owners is a space seperated list of users and groups as specified in
   <code>/etc/cobbler/users.conf</code>.</p>
   <p>Users with small sites and a limited number of admins can probably ignore this option, since it only applies to
   the Cobbler WebUI and XMLRPC interface, not the "cobbler" command line tool run from the shell. Furthermore, this is
   only respected when using the "authz_ownership" module which must be enabled and is not the default.</p>
   <p>Please see the [Web Authorization]({% link manuals/2.8.0/5/3_-_Web_Authorization.md %}) section for more
   details.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--redhat-management-key</td>
  <td>
   <p>If you’re using Red Hat Network, Red Hat Satellite Server, or Spacewalk, you can store your authentication keys
   here and Cobbler can add the neccessary authentication code to your kickstart where the snippet named
   "redhat_register" is included. The default option specified in
   [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) will be used if this field is left blank.</p>
   <p>Please see the [Tips For RHN]({% link manuals/2.8.0/Appendix/C_-_Tips_for_RHN.md %}) section for more details on
   integrating Cobbler with RHN/Spacewalk.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--redhat-management-server</td>
  <td>
   <p>The RHN Satellite or Spacewalk server to use for registration. As above, the default option specified in
   [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) will be used if this field is left blank.</p>
   <p>Please see the [Tips For RHN]({% link manuals/2.8.0/Appendix/C_-_Tips_for_RHN.md %}) section for more details on
   integrating Cobbler with RHN/Spacewalk.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--template-files</td>
  <td>
   <p>This feature allows cobbler to be used as a configuration management system. The argument is a space delimited
   string of key=value pairs. Each key is the path to a template file, each value is the path to install the file on the
   system. Koan also can retrieve these files from a cobbler server on demand, effectively allowing cobbler to function
   as a lightweight templated configuration management system.</p>
   <p>Please see the
   [Built-In Configuration Management]({% link manuals/2.8.0/4/3/1_-_Built-In_Configuration_Management.md %}) section
   for more details on using template files.</p>
  </td>
 </tr>
</tbody>
</table>

Profiles and Sub Profiles
=========================

A profile associates a distribution to additional specialized options, such as a kickstart automation file. Profiles are
the core unit of provisioning and at least one profile must exist for every distribution to be provisioned. A profile
might represent, for instance, a web server or desktop configuration. In this way, profiles define a role to be
performed.

The profile command has the following sub-commands:

.. code-block:: bash

    $ cobbler profile --help
    usage
    =====
    cobbler profile add
    cobbler profile copy
    cobbler profile dumpvars
    cobbler profile edit
    cobbler profile find
    cobbler profile getks
    cobbler profile list
    cobbler profile remove
    cobbler profile rename
    cobbler profile report

Add/Edit Options
****************

**Example:**

.. code-block:: bash

    $ cobbler profile add --name=string --distro=string [options]

<table class="table table-condensed table-striped">
<thead>
 <tr>
  <th>Field Name</th>
  <th>Description</th>
 </tr>
</thead>
<tbody>
 <tr>
  <td class="nowrap">--name (required)</td>
  <td>A descriptive name. This could be something like "rhel5webservers" or "f9desktops".</td>
 </tr>
 <tr>
  <td class="nowrap">--distro (required)</td>
  <td>The name of a previously defined cobbler distribution. This value is required.</td>
 </tr>
 <tr>
  <td class="nowrap">--boot-files</td>
  <td>This option is used to specify additional files that should be copied to the TFTP directory for the distro so that they can be fetched during earlier stages of the installation. Some distributions (for example, VMware ESXi) require this option to function correctly.</td>
 </tr>
 <tr>
  <td class="nowrap">--clobber</td>
  <td>This option allows "add" to overwrite an existing profile with the same name, so use it with caution.</td>
 </tr>
 <tr>
  <td class="nowrap">--comment</td>
  <td>An optional comment to associate with this profile.</td>
 </tr>
 <tr>
  <td class="nowrap">--dhcp-tag</td>
  <td>
   <p>DHCP tags are used in the dhcp.template when using multiple networks.</p>
   <p>Please refer to the [Managing DHCP]({% link manuals/2.8.0/3/4/1_-_Managing_DHCP.md %}) section for more details.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--enable-gpxe</td>
  <td>
   <p>When enabled, the system will use gPXE instead of regular PXE for booting.</p>
   <p>Please refer to the [Using gPXE]({% link manuals/2.8.0/4/13_-_Using_gPXE.md %}) section for details on using gPXE for booting over a network.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--enable-menu</td>
  <td>When managing TFTP, Cobbler writes the `${tftproot}/pxelinux.cfg/default` file, which contains entries for all profiles. When this option is enabled for a given profile, it will not be added to the default menu.</td>
 </tr>
 <tr>
  <td class="nowrap">--fetchable-files</td>
  <td>
   <p>This option is used to specify a list of key=value files that can be fetched via the python based TFTP server. The "value" portion of the name is the path/name they will be available as via TFTP.</p>
   <p>Please see the [Managing TFTP]({% link manuals/2.8.0/3/4/4_-_Managing_TFTP.md %}) section for more details on using the python-based TFTP server.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--in-place</td>
  <td>By default, any modifications to key=value fields (ksmeta, kopts, etc.) do no preserve the contents. To preserve the contents of these fields, --in-place should be specified. This option is also required is using a key with multiple values (for example, "foo=bar foo=baz").</td>
 </tr>
 <tr>
  <td class="nowrap">--kickstart</td>
  <td>
   <p>Local filesystem path to a kickstart file. http:// URLs (even CGI’s) are also accepted, but a local file path is recommended, so that the kickstart templating engine can be taken advantage of.</p>
   <p>If this parameter is not provided, the kickstart file will default to `/var/lib/cobbler/kickstarts/default.ks`. This file is initially blank, meaning default kickstarts are not automated "out of the box". Admins can change the default.ks if they desire.</p>
   <p>When using kickstart files, they can be placed anywhere on the filesystem, but the recommended path is `/var/lib/cobbler/kickstarts`. If using the webapp to create new kickstarts, this is where the web application will put them.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--kopts</td>
  <td>
   <p>Sets kernel command-line arguments that the profile, and sub-profiles/systems dependant on it, will use during installation only. This field is a hash field, and accepts a set of key=value pairs:</p>
   <p><b>Example:</b></p>
{% highlight bash %}
--kopts="console=tty0 console=ttyS0,8,n,1 noapic"
{% endhighlight %}
  </td>
 </tr>
 <tr>
  <td class="nowrap">--kopts-post</td>
  <td>This is just like --kopts, though it governs kernel options on the installed OS, as opposed to kernel options fed
  to the installer. This requires some special snippets to be found in your kickstart template to work correctly.</td>
 </tr>
 <tr>
  <td class="nowrap">--ksmeta</td>
  <td>
   <p>This is an advanced feature that sets variables available for use in templates. This field is a hash field, and
   accepts a set of key=value pairs:</p>
   <p><b>Example:</b></p>
{% highlight bash %}
--ksmeta="foo=bar baz=3 asdf"
{% endhighlight %}
   <p>See the section on [Kickstart Templating]({% link manuals/2.8.0/3/5_-_Kickstart_Templating.md %}) for further
   information.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--mgmt-classes<br />--mgmt-parameters</td>
  <td>
   <p>Management classes and parameters that should be associated with this profile for use with configuration
   management systems.</p>
   <p>Please see the [Configuration Management]({% link manuals/2.8.0/4/3_-_Configuration_Management.md %}) section for
   more details on integrating Cobbler with configuration management systems.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--name-servers</td>
  <td>If your nameservers are not provided by DHCP, you can specify a space seperated list of addresses here to
  configure each of the installed nodes to use them (provided the kickstarts used are installed on a per-system basis).
  Users with DHCP setups should not need to use this option. This is available to set in profiles to avoid having to set
  it repeatedly for each system record.</td>
 </tr>
 <tr>
  <td class="nowrap">--name-servers-search</td>
  <td>As with the --name-servers option, this can be used to specify the default domain search line. Users with DHCP
  setups should not need to use this option. This is available to set in profiles to avoid having to set it repeatedly
  for each system record.</td>
 </tr>
 <tr>
  <td class="nowrap">--owners</td>
  <td>
   <p>The value for --owners is a space seperated list of users and groups as specified in
   <code>/etc/cobbler/users.conf</code>.</p>
   <p>Users with small sites and a limited number of admins can probably ignore this option, since it only applies to
   the Cobbler WebUI and XMLRPC interface, not the "cobbler" command line tool run from the shell. Furthermore, this is
   only respected when using the "authz_ownership" module which must be enabled and is not the default.</p>
   <p>Please see the [Web Authorization]({% link manuals/2.8.0/5/3_-_Web_Authorization.md %}) section for more
   details.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--parent</td>
  <td>
   <p>This is an advanced feature.</p>
   <p>Profiles may inherit from other profiles in lieu of specifing --distro. Inherited profiles will override any
   settings specified in their parent, with the exception of --ksmeta (templating) and --kopts (kernel options), which
   will be blended together.</p>
   <p><b>Example:</b></p>
   <p>If profile A has --kopts="x=7 y=2", B inherits from A, and B has --kopts="x=9 z=2", the actual kernel options that
   will be used for B are "x=9 y=2 z=2".</p>
   <p><b>Example:</b></p>
   <p>If profile B has --virt-ram=256 and A has --virt-ram of 512, profile B will use the value 256.</p>
   <p><b>Example:</b></p>
   <p>If profile A has a --virt-file-size of 5 and B does not specify a size, B will use the value from A.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--proxy</td>
  <td>
   <p>Specifies a proxy to use during the installation stage.</p>
   <div class="alert alert-info alert-block"><b>Note:</b> Not all distributions support using a proxy in this
   manner.</div>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--redhat-management-key</td>
  <td>
   <p>If you’re using Red Hat Network, Red Hat Satellite Server, or Spacewalk, you can store your authentication keys
   here and Cobbler can add the neccessary authentication code to your kickstart where the snippet named
   "redhat_register" is included. The default option specified in
   [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) will be used if this field is left blank.</p>
   <p>Please see the [Tips For RHN]({% link manuals/2.8.0/Appendix/C_-_Tips_for_RHN.md %}) section for more details on
   integrating Cobbler with RHN/Spacewalk.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--redhat-management-server</td>
  <td>
   <p>The RHN Satellite or Spacewalk server to use for registration. As above, the default option specified in
   [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) will be used if this field is left blank.</p>
   <p>Please see the [Tips For RHN]({% link manuals/2.8.0/Appendix/C_-_Tips_for_RHN.md %}) section for more details on
   integrating Cobbler with RHN/Spacewalk.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--repos</td>
  <td>This is a space delimited list of all the repos (created with "cobbler repo add" and updated with "cobbler reposync") that this profile can make use of during kickstart installation. For example, an example might be --repos="fc6i386updates fc6i386extras" if the profile wants to access these two mirrors that are already mirrored on the cobbler server. Repo management is described in greater depth later in the manpage.</td>
 </tr>
 <tr>
  <td class="nowrap">--server</td>
  <td>This parameter should be useful only in select circumstances. If machines are on a subnet that cannot access the cobbler server using the name/IP as configured in the cobbler settings file, use this parameter to override that server name. See also --dhcp-tag for configuring the next server and DHCP informmation of the system if you are also using Cobbler to help manage your DHCP configuration.</td>
 </tr>
 <tr>
  <td class="nowrap">--template-files</td>
  <td>
   <p>This feature allows cobbler to be used as a configuration management system. The argument is a space delimited string of key=value pairs. Each key is the path to a template file, each value is the path to install the file on the system. Koan also can retrieve these files from a cobbler server on demand, effectively allowing cobbler to function as a lightweight templated configuration management system.</p>
   <p>Please see the
   [Built-In Configuration Management]({% link manuals/2.8.0/4/3/1_-_Built-In_Configuration_Management.md %}) section
   for more details on using template files.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--template-remote-kickstarts</td>
  <td>If enabled, any kickstart with a remote path (http://, ftp://, etc.) will not be passed through Cobbler's template engine.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-auto-boot</td>
  <td><b>(Virt-only)</b> When set, the VM will be configured to automatically start when the host reboots.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-bridge</td>
  <td><b>(Virt-only)</b> This specifies the default bridge to use for all systems defined under this profile. If not specified, it will assume the default value in the cobbler settings file, which as shipped in the RPM is ’xenbr0’. If using KVM, this is most likely not correct. You may want to override this setting in the system object. Bridge settings are important as they define how outside networking will reach the guest. For more information on bridge setup, see the Cobbler Wiki, where there is a section describing koan usage.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-cpus</td>
  <td><b>(Virt-only)</b> How many virtual CPUs should koan give the virtual machine? The default for this value is set
  in the [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) file, and should be set as an integer.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-disk-driver</td>
  <td><b>(Virt-only)</b> The type of disk driver to use for the disk image, for example "raw" or "qcow2".</td>
 </tr>
 <tr>

  <td class="nowrap">--virt-file-size</td>
  <td><b>(Virt-only)</b> How large the disk image should be in Gigabytes. The default for this value is set in the
  [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) file. This can be a space seperated list (ex:
  "5,6,7") to allow for multiple disks of different sizes depending on what is given to --virt-path. This should be
  input as a integer or decimal value without units.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-path</td>
  <td>
   <p><b>(Virt-only)</b> Where to store the virtual image on the host system. Except for advanced cases, this parameter
   can usually be omitted. For disk images, the value is usually an absolute path to an existing directory with an
   optional file name component. There is support for specifying partitions "/dev/sda4" or volume groups "VolGroup00",
   etc.</p>
   <p>For multiple disks, seperate the values with commas such as "VolGroup00,VolGroup00" or "/dev/sda4,/dev/sda5". Both
   those examples would create two disks for the VM.</p>
  </td>
 </tr>
 <tr>
  <td class="nowrap">--virt-ram</td>
  <td><b>(Virt-only)</b> How many megabytes of RAM to consume. The default for this value is set in the
  [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) file. This should be input as an integer
  without units, and will be interpretted as MB.</td>
 </tr>
 <tr>
  <td class="nowrap">--virt-type</td>
  <td><b>(Virt-only)</b> Koan can install images using several different virutalization types. Choose one or the other
  strings to specify, or values will default to attempting to find a compatible installation type on the client system
  ("auto"). See the [Koan]({% link manuals/2.8.0/6_-_Koan.md %}) section for more documentation. The default for this
  value is set in the [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) file.</td>
 </tr>
 <tr>
</tbody>
</table>

Get Kickstart (getks)
*********************

The getks command shows the rendered kickstart/response file (preseed, etc.) for the given profile. This is useful for
previewing what will be downloaded from Cobbler when the system is building. This is also a good opportunity to catch
snippets that are not rendering correctly.

As with remove, the ``--name`` option is required and is the only valid argument.

**Example:**

.. code-block:: bash

    $ cobbler profile getks --name=foo | less

Systems
=======

System records map a piece of hardware (or a virtual machine) with the cobbler profile to be assigned to run on it. This
may be thought of as chosing a role for a specific system.

The system commmand has the following sub-commands:

.. code-block:: bash

    $ cobbler system --help
    usage
    =====
    cobbler system add
    cobbler system copy
    cobbler system dumpvars
    cobbler system edit
    cobbler system find
    cobbler system getks
    cobbler system list
    cobbler system poweroff
    cobbler system poweron
    cobbler system powerstatus
    cobbler system reboot
    cobbler system remove
    cobbler system rename
    cobbler system report

Note that if provisioning via koan and PXE menus alone, it is not required to create system records in cobbler, though
they are useful when system specific customizations are required. One such customization would be defining the MAC
address. If there is a specific role inteded for a given machine, system records should be created for it.

System commands have a wider variety of control offered over network details. In order to use these to the fullest
possible extent, the kickstart template used by cobbler must contain certain kickstart snippets (sections of code
specifically written for Cobbler to make these values become reality). Compare your kickstart templates with the stock
ones in ``/var/lib/cobbler/kickstarts`` if you have upgraded, to make sure you can take advantage of all options to
their fullest potential. If you are a new cobbler user, base your kickstarts off of these templates. Non-kickstart based
distributions, while supported by Cobbler, may not be able to use all of these features.

**Example:**

.. code-block:: bash

    $ cobbler system add --name=string [--profile=name|--image=name] [options]

As you can see, a system must either be assigned to a ``--profile`` or an ``--image``, which are mutually exclusive
options.

Add/Edit Options
****************

--name (required)
+++++++++++++++++

The system name works like the name option for other commands.

If the name looks like a MAC address or an IP, the name will implicitly be used for either ``--mac`` or ``--ip-address``
of the first interface, respectively. However, it’s usually better to give a descriptive name -- don’t rely on this
behavior.

A system created with name "default" has special semantics. If a default system object exists, it sets all undefined
systems to PXE to a specific profile. Without a "default" system name created, PXE will fall through to local boot for
unconfigured systems.

When using "default" name, don’t specify any other arguments than ``--profile`` ... they won’t be used.

--profile (required, if --image not set)
++++++++++++++++++++++++++++++++++++++++

The name of the profile or sub-profile to which this system belongs.

--image (required, if --profile not set)
++++++++++++++++++++++++++++++++++++++++

The name of the image to which this system belongs.

--boot-files
++++++++++++

This option is used to specify additional files that should be copied to the TFTP directory for the distro so that they
can be fetched during earlier stages of the installation. Some distributions (for example, VMware ESXi) require this
option to function correctly.

--clobber
+++++++++

This option allows "add" to overwrite an existing system with the same name, so use it with caution.

--comment
+++++++++

An optional comment to associate with this system.

--enable-gpxe
+++++++++++++

When enabled, the system will use gPXE instead of regular PXE for booting.

Please refer to the :ref:`using-gpxe` section for details on using gPXE for booting over a network.

--fetchable-files
+++++++++++++++++

This option is used to specify a list of ``key=value`` files that can be fetched via the python based TFTP server. The
"value" portion of the name is the path/name they will be available as via TFTP.

Please see the [Managing TFTP]({% link manuals/2.8.0/3/4/4_-_Managing_TFTP.md %}) section for more details on using the
python-based TFTP server.

--gateway
+++++++++

Sets the default gateway, which in Redhat-based systems is typically in ``/etc/sysconfig/network``. Per-interface
gateways are not supported at this time. This option will be ignored unless ``--static=1`` is also set on the interface.

--hostname
++++++++++

This field corresponds to the hostname set in a systems ``/etc/sysconfig/network`` file. This has no bearing on DNS,
even when ``manage_dns`` is enabled. Use ``--dns-name`` instead for that feature, which is a per-interface setting.

--in-place
++++++++++

By default, any modifications to ``key=value`` fields (``ksmeta``, ``kopts``, etc.) do no preserve the contents. To
preserve the contents of these fields, ``--in-place`` should be specified. This option is also required is using a key
with multiple values (for example, ``foo=bar foo=baz``).

--kickstart
+++++++++++

While it is recommended that the ``--kickstart`` parameter is only used within for the "profile add" command, there are
limited scenarios when an install base switching to cobbler may have legacy kickstarts created on a per-system basis
(one kickstart for each system, nothing shared) and may not want to immediately make use of the cobbler templating
system. This allows specifing a kickstart for use on a per-system basis. Creation of a parent profile is still required.
If the kickstart is a filesystem location, it will still be treated as a cobbler template.

--kopts
+++++++

Sets kernel command-line arguments that the system will use during installation only. This field is a hash field, and
accepts a set of key=value pairs:

**Example:**

.. code-block:: bash

    --kopts="console=tty0 console=ttyS0,8,n,1 noapic"

--kopts-post
++++++++++++

This is just like ``--kopts``, though it governs kernel options on the installed OS, as opposed to kernel options fed
to the installer. This requires some special snippets to be found in your kickstart template to work correctly.

--ksmeta
++++++++

This is an advanced feature that sets variables available for use in templates. This field is a hash field, and accepts
a set of ``key=value`` pairs:

**Example:**

.. code-block:: bash

    --ksmeta="foo=bar baz=3 asdf"

See the section on :ref:`kickstart-templating` for further information.

--ldap-enabled, --ldap-type
+++++++++++++++++++++++++++

Cobbler contains features that enable ldap management for easier configuration after system provisioning. If set true,
koan will run the ldap command as defined by the systems ldap_type. The default value is false.

--mgmt-classes and --mgmt-parameters
++++++++++++++++++++++++++++++++++++

Management classes and parameters that should be associated with this system for use with configuration management
systems.

Please see the [Configuration Management]({% link manuals/2.8.0/4/3_-_Configuration_Management.md %}) section for more
details on integrating Cobbler with configuration management systems.

--monit-enabled
+++++++++++++++

.. warning:: This feature has been deprecated and will not be available in cobbler 3.0

If set true, koan will reload monit after each configuration run. The default value is false.

--name-servers
++++++++++++++

If your nameservers are not provided by DHCP, you can specify a space seperated list of addresses here to configure each
of the installed nodes to use them (provided the kickstarts used are installed on a per-system basis). Users with DHCP
setups should not need to use this option. This is available to set in profiles to avoid having to set it repeatedly for
each system record.

--name-servers-search
+++++++++++++++++++++

As with the ``--name-servers`` option, this can be used to specify the default domain search line. Users with DHCP
setups should not need to use this option. This is available to set in profiles to avoid having to set it repeatedly for
each system record.

--netboot-enabled
+++++++++++++++++

If set false, the system will be provisionable through koan but not through standard PXE. This will allow the system to
fall back to default PXE boot behavior without deleting the cobbler system object. The default value allows PXE. Cobbler
contains a PXE boot loop prevention feature (``pxe_just_once``, can be enabled in ``/etc/cobbler/settings``) that can
automatically trip off this value after a system gets done installing. This can prevent installs from appearing in an
endless loop when the system is set to PXE first in the BIOS order.

--owners
++++++++

The value for ``--owners`` is a space seperated list of users and groups as specified in ``/etc/cobbler/users.conf``.

--power-address, --power-type, --power-user, --power-password, --power-id
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Cobbler contains features that enable integration with power management for easier installation, reinstallation, and
management of machines in a datacenter environment. These parameters are described in the :ref:`power-management`
section under :ref:`advanced-topics`. If you have a power-managed datacenter/lab setup, usage of these features may be
something you are interested in.

--proxy
+++++++

Specifies a proxy to use during the installation stage.

.. note:: Not all distributions support using a proxy in this manner.

--redhat-management-key
+++++++++++++++++++++++

If you’re using Red Hat Network, Red Hat Satellite Server, or Spacewalk, you can store your authentication keys here and
Cobbler can add the neccessary authentication code to your kickstart where the snippet named "redhat_register" is
included. The default option specified in [Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) will be
used if this field is left blank.

Please see the :ref:`tips-for-rhn` section for more details on integrating Cobbler with RHN/Spacewalk.

--redhat-management-server
++++++++++++++++++++++++++

The RHN Satellite or Spacewalk server to use for registration. As above, the default option specified in :ref:`settings`
will be used if this field is left blank.

Please see the :ref:`tips-for-rhn` section for more details on integrating Cobbler with RHN/Spacewalk.

--repos-enabled
+++++++++++++++

If set true, koan can reconfigure repositories after installation.

--server
++++++++

This parameter should be useful only in select circumstances. If machines are on a subnet that cannot access the cobbler
server using the name/IP as configured in the cobbler settings file, use this parameter to override that server name.
See also ``--dhcp-tag`` for configuring the next server and DHCP informmation of the system if you are also using
Cobbler to help manage your DHCP configuration.

--status
++++++++

An optional field used to keep track of a systems build or deployment status. This field is only set manually, and is
not updated automatically at this time.

--template-files
++++++++++++++++

This feature allows cobbler to be used as a configuration management system. The argument is a space delimited string of
key=value pairs. Each key is the path to a template file, each value is the path to install the file on the system. Koan
also can retrieve these files from a cobbler server on demand, effectively allowing cobbler to function as a lightweight
templated configuration management system.

Please see the :ref:`config-management-built-in` section for more details on using template files.

--template-remote-kickstarts
++++++++++++++++++++++++++++

If enabled, any kickstart with a remote path (``http://``, ``ftp://``, etc.) will not be passed through Cobbler's
template engine.

--virt-auto-boot
++++++++++++++++

**(Virt-only)** When set, the VM will be configured to automatically start when the host reboots.

--virt-cpus
+++++++++++

**(Virt-only)** The number of virtual CPUs to allocate to a system. The default for this value is set in the
:ref:`settings` file, and should be set as an integer.

--virt-disk-driver
++++++++++++++++++

**(Virt-only)** The type of disk driver to use for the disk image, for example "raw" or "qcow2".

--virt-file-size
++++++++++++++++

**(Virt-only)** How large the disk image should be in Gigabytes. The default for this value is set in the
[Cobbler Settings]({% link manuals/2.8.0/3/3_-_Cobbler_Settings.md %}) file. This can be a space seperated list (ex:
"5,6,7") to allow for multiple disks of different sizes depending on what is given to `--virt-path`. This should be
input as a integer or decimal value without units.

--virt-path
+++++++++++

**(Virt-only)** Where to store the virtual image on the host system. Except for advanced cases, this parameter can
usually be omitted. For disk images, the value is usually an absolute path to an existing directory with an optional
file name component. There is support for specifying partitions ``/dev/sda4`` or volume groups ``VolGroup00``, etc.

For multiple disks, seperate the values with commas such as ``VolGroup00,VolGroup00`` or ``/dev/sda4,/dev/sda5``. Both
those examples would create two disks for the VM.

--virt-pxe-boot
+++++++++++++++

**(Virt-only)** When set, the guest VM will use PXE to boot. By default, koan will use the ``--location`` option to
virt-install to specify the installer for the guest.

--virt-ram
++++++++++

**(Virt-only)** How many megabytes of RAM to consume. The default for this value is set in the :ref:`settings` file.
This should be input as an integer without units, and will be interpretted as ``MB``.

--virt-type
+++++++++++

**(Virt-only)** Koan can install images using several different virutalization types. Choose one or the other strings to
specify, or values will default to attempting to find a compatible installation type on the client system ("auto"). See
the https://koan.readthedocs.io/ section for more documentation. The default for this value is set in the
:ref:`settings` file.

Interface Specific Commands
***************************

System primitives are unique in that they are the only object in Cobbler that embeds another complex
object - interfaces. As such, there is an entire subset of options that are specific to interfaces only.

--interface
+++++++++++

All interface options require the use of the ``--interface=ifname`` option. If this is omitted, Cobbler will default to
using the interface name "eth0", which may not be what you want. We may also change this default behavior in the future,
so in general it is always best to explicitly specify the interface name with this option.

.. note:: **You can only edit one interface at a time!** If you specify multiple ``--interface`` options, only the last
one will be used.

**Interface naming notes:**

Additional interfaces can be specified (for example: eth1, or any name you like, as long as it does not conflict with
any reserved names such as kernel module names) for use with the edit command. Defining VLANs this way is also
supported, if you want to add VLAN 5 on interface eth0, simply name your interface eth0:5.

**Example:**

.. code-block:: bash

    $ cobbler system edit --name=foo --ip-address=192.168.1.50 --mac=AA:BB:CC:DD:EE:A0
    $ cobbler system edit --name=foo --interface=eth0 --ip-address=192.168.1.51 --mac=AA:BB:CC:DD:EE:A1
    $ cobbler system report foo

Interfaces can be deleted using the ``--delete-interface`` option.

**Example:**

.. code-block:: bash

    $ cobbler system edit --name=foo --interface=eth2 --delete-interface

--bonding-opts and --bridge-opts
++++++++++++++++++++++++++++++++

Bonding and bridge options for the master-interface may be specified using --bonding-opts="foo=1 bar=2" or
`--bridge-opts="foo=1 bar=2"`, respectively. These are only used if the `--interface-type` is a master or
bonded_bridge_slave (which is also a bond master).

#### --dhcp-tag
If you are setting up a PXE environment with multiple subnets/gateways, and are using cobbler to manage a DHCP
configuration, you will probably want to use this option. If not, it can be ignored.

By default, the dhcp tag for all systems is "default" and means that in the DHCP template files the systems will expand
out where $insert_cobbler_systems_definitions is found in the DHCP template. However, you may want certain systems to
expand out in other places in the DHCP config file. Setting --dhcp-tag=subnet2 for instance, will cause that system to
expand out where $insert_cobbler_system_definitions_subnet2 is found, allowing you to insert directives to specify
different subnets (or other parameters) before the DHCP configuration entries for those particular systems.

--dns-name
++++++++++

If using the DNS management feature (see advanced section -- cobbler supports auto-setup of BIND and dnsmasq), use this
to define a hostname for the system to receive from DNS.

**Example:**

.. code-block:: bash

    --dns-name=mycomputer.example.com


This is a per-interface parameter. If you have multiple interfaces, it may be different for each interface, for example,
assume a DMZ/dual-homed setup.

--interface-type and --interface-master
+++++++++++++++++++++++++++++++++++++++

One of the other advanced networking features supported by Cobbler is NIC bonding and bridging. You can use this to bond
multiple physical network interfaces to one single logical interface to reduce single points of failure in your network,
or to create bridged interfaces for things like tunnels and virtual machine networks. Supported values for the
``--interface-type`` parameter are "bond", "bond_slave", "bridge", "bridge_slave" and "bonded_bridge_slave". If one of
the ``_slave`` options is specified, you also need to define the master-interface for this bond using
``--interface-master=INTERFACE``.

.. note:: The options ``master`` and ``slave`` are deprecated, and are assumed to me ``bond`` and ``bond_slave`` when
encountered. When a system object is saved, the deprecated values will be overwritten with the new, correct values.

For more details on using these interface types, please see the :ref:`advanced-networking` section.

--ip-address
++++++++++++

If cobbler is configured to generate a DHCP configuratition (see advanced section), use this setting to define a
specific IP for this system in DHCP. Leaving off this parameter will result in no DHCP management for this particular
system.

**Example:**

.. code-block:: bash

    --ip-address=192.168.1.50

Note for Itanium users: This setting is always required for IA64 regardless of whether DHCP management is enabled.

If DHCP management is disabled and the interface is labelled ``--static=1``, this setting will be used for static IP
configuration.

Special feature: To control the default PXE behavior for an entire subnet, this field can also be passed in using CIDR
notation. If ``--ip-address`` is CIDR, do not specify any other arguments other than ``--name`` and ``--profile``.

When using the CIDR notation trick, don’t specify any arguments other than ``--name`` and ``--profile``... they won’t be
used.

--ipv6-address
++++++++++++++

The IPv6 address to use for this interface.

.. note:: This is not mutually exclusive with the ``--ipv6-autoconfiguration`` option, as interfaces can have many
IPv6 addresses.

--ipv6-autoconfiguration
++++++++++++++++++++++++

Use autoconfiguration mode to obtain the IPv6 address for this interface.

--ipv6-default-device
+++++++++++++++++++++

The default IPv6 device.

--ipv6-secondaries
++++++++++++++++++

The list of IPv6 secondaries for this interface.

--ipv6-mtu
++++++++++

Same as ``--mtu``, however specific to the IPv6 stack for this interface.

--ipv6-static-routes
++++++++++++++++++++

Same as ``--static-routes``, however specific to the IPv6 stack for this interface.

--ipv6-default-gateway
++++++++++++++++++++++

This is the default gateway to use for this interface, specific only to the IPv6 stack. Unlike ``--gateway``, this is
set per-interface.

--mac-address (--mac)
+++++++++++++++++++++

Specifying a mac address via ``--mac`` allows the system object to boot directly to a specific profile via PXE,
bypassing cobbler’s PXE menu. If the name of the cobbler system already looks like a mac address, this is inferred from
the system name and does not need to be specified.

MAC addresses have the format ``AA:BB:CC:DD:EE:FF``. It’s higly recommended to register your MAC-addresses in Cobbler if
you’re using static adressing with multiple interfaces, or if you are using any of the advanced networking features like
bonding, bridges or VLANs.

Cobbler does contain a feature (enabled in ``/etc/cobbler/settings``) that can automatically add new system records when
it finds profiles being provisioned on hardware it has seen before. This may help if you do not have a report of all the
MAC addresses in your datacenter/lab configuration.

--mtu
+++++

Sets the MTU (max transfer unit) property for the interface. Normally, this is set to 9000 to enable jumbo frames, but
remember you must also enable it on in your switch configuration to function properly.

--management
++++++++++++

When set to true, this interface will take precedence over others as the communication link to the Cobbler server. This
means it will be used as the default kickstart interface if there are multiple interfaces to choose from.

--static
++++++++

Indicates that this interface is statically configured. Many fields (such as gateway/subnet) will not be used unless
this field is enabled. When Cobbler is managing DHCP, this will result in a static lease entry being created in the
``dhcpd.conf``.

--static-routes
+++++++++++++++

This is a space delimited list of ip/mask:gateway routing information in that format, which will be added as extra
routes on the system. Most systems will not need this information.

.. code-block:: bash

    --static-routes="192.168.1.0/16:192.168.1.1 172.16.0.0/16:172.16.0.1"

--netmask (formerly --subnet)
+++++++++++++++++++++++++++++

This is the netmask of the interface, for example 255.255.255.0.

--virt-bridge
+++++++++++++

**(Virt-only)** When specified, koan will associate the given interface with the physical bridge on the system. If no
bridge is specified, this value will be inherited from the profile, which in turn may be inherited from the default virt
bridge configured in :ref:`settings`.

Get Kickstart (getks)
*********************

The getks command shows the rendered kickstart/response file (preseed, etc.) for the given system. This is useful for
previewing what will be downloaded from Cobbler when the system is building. This is also a good opportunity to catch
snippets that are not rendering correctly.

As with remove, the ``--name`` option is required and is the only valid argument.

**Example:**

.. code-block:: bash

    $ cobbler system getks --name=foo | less

Power Commands
**************

By configuring the ``--power-*`` options above, Cobbler can be used to power on/off and reboot systems in your
environment.

**Example:**

.. code-block:: bash

    $ cobbler system poweron --name=foo

Please see the :ref:`power-management` section for more details on using these commands.

Images
======

Cobbler can help with booting images physically and virtually, though the usage of these commands varies substantially
by the type of image. Non-image based deployments are generally easier to work with and lead to more sustaintable
infrastructure.

Repos
=====

Repository mirroring allows cobbler to mirror not only install trees ("cobbler import" does this for you) but also
optional packages, 3rd party content, and even updates. Mirroring all of this content locally on your network will
result in faster, more up-to-date installations and faster updates.  If you are only provisioning a home setup, this
will probably be overkill, though it can be very useful for larger setups (labs, datacenters, etc).  For information on
how to keep your mirror up-to-date, see [Reposync]({% link manuals/2.8.0/3/2/5_-_Reposync.md %}).

Example:

.. code-block:: bash

    $ cobbler repo add --mirror=url --name=string [--rpmlist=list] [--creatrepo-flags=string] \
    [--keep-updated=Y/N] [--priority=number] [--arch=string] [--mirror-locally=Y/N] [--breed=yum|rsync|rhn]

mirror
******

The addresss of the yum mirror.  This can be an rsync:// URL, an ssh location, or a http:// or ftp:// mirror location.
Filesystem paths also work.

The mirror address should specify an exact repository to mirror -- just one architecture and just one distribution. If
you have a seperate repo to mirror for a different arch, add that repo seperately.

Example:

.. code-block:: bash

    rsync://yourmirror.example.com/fedora-linux-core/updates/6/i386 (for rsync protocol)
    http://mirrors.kernel.org/fedora/extras/6/i386/ (for http://)
    user@yourmirror.example.com/fedora-linux-core/updates/6/i386  (for SSH)

Experimental support is also provided for mirroring RHN content when you need a fast local mirror. The mirror syntax for
this is ``--mirror=rhn://channel-name`` and you must have entitlements for this to work. This requires the cobbler
server to be installed on RHEL5 or later. You will also need a version of yum-utils equal or greater to 1.0.4.

name
****

This name is used as the save location for the mirror. If the mirror represented, say, Fedora Core 6 i386 updates, a
good name would be "fc6i386updates".  Again, be specific.

This name corresponds with values given to the ``--repos`` parameter of ``cobbler profile add``. If a profile has a
``--repos`` value that matches the name given here, that repo can be automatically set up during provisioning (when
supported) and installed systems will also use the boot server as a mirror (unless ``yum_post_install_mirror`` is
disabled in the settings file). By default the provisioning server will act as a mirror to systems it installs, which
may not be desirable for laptop configurations, etc.

Distros that can make use of yum repositories during kickstart include FC6 and later, RHEL 5 and later, and derivative distributions.

See the documentation on ``cobbler profile add`` for more information.

rpm-list
********

By specifying a space-delimited list of package names for ``--rpm-list``, one can decide to mirror only a part of a repo
(the list of packages given, plus dependencies). This may be helpful in conserving time/space/bandwidth. For instance,
when mirroring FC6 Extras, it may be desired to mirror just cobbler and koan, and skip all of the game packages. To do
this, use ``--rpm-list="cobbler koan"``.

This option only works for ``http://`` and ``ftp://`` repositories (as it is powered by yumdownloader). It will be
ignored for other mirror types, such as local paths and ``rsync://`` mirrors.

createrepo-flags
****************

Specifies optional flags to feed into the createrepo tool, which is called when ``cobbler reposync`` is run for the
given repository. The defaults are ``-c cache``.

keep-updated
************

Specifies that the named repository should not be updated during a normal ``cobbler reposync``. The repo may still be
updated by name. The repo should be synced at least once before disabling this feature See ``cobbler reposync`` below.

mirror-locally
**************

When set to "N", specifies that this yum repo is to be referenced directly via kickstarts and not mirrored locally on
the cobbler server. Only ``http://`` and ``ftp://`` mirror urls are supported when using ``--mirror-locally=N``, you
cannot use filesystem URLs.

priority
********

Specifies the priority of the repository (the lower the number, the higher the priority), which applies to installed
machines using the repositories that also have the yum priorities plugin installed. The default priority for the plugin
is 99, as is that of all cobbler mirrored repositories.

arch
****

Specifies what architecture the repository should use. By default the current system arch (of the server) is used, which
may not be desirable. Using this to override the default arch allows mirroring of source repositories (using
``--arch=src``).

yumopts
*******

Sets values for additional yum options that the repo should use on installed systems. For instance if a yum plugin takes
a certain parameter "alpha" and "beta", use something like ``--yumopts="alpha=2 beta=3"``.

breed
*****

Ordinarily cobbler’s repo system will understand what you mean without supplying this parameter, though you can set it
explicitly if needed.

Management Classes
==================

Management classes allow cobbler to function as a configuration management system. The lego blocks of configuration
management, resources are grouped together via Management Classes and linked to a system. Cobbler supports two (2)
resource types, which are configured in the order listed below:

1. :ref:`cobbler-primitives-package-resources`
2. :ref:`cobbler-primitives-file-resources`


To add a Management Class, you would run the following command:

.. code-block:: bash

    $ cobbler mgmtclass add --name=string --comment=string [--packages=list] [--files=list]

name
****

The name of the mgmtclass. Use this name when adding a management class to a system, profile, or distro. To add a
mgmtclass to an existing system use something like
(``cobbler system edit --name="madhatter" --mgmt-classes="http mysql"``).

comment
*******

A comment that describes the functions of the management class.

packages
********

Specifies a list of package resources required by the management class.

files
*****

Specifies a list of file resources required by the management class.

.. _cobbler-primitives-file-resources:

File Resources
==============

File resources are managed using cobbler file add, allowing you to create and delete files on a system.

Actions
*******

create
++++++

Create the file. [Default]

remove
++++++

Remove the file.

Attributes
**********

mode
++++

Permission mode (as in chmod).

group
+++++

The group owner of the file.

user
++++

The user for the file.

path
++++

The path for the file.

template
++++++++

The template for the file.

Example:
********

.. code-block:: bash

    $ cobbler file add --name=string --comment=string [--action=string] --mode=string --group=string \
    --user=string --path=string [--template=string]

.. _cobbler-primitives-package-resources:

Package Resources
=================

Package resources are managed using cobbler package add, allowing you to install and uninstall packages on a system
outside of your install process.

Actions
*******

install
+++++++

Install the package. [Default]

uninstall
+++++++++

Uninstall the package.

Attributes
**********

installer
+++++++++

Which package manager to use, vaild options [rpm|yum].

version
+++++++

Which version of the package to install.

Example:
********

.. code-block:: bash

    $ cobbler package add --name=string --comment=string [--action=install|uninstall] --installer=string \
    [--version=string]
