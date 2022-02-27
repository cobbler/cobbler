.. _configuration-management:

*************************************
Configuration Management Integrations
*************************************

Cobbler contains features for integrating an installation environment with a configuration management system, which
handles the configuration of the system after it is installed by allowing changes to configuration files and settings.

Resources are the lego blocks of configuration management. Resources are grouped together via Management Classes, which
are then linked to a system. Cobbler supports two (2) resource types. Resources are configured in the order listed
below.

The initial provisioning of client systems with cobbler is just one component of their management. We also need to
consider how to continue to manage them using a configuration management system (CMS). Cobbler can help you provision
and introduce a CMS onto your client systems.

One option is cobbler's own lightweight CMS. For that, see the document `Built-In Configuration Management`_.

Here we discuss the other option: deploying a CMS such as `cfengine3 <http://cfengine.com/>`_,
`puppet <http://puppetlabs.com/>`_, `bcfg2 <http://bcfg2.org>`_, `Chef <http://wiki.opscode.com/display/chef/Home>`_,
etc.

Cobbler doesn't force you to chose a particular CMS (or to use one at all), though it helps if you do some things to
link cobbler's profiles with the "profiles" of the CMS. This, in general, makes management of both a lot easier.

Note that there are two independent "variables" here: the possible client operating systems and the possible CMSes. We
don't attempt to cover all details of all combinations; rather we illustrate the principles and give a small number of
illustrative examples of particular OS/CMS combinations. Currently cobbler has better support for Red Hat based OSes and
for Puppet so the current examples tend to deal with this combination.

Background considerations
#########################

Machine lifecycle
=================

A typical computer has a lifecycle something like:

* installation
* initial configuration
* ongoing configuration and maintenance
* decommissioning

Typically installation happens once. Likewise, the initial configuration happens once, usually shortly after
installation. By contrast ongoing configuration evolves over an extended period, perhaps of several years. Sometimes
part of that ongoing configuration may involve re-installing an OS from scratch. We can regard this as repeating the
earlier phase.

We need not consider decommissioning here.

Installation clearly belongs (in our context) to Cobbler. In a complementary manner, ongoing configuration clearly
belongs to the CMS. But what about initial configuration?

Some sites consider their initial configuration as the final phase of installation: in our context, that would put it at
the back end of Cobbler, and potentially add significant configuration-based complication to the installation-based
Cobbler set-up.

But it is worth considering initial configuration as the first step of ongoing configuration: in our context that would
put it as part of the CMS, and keep the Cobbler set-up simple and uncluttered.

Local package repositories
==========================

Give consideration to:

* local mirrors of OS repositories
* local repository of local packages
* local repository of pick-and-choose external packages

In particular consider having the packages for your chosen CMS in one of the latter.

Package management
==================

Some sites set up Cobbler always to deploy just a minimal subset of packages, then use the CMS to install many others in
a large-scale fashion. Other sites may set up Cobbler to deploy tailored sets of packages to different types of
machines, then use the CMS to do relatively small-scale fine-tuning of that.

General scheme
##############

We need to consider getting Cobbler to install and automatically invoke the CMS software.

Set up Cobbler to include a package repository that contains your chosen CMS:

.. code-block:: shell

    cobbler repo add ...

Then (illustrating a Red Hat/Puppet combination) set up the kickstart file to say something like:

.. code::

    %packages
    puppet

    %post
    /sbin/chkconfig --add puppet

The detail may need to be more substantial, requiring some other associated local packages, files and configuration. You
may wish to manage this through kickstart snippets.

David Lutterkort has a `walkthrough for kickstart <http://watzmann.net/blog/2006/12/kickstarting-into-puppet.html>`_.
While his example is written for Red Hat (Fedora) and Puppet, the principles are useful for other OS/CMS combinations.

Built-In Configuration Management
#################################

Cobbler is not just an installation server, it can also enable two different types of ongoing configuration management
system (CMS):

* integration with an established external CMS such as `cfengine3 <http://cfengine.com/>`_, `bcfg2 <http://bcfg2.org>`_,
  `Chef <http://wiki.opscode.com/display/chef/Home>`_, or `puppet <http://puppetlabs.com/>`_.
* its own, much simpler, lighter-weight, internal CMS, discussed here.

Setting up
==========

