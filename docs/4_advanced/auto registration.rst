*****************
Auto registration
*****************

You have a lot of machines coming right "off the truck" and you want to plug them in, install them however (perhaps
using PXE menus, koan with --profile, a live CD, etc) and then have the system mac address recorded in cobbler so you
can change things later.

In the simplest of use cases, you could set up a cobbler default profile that did nothing more than serve up a mostly
blank kickstart, set up a post install trigger to email your admin, and then all turned on machines would register
automagically, and then you could reassign them to other profiles using the cobbler command line tools.
(See [Triggers](Triggers))

There are then quite a few ways in which you might want to use this.

## Warning

Though this feature cannot overwrite system records, it does have the ability to create a /LOT/ of cobbler system
records remotely if someone wanted to write a script to do it. It should not be enabled on a public network, so use your
judgement. In most cases it's perfectly safe.

For instance, this was originally written for FreeLinuxPC.org, which had a large amount of machines on a private network
that was for installation purposes only. On a restricted installation-only subnet this should be fine.

## How It Works

A tool called "cobbler-register" is installed as part of the koan package.

There is also a [Kickstart Snippets](Kickstart Snippets) that is in every default kickstart that says "if this feature
is enabled in the settings file, and this is a profile based install, register this system automatically in %post to
create a system record for this system if it did not already exist.

If you want to run cobbler-register over SSH instead that works too.

cobbler-register is smart and will set all fields to "netboot disabled" to prevent newly registered systems from being
reinstalled unless you ask them to be.

    cobbler-register [---server=cobbler.example.org] --profile=name [--hostname=override-hostname.example.org]

The server will be sourced from the environment variable COBBLER\_SERVER if installed previously with cobbler, meaning
you won't need to provide it in many cases. The hostname can also be used if available.

This registration script will populate all physical interfaces found, including IP, MAC, and netmask info. The user may
wish to fill in additional information later by a script or using web interface or the command line -- not everything
can be autodetected.
