.. _power-management:

****************
Power Management
****************

Cobbler allows for linking your power management systems with cobbler, making it very easy to make changes to your
systems when you want to reinstall them, or just use it to remember what the power management settings for all of your
systems are. For instance, you can just change what profile they should run and flip their power states to begin the
reinstall!

Fence Agents
############

Cobbler relies on fencing agents, provided by the 'cman' package for some distributions or 'fence-agents' for others.
These scripts are installed in the `/usr/sbin` directories. Cobbler will automatically find any files in that directory
named fence_* and allow them to be used for power management.

**NOTE:** Some distros may place the fencing agents in `/sbin` - this is currently a known bug. To work around this for
now, symlink the `/sbin/fence_*` scripts you wish to use to `/usr/sbin` so cobbler can find them. This will be fixed in
a future version.

Changes From Older Versions
###########################

Cobbler versions prior to 2.2.3-2 used templates stored in `/etc/cobbler/power` to generate commands that were run as
shell commands. This was changed in 2.2.3-2 to use the fencing agents ability to instead read the parameters from STDIN.
This is safer, as no passwords are shown in plaintext command line options, nor can a malformed variable be used to
inject improper shell commands during the fencing agent execution.

New Power Templates
*******************

By default, the following options are passed in to the fencing agent's STDIN:

{% highlight bash %}
action=$power_mode
login=$power_user
passwd=$power_pass
ipaddr=$power_address
port=$power_id
{% endhighlight %}

The variables above correspond to the --power-* options available when adding/editing a system (or via the
"Power Management" tab in the Web UI). If you wish to add aditional options, you can create a template in
`/etc/cobbler/power` named fence_&lt;name&gt;.template, where name is the fencing agent you wish to use.

Any additional options should be added one per line, as described in the fencing agents man page. Additional variables
can be used if they are set in --ksmeta.

Custom Fencing Agents
*********************

If you would like to use a custom fencing agent not provided by your distribution, you can do so easily by placing it in
the `/usr/sbin` directory and name it fence_&lt;mytype&gt;. Just make sure that your custom program reads its options
from STDIN, as noted above.

## Defaults

If --power-user and --power-pass are left blank, the values of default\_power\_user and default\_power\_pass will be
loaded from cobblerd's environment at the time of usage.

--power-type also has a default value in `/etc/cobbler/settings`, initially set to "ipmilan".

Important: Security Implications
################################

Storing the power control usernames and passwords in Cobbler means that information is essentially public (this data is
available via XMLRPC without access control), therefore you will want to control what machines have network access to
contact the power management devices if you use this feature (such as /only/ the cobbler machine, and then control who
has local access to the cobbler machine). Also do not reuse important passwords for your power management devices. If
this concerns you, you can still use this feature, just don't store the username/password in Cobbler for your power
management devices.

If you are not going to to store power control passwords in Cobbler, leave the username and password fields blank.
Cobbler will first try to source them from it's environment using the COBBLER\_POWER\_USER and COBBLER\_POWER\_PASS
variables.

This may also be too insecure for some, so in this case, don't set these, and supply --power-user and --power-pass when
running commands like "cobbler system poweron" and "cobbler system poweroff". The values used on the command line are
always used, regardless of the value stored in Cobbler or the environment, if so provided.

{% highlight bash %}
$ cobbler system poweron --name=foo --power-user=X --power-pass=Y
{% endhighlight %}

Be advised of current limitations in storing passwords, make your choices accordingly and in relation to the ease-of-use
that you need, and secure your networks appropriately.

Sample Use
##########

Configuring Power Options on a System
*************************************

You have a DRAC based blade:

{% highlight bash %}
$ cobbler system edit --name=foo --power-type=drac --power-address=blade-mgmt.example.org --power-user=Administrator --power-pass=PASSWORD --power-id=blade7
{% endhighlight %}

You have an IPMI based system:

{% highlight bash %}
$ cobbler system edit --name=foo --power-type=ipmilan --power-address=foo-mgmt.example.org --power-user=Administrator --power-pass=PASSWORD
{% endhighlight %}

You have a IBM HMC managed system:

{% highlight bash %}
$ cobbler system edit --name=foo --power-type=lpar --power-address=ibm-hmc.example.org --power-user=hscroot --power-pass=PASSWORD --power-id=system:partition
{% endhighlight %}

**NOTE**: The --power-id option is used to indicate both the managed system name **and** a logical partition name. Since
an IBM HMC is responsible for managing more than one system, you must supply the managed system name and logical
partition name separated by a colon (':') in the --power-id command-line option.

You have an IBM Bladecenter:

{% highlight bash %}
$ cobbler system edit --name=foo --power-type=bladecenter --power-address=blademm.example.org --power-user=USERID --power-pass=PASSW0RD --power-id=6
{% endhighlight %}

**NOTE**: The *--power-id* option is used to specify what slot your blade is connected.

### Powering Off A System

{% highlight bash %}
$ cobbler system poweroff --name=foo
{% endhighlight %}

Powering On A System
********************

{% highlight bash %}
$ cobbler system poweron --name=foo
{% endhighlight %}

If --netboot-enabled is not set to false, the system could potentially reinstall itself if PXE has been configured, so
make sure to disable that option when using power management features.

Rebooting A System
******************

{% highlight bash %}
$ cobbler system reboot --name=foo
{% endhighlight %}

Since not all power management systems support reboot, this is a "power off, sleep for 1 second, and power on"
operation.