Cobbler's internal CMS is focused around packages and templated configuration files, and installing these on client
systems.

This all works using the same `Cheetah-powered <http://cheetahtemplate.org>`_ templating engine used in
kickstart templating, so once you learn about the power of treating your distribution answer
files as templates, you can use the same templating to drive your CMS configuration files.

For example:

.. code-block:: shell

    cobbler profile edit --name=webserver --template-files=/srv/cobbler/x.template=/etc/foo.conf

A client system installed via the above profile will gain a file ``/etc/foo.conf`` which is the result of rendering the
template given by ``/srv/cobbler/x.template``. Multiple files may be specified; each ``template=destination`` pair
should be placed in a space-separated list enclosed in quotes:

.. code-block:: shell

    --template-files="srv/cobbler/x.template=/etc/xfile.conf srv/cobbler/y.template=/etc/yfile.conf"

Template files
==============

Because the template files will be parsed by the Cheetah parser, they must conform to the guidelines described in
kickstart templating. This is particularly important when the file is generated outside a
Cheetah environment. Look for, and act on, Cheetah 'ParseError' errors in the Cobbler logs.

Template files follows general Cheetah syntax, so can include Cheetah variables. Any variables you define anywhere in
the cobbler object hierarchy (distros, profiles, and systems) are available to your templates. To see all the variables
available, use the command:

.. code-block:: shell

    cobbler profile dumpvars --name=webserver

Cobbler snippets and other advanced features can also be employed.

Ongoing maintenance
===================

Koan can pull down files to keep a system updated with the latest templates and variables:

.. code-block:: shell

    koan --server=cobbler.example.org --profile=foo --update-files

You could also use ``--server=bar`` to retrieve a more specific set of templating. Koan can also autodetect the server
if the MAC address is registered.

Further uses
============

This Cobbler/Cheetah templating system can serve up templates via the magic URLs (see "Leveraging Mod Python" below).
To do this ensure that the destination path given to any ``--template-files`` element is relative, not absolute; then
Cobbler and Koan won't download those files.

For example, in:

.. code-block:: shell

    cobbler profile edit --name=foo --template-files="/srv/templates/a.src=/etc/foo/a.conf /srv/templates/b.src=1"

Cobbler and koan would automatically download the rendered ``a.src`` to replace the file ``/etc/foo/a.conf``, but the
``b.src`` file would not be downloaded to anything because the destination pathname ``1`` is not absolute.

This technique enables using the Cobbler/Cheetah templating system to build things that other systems can fetch and use,
for instance, BIOS config files for usage from a live environment.

Leveraging Mod Python
=====================

All template files are generated dynamically at run-time. If a change is made to a template, a ``--ks-meta`` variable or
some other variable in Cobbler, the result of template rendering will be different on subsequent runs. This is covered
in more depth in the `Developer documentation <https://github.com/cobbler/cobbler/wiki>_`.

Possible future developments
============================

* Serving and running scripts via ``--update-files`` (probably staging them through ``/var/spool/koan``).
* Auto-detection of the server name if ``--ip`` is registered.

Terraform Provider
##################

This is developed and maintained by the Cobbler community. You will find more information in the docs under
https://registry.terraform.io/providers/cobbler/cobbler/latest/docs.

The code for the Terraform-Provider can be found at: https://github.com/cobbler/terraform-provider-cobbler

Ansible
#######

Official integration:

- https://docs.ansible.com/ansible/latest/collections/community/general/cobbler_inventory.html#ansible-collections-community-general-cobbler-inventory

Community provided integration:

- https://github.com/ac427/my_cm
- https://github.com/AnKosteck/ansible-cluster
- https://github.com/osism/ansible-cobbler
- https://github.com/hakoerber/ansible-roles

Saltstack
#########

Although we currently can not provide something official we can indeed link some community work here:

- https://github.com/hakoerber/salt-states/tree/master/cobbler

Vagrant
#######

Although we currently can not provide something official we can indeed link some community work here:

- https://github.com/davegermiquet/vmwarevagrantcobblercentos
- https://github.com/dratushnyy/tools
- https://github.com/mkusanagi/cobbler-kickstart-playground

Puppet
######

There is also an example of Puppet deploying Cobbler: https://github.com/gothicfann/puppet-cobbler

