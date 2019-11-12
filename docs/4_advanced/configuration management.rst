************************
Configuration Management
************************

The initial provisioning of client systems with cobbler is just one component of their management. We also need to
consider how to continue to manage them using a configuration management system (CMS). Cobbler can help you provision
and introduce a CMS onto your client systems.

One option is cobbler's own lightweight CMS. For that, see the document
[Built in configuration management](Built in configuration management).

Here we discuss the other option: deploying a CMS such as puppet, cfengine, bcfg2, Chef, etc.

Cobbler doesn't force you to chose a particular CMS (or to use one at all), though it helps if you do some things to
link cobbler's profiles with the "profiles" of the CMS. This, in general, makes management of both a lot easier.

Note that there are two independent "variables" here: the possible client operating systems and the possible CMSes. We
don't attempt to cover all details of all combinations; rather we illustrate the principles and give a small number of
illustrative examples of particular OS/CMS combinations. Currently cobbler has better support for Redhat-based OSes and
for Puppet so the current examples tend to deal with this combination.

Background considerations
#########################

Machine lifecyle
****************

A typical computer has a lifecycle something like:

* installation
* initial configuration
* ongoing configuration and maintenance
* decommissioning

Typically installation happens once.  Likewise, the initial configuration happens once, usually shortly after
installation. By contrast ongoing configuration evolves over an extended period, perhaps of several years. Sometimes
part of that ongoing configuration may involve re-installing an OS from scratch.  We can regard this as repeating the
earlier phase.

We need not consider decommissioning here.

Installation clearly belongs (in our context) to Cobbler.  In a complementary manner, ongoing configuration clearly
belongs to the CMS. But what about initial configuration?

Some sites consider their initial configuration as the final phase of installation: in our context, that would put it at
the back end of Cobbler, and potentially add significant configuration-based complication to the installation-based
Cobbler set-up.

But it is worth considering initial configuration as the first step of ongoing configuration: in our context that would
put it as part of the CMS, and keep the Cobbler set-up simple and uncluttered.

Local package repositories
**************************

Give consideration to:

- local mirrors of OS repositories
- local repository of local packages
- local repository of pick-and-choose external packages

In particular consider having the packages for your chosen CMS in one of the latter.

Package management
******************

Some sites set up Cobbler always to deploy just a minimal subset of packages, then use the CMS to install many others in
a large-scale fashion.  Other sites may set up Cobbler to deploy tailored sets of packages to different types of
machines, then use the CMS to do relatively small-scale fine-tuning of that.

General scheme
##############

We need to consider getting Cobbler to install and automatically invoke the CMS software.

Set up Cobbler to include a package repository that contains your chosen CMS:

    cobbler repo add ...

Then (illustrating a Redhat/Puppet combination) set up the kickstart file to say something like:

    %packages
    puppet

    %post
    /sbin/chkconfig --add puppet

The detail may need to be more substantial, requiring some other associated local packages, files and configuration. You
may wish to manage this through [Kickstart snippets](Kickstart Snippets).

Built-In Configuration Management
#################################

Cobbler is not just an installation server, it can also enable two different types of ongoing configuration management
system (CMS):