This example is relatively advanced, involving Cobbler "mgmt-classes" to control different types of initial
configuration. But if instead you opt to put most of the initial configuration into the Puppet CMS rather than here,
then things could be simpler.

Keeping Class Mappings In Cobbler
=================================

First, we assign management classes to distro, profile, or system
objects.

.. code-block:: shell

    cobbler distro edit --name=distro1 --mgmt-classes="distro1"
    cobbler profile add --name=webserver --distro=distro1 --mgmt-classes="webserver likes_llamas" --autoinstall=/etc/cobbler/my.ks
    cobbler system edit --name=system --profile=webserver --mgmt-classes="orange" --dns-name=system.example.org

For Puppet, the ``--dns-name`` (shown above) must be set because this is what puppet will be sending to cobbler and is
how we find the system. Puppet doesn't know about the name of the system object in cobbler. To play it safe you probably
want to use the FQDN here (which is also what you want if you were using Cobbler to manage your DNS, which you don't
have to be doing).

External Nodes
==============

For more documentation on Puppet's external nodes feature, see https://docs.puppetlabs.com.

Cobbler provides one, so configure puppet to use ``/usr/bin/cobbler-ext-nodes``:

.. code::

    [main]
    external_nodes = /usr/bin/cobbler-ext-nodes

Note: if you are using puppet 0.24 or later then you will want to also add the following to your configuration file.

.. code::

    node_terminus = exec

You may wonder what this does. This is just a very simple script that grabs the data at the following URL, which is a
URL that always returns a YAML document in the way that Puppet expects it to be returned. This file contains all the
parameters and classes that are to be assigned to the node in question. The magic URL being visited is powered by
Cobbler.

.. code::

    http://cobbler/cblr/svc/op/puppet/hostname/foo

(for developer information about this magic URL, visit https://fedorahosted.org/cobbler/wiki/ModPythonDetails)

And this will return data such as:

.. code::

    ---
    classes:
        - distro1
        - webserver
        - likes_llamas
        - orange
    parameters:
        tree: 'http://.../x86_64/tree'

Where do the parameters come from? Everything that cobbler tracks in ``--ks-meta`` is also a parameter. This way you can
easily add parameters as easily as you can add classes, and keep things all organized in one place.

What if you have global parameters or classes to add? No problem. You can also add more classes by editing the following
fields in ``/etc/cobbler/settings.yaml``:

.. code::

    # cobbler has a feature that allows for integration with config management
    # systems such as Puppet.  The following parameters work in conjunction with

    # --mgmt-classes  and are described in furhter detail at:
    # https://fedorahosted.org/cobbler/wiki/UsingCobblerWithConfigManagementSystem
    mgmt_classes: []
    mgmt_parameters:
       from_cobbler: 1

Alternate External Nodes Script
===============================

Attached at ``puppet_node.py`` is an alternate external node script that fills in the nodes with items from a manifests
repository (at ``/etc/puppet/manifests/``) and networking information from cobbler. It is configured like the above from
the puppet side, and then looks for ``/etc/puppet/external_node.yaml`` for cobbler side configuration.
The configuration is as follows.

.. code::

    base: /etc/puppet/manifests/nodes
    cobbler: <%= cobbler_host %>
    no_yaml: puppet::noyaml
    no_cobbler: network::nocobbler
    bad_yaml: puppet::badyaml
    unmanaged: network::unmanaged

The output for network information will be in the form of a pseudo data structure that allows puppet to split it apart
and create the network interfaces on the node being managed.

cfengine support
################

Documentation to be added

bcfg2 support
#############

Documentation to be added

Chef
####

Documentation to be added.

There is some integration information on bootstrapping chef clients with cobbler in
[this blog article](http://blog.milford.io/2012/03/getting-a-basic-cobbler-server-going-on-centos/)

Conclusion
##########

Hopefully this should get you started in linking up your provisioning configuration with your CMS implementation. The
examples provided are for Puppet, but we can (in the future) presumably extend ``--mgmt-classes`` to work with other
tools... Just let us know what you are interested in, or perhaps take a shot at creating a patch for it.

Attachments
###########

-   [puppet\_node.py](/cobbler/attachment/wiki/UsingCobblerWithConfigManagementSystem/puppet_node.py)
    (2.5 kB) -Alternate External Nodes Script, added by shenson on
    12/09/10 20:33:36.