- integration with an established external CMS such as [cfengine3](http://cfengine.com/) or
  [puppet](http://puppetlabs.com/), discussed [elsewhere](Using cobbler with a configuration management system);
- its own, much simpler, lighter-weight, internal CMS, discussed here.

## Setting up

Cobbler's internal CMS is focused around packages and templated configuration files, and installing these on client
systems.

This all works using the same [Cheetah-powered](http://cheetahtemplate.org) templating engine used in
[KickstartTemplating](/cobbler/cobbler/wiki/KickstartTemplating), so once you learn about the power of treating your
distribution answer files as templates, you can use the same templating to drive your CMS configuration files.

For example:

    cobbler profile edit --name=webserver \
      --template-files=/srv/cobbler/x.template=/etc/foo.conf

A client system installed via the above profile will gain a file "/etc/foo.conf" which is the result of rendering the
template given by "/srv/cobbler/x.template". Multiple files may be specified; each "template=destination" pair should be
placed in a space-separated list enclosed in quotes:

    --template-files="srv/cobbler/x.template=/etc/xfile.conf srv/cobbler/y.template=/etc/yfile.conf"

## Template files

Because the template files will be parsed by the Cheetah parser, they must conform to the guidelines described in
[Kickstart Templating](Kickstart Templating). This is particularly important when the file is generated outside a
Cheetah environment. Look for, and act on, Cheetah 'ParseError' errors in the Cobbler logs.

Template files follows general Cheetah syntax, so can include Cheetah variables. Any variables you define anywhere in
the cobbler object hierarchy (distros, profiles, and systems) are available to your templates. To see all the variables
available, use the command:

    cobbler profile dumpvars --name=webserver

Cobbler snippets and other advanced features can also be employed.

## Ongoing maintenance

Koan can pull down files to keep a system updated with the latest templates and variables:

    koan --server=cobbler.example.org --profile=foo --update-files

You could also use `--server=bar` to retrieve a more specific set of templating.(???) Koan can also autodetect the
server if the MAC address is registered.

## Further uses

This Cobbler/Cheetah templating system can serve up templates via the magic URLs (see "Leveraging Mod Python" below). To
do this ensure that the destination path given to any `--template-files` element is relative, not absolute; then Cobbler
and koan won't download those files.

For example, in:

    cobbler profile edit --name=foo \
      --template-files="/srv/templates/a.src=/etc/foo/a.conf /srv/templates/b.src=1"

cobbler and koan would automatically download the rendered "a.src" to replace the file "/etc/foo/a.conf", but the b.src
file would not be downloaded to anything because the destination pathname "1" is not absolute.

This technique enables using the Cobbler/Cheetah templating system to build things that other systems can fetch and use,
for instance, BIOS config files for usage from a live environment.

## Leveraging Mod Python

All template files are generated dynamically at run-time. If a change is made to a template, a `--ks-meta` variable or
some other variable in cobbler, the result of template rendering will be different on subsequent runs. This is covered
in more depth in the [Developer documentation](Developer documentation).

## Possible future developments

* Serving and running scripts via `--update-files` (probably staging them through "/var/spool/koan").
* Auto-detection of the server name if `--ip` is registered.

Puppet Integration
##################

This example is relatively advanced, involving Cobbler "mgmt-classes" to control different types of initial
configuration. But if instead you opt to put most of the initial configuration into the Puppet CMS rather than here,
then things could be simpler.

### Keeping Class Mappings In Cobbler

First, we assign management classes to distro, profile, or system objects.

    cobbler distro edit --name=distro1 --mgmt-classes="distro1"
    cobbler profile add --name=webserver --distro=distro1 --mgmt-classes="webserver likes_llamas" --kickstart=/etc/cobbler/my.ks
    cobbler system edit --name=system --profile=webserver --mgmt-classes="orange" --dns-name=system.example.org

For Puppet, the --dns-name (shown above) must be set because this is what puppet will be sending to cobbler and is how
we find the system. Puppet doesn't know about the name of the system object in cobbler. To play it safe you probably
want to use the FQDN here (which is also what you want if you were using Cobbler to manage your DNS, which you don't
have to be doing).

### External Nodes

For more documentation on Puppet's external nodes feature, see docs.puppetlabs.com

Cobbler provides one, so configure puppet to use
`/usr/bin/cobbler-ext-nodes`:

    [main]
    external_nodes = /usr/bin/cobbler-ext-nodes

<div class="alert alert-info alert-block"><b>Note:</b> if you are using puppet 0.24 or later then you will want to</div>
also add the following to your configuration file

    node_terminus = exec

You may wonder what this does. This is just a very simple script that grabs the data at the following URL, which is a
URL that always returns a YAML document in the way that Puppet expects it to be returned. This file contains all the
parameters and classes that are to be assigned to the node in question. The magic URL being visited is powered by
Cobbler.

    http://cobbler/cblr/svc/op/puppet/hostname/foo


And this will return data such as:

    ---
    classes:
        - distro1
        - webserver
        - likes_llamas
        - orange
    parameters:
        tree: 'http://.../x86_64/tree'

Where do the parameters come from? Everything that cobbler tracks in `--ks-meta` is also a parameter. This way you can
easily add parameters as easily as you can add classes, and keep things all organized in one place.

What if you have global parameters or classes to add? No problem. You can also add more classes by editing the following
fields in `/etc/cobbler/settings`:

    mgmt_classes: []
    mgmt_parameters:
       from_cobbler: 1

### Alternate External Nodes Script

Attached at puppet\_node.py is an alternate external node script that fills in the nodes with items from a manifests
repository (at `/etc/puppet/manifests/`) and networking information from cobbler. It is configured like the above from
the puppet side, and then looks for `/etc/puppet/external_node.yaml` for cobbler side configuration.

The configuration is as follows.

    base: /etc/puppet/manifests/nodes
    cobbler: <%= cobbler_host %>
    no_yaml: puppet::noyaml
    no_cobbler: network::nocobbler
    bad_yaml: puppet::badyaml
    unmanaged: network::unmanaged

The output for network information will be in the form of a pseudo data structure that allows puppet to split it apart
and create the network interfaces on the node being managed.

Func Integration
################

<div class="alert alert-info alert-block">
    <b>Warning:</b> This feature has been deprecated and will not be available in Cobbler 3.0.
</div>

Func is a neat tool, (which, in full disclosure, Michael had a part in creating).

## Integration

Cobbler makes it even easier to deploy Func though. We have two settings in `/etc/cobbler/settings`:

    func_master: overlord.example.org
    func_auto_setup: 1

This will make sure the right packages are in packages for each kickstart and the right bits are automatically in %post
to set it up... so a new user can set up a cobbler server, set up a func overlord, and automatically have all their new
kickstarts configurable to point at that overlord.

This will be available in all the sample kickstart files, but will be off by default. To enable this feature all you
need to do then is set up

## How This Is Implemented

This is all powered by cobbler's [Kickstart Templating](Kickstart Templating) and
[Kickstart Snippets](Kickstart Snippets) feature, with two snippets that ship stock in `/var/lib/cobbler/snippets`

    %packages
    koan
    ...
    $func_install_if_enabled

    %post
    ...
    SNIPPET:func_register_if_enabled

If curious you can read the implementations in `/var/lib/cobbler/snippets` and these are of course controlled by the
aforemented values in settings.

The "func\_register\_if\_enabled" snippet is pretty basic.

It configures func to point to the correct certmaster to get certificates and enables the service. When the node boots
into the OS it will request the certificate (see note on autosigning below) and func is now operational. If there are
problems, see `/var/log/func` and `/var/log/certmaster` for debugging info (or other resources and information on the
Func Wiki page).

## Notes about Func Autosigning

This may work better for you if you are using Func autosigning, otherwise the administrator will need to use
certmaster-ca --sign hostname (see also certmaster-ca --list) to deal with machines.

Not using autosigning is good if you don't trust all the hosts you are provisioning and don't want to enslave unwanted
machines.

Either choice is ok, just be aware of the manual steps required if you don't enable it, or the implications if you do.

## Package Hookup

If you are not already using Cobbler to mirror package content, you are going to want to, so that you can make the func
packages available to your systems -- they are not part of the main install "tree".

Thankfully Cobbler makes this very simple -- see [Manage Yum Repos](Manage Yum Repos) for details

### for Fedora

Func is part of the package set for Fedora, but you need to mirror the "Everything" repo to get at it. Therefore you
will want to mirror "Everything" and make it available to your cobbler profiles so you can effectively put func on your
installed machines. You will also want to mirror "updates" to make sure you get the latest func.

An easy way to mirror these with cobbler is just:

    cobbler repo add --name=f10-i386-updates --mirror=http://download.fedora.redhat.com/pub/fedora/linux/updates/10/i386/
    cobbler repo add --name=f10-i386-everything --mirror=http://download.fedora.redhat.com/pub/fedora/linux/releases/10/Everything/i386/os/Packages/

Then you need to make sure that every one of your Fedora profiles is set up to use the appropriate repos:

    cobbler profile edit --name=f10-profile-name-goes-here --repos="f10-i386-updates f10-i386-everything"

And then you would probably want to put 'cobbler reposync' on cron so you keep installing the latest func, not an older func.

### for Enterprise Linux 4 and 5

As with Fedora, you'll need to configure your systems as above to get func onto them, and that is not included as part
of the Func integration process. RHEL 5 uses yum, so it can follow similar instructions as above. That's very simple. In
those cases you will just want to mirror the repositories for EPEL:

    cobbler repo add --name=el-5-i386-epel --mirror=http://download.fedora.redhat.com/pub/epel/5/i386
    cobbler repo add --name=el-5-i386-epel-testing --mirror=http://download.fedora.redhat.com/pub/epel/testing/5/i386

Of course in the above you would want to substitute '4' for '5' if neccessary and also 'i386' for 'x86\_64' if
neccessary. You will probably want to mirror multiples of the above. Cobbler doesn't care, just go ahead and do it. If
you have space concerns, as discussed on [Manage Yum Repos](Manage Yum Repos) you can use the --rpm-list parameter to do
partial yum mirroring.

Once you do this, you will need to make sure your EL profiles (for those that support yum, i.e. the EL 5 and later ones)
know about the repos and attach to them automatically:

    cobbler profile edit --name=el5-profile-name-goes-here --repos="el-5-i386-epel el-5-i386-epel-testing"

Another simple option is to just put the func RPMs on a webserver somewhere and wget them from the installer so they are
available at install time, you would do this as the very first step in post.

    %post
    wget http://myserver.example.org/func-version.rpm -O /tmp/func.rpm
    rpm -i /tmp/func.rpm

## Func Questions

See \#func on irc.freenode.net and func-list@redhat.com

Conclusion
##########

Hopefully this should get you started in linking up your provisioning configuration with your CMS implementation. The
examples provided are for Puppet, but we can (in the future) presumably extend --mgmt-classes to work with other
tools... just let us know what you are interested in, or perhaps take a shot at creating a patch for it.

