.. _configuration-management:

*************************************
Configuration Management Integrations
*************************************

Cobbler contains features for integrating an installation environment with a configuration management system, which
handles the configuration of the system after it is installed by allowing changes to configuration files and settings.

The initial provisioning of client systems with cobbler is just one component of their management. We also need to
consider how to continue to manage them using a configuration management system (CMS). Cobbler can help you provision
and introduce a CMS onto your client systems.

There are two broad approaches to this:

* Cobbler's own lightweight, templating-based CMS. For that, see `Built-In Configuration Management`_.
* Deploying a full external CMS such as

  * `cfengine3 <https://cfengine.com/>`_,
  * `puppet <https://puppet.com/>`_,
  * `bcfg2 <http://bcfg2.org>`_,
  * `Chef <https://www.chef.io/products/chef-infrastructure-management>`_,
  * etc.

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

.. code-block:: text

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

* integration with an established external CMS such as cfengine3, bcfg2, Chef, or puppet.
* its own, much simpler, lighter-weight, internal CMS, discussed here.

Setting up
==========

Cobbler's internal CMS is focused around packages and templated configuration files, and installing these on client
systems.

This all works using the same `Cheetah-powered <https://cheetahtemplate.org>`_ or Jinja2 templating engine used in
autoinstall templating (see :ref:`templating`), so once you learn about the power of treating your distribution answer
files as templates, you can use the same templating to drive your CMS configuration files.

For example:

.. code-block:: shell

    cobbler profile edit --name=webserver --template-files=/srv/cobbler/x.template=/etc/foo.conf

A client system installed via the above profile will gain a file ``/etc/foo.conf`` which is the result of rendering the
template given by ``/srv/cobbler/x.template``. Multiple files may be specified as a comma-delimited list of
``source=destination`` pairs:

.. code-block:: shell

    --template-files=/srv/cobbler/x.template=/etc/xfile.conf,/srv/cobbler/y.template=/etc/yfile.conf

.. warning:: Do **not** separate multiple pairs with spaces (e.g. ``"src1=dst1 src2=dst2"``) -- the CLI parses this flag
             as a comma-delimited map, so a space-separated value is silently misparsed into a single, wrong mapping
             instead of raising an error.

Template files
==============

Because the template files will be parsed by the Cheetah or Jinja2 parser, they must conform to the guidelines described
in :ref:`templating`. This is particularly important when the file is generated outside of that templating environment.
Look for, and act on, template parse errors in the Cobbler logs.

Template files follow the general syntax of whichever template engine renders them, so can include template variables.
Any variables you define anywhere in the cobbler object hierarchy (distros, profiles, and systems) are available to your
templates. To see all the variables available, use the command:

.. code-block:: shell

    cobbler profile dumpvars --name=webserver

Cobbler snippets and other advanced features can also be employed.

Ongoing maintenance
===================

Koan can pull down files to keep a system updated with the latest templates and variables:

.. code-block:: shell

    koan --server=cobbler.example.org --profile=foo --update-files

You could also use ``--server=bar`` to retrieve a more specific set of templating. ``--server`` (or the
``COBBLER_SERVER`` environment variable) is always required, but if you omit both ``--profile`` and ``--system``, koan
will autodetect which system record to use by matching the local machine's MAC address and IP against the systems known
to that server.

Further uses
============

This Cobbler templating system can serve up templates via the magic URLs (see `Magic URLs`_ below). To do this ensure
that the destination path given to any ``--template-files`` element is relative, not absolute; then Cobbler and Koan
won't download those files.

For example, in:

.. code-block:: shell

    cobbler profile edit --name=foo --template-files=/srv/templates/a.src=/etc/foo/a.conf,/srv/templates/b.src=1

Cobbler and koan would automatically download the rendered ``a.src`` to replace the file ``/etc/foo/a.conf``, but the
``b.src`` file would not be downloaded to anything because the destination pathname ``1`` is not absolute.

This technique enables using the Cobbler templating system to build things that other systems can fetch and use, for
instance, BIOS config files for usage from a live environment.

Magic URLs
==========

All template files are generated dynamically at run-time, served by the ``template`` operation of the ``/cblr/svc/``
HTTP API (see :ref:`http-api`; this used to run under Apache's ``mod_python``, it is WSGI/gunicorn-based today). If a
change is made to a template, a ``--autoinstall-meta`` variable or some other variable in Cobbler, the result of
template rendering will be different on subsequent runs. This is covered in more depth in the `Developer documentation
<https://github.com/cobbler/cobbler/wiki>`_.

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
- https://github.com/osism/ansible-cobbler (archived by its author -- kept for reference only)
- https://github.com/hakoerber/ansible-roles

Saltstack
#########

The Cobbler community maintains an official SaltStack formula for installing and configuring Cobbler itself:

- https://github.com/cobbler/cobbler-formula

There is also community work targeting the opposite direction -- using Salt to manage systems that Cobbler provisions:

- https://github.com/hakoerber/salt-states/tree/master/cobbler

Vagrant
#######

Although we currently can not provide something official we can indeed link some community work here:

- https://github.com/davegermiquet/vmwarevagrantcobblercentos
- https://github.com/dratushnyy/tools
- https://github.com/mkusanagi/cobbler-kickstart-playground

Puppet
######

Puppet is driven the same way as any other CMS: install and bootstrap it through `General scheme`_, then use `Built-In
Configuration Management`_ (or Puppet's own catalog/module system) to manage its ongoing configuration. There is no
Puppet-specific integration beyond this in current Cobbler -- the ``--mgmt-classes`` item attribute and the Puppet
"External Nodes" HTTP endpoint that older Cobbler versions provided were both removed; manifests, node classification
and module assignment are expected to live entirely on the Puppet side (e.g. via Hiera/ENC backed by your own inventory,
such as the Ansible ``cobbler_inventory`` plugin above) rather than being pushed from Cobbler.

cfengine support
################

Documentation to be added

bcfg2 support
#############

Documentation to be added

Chef support
############

This walkthrough shows a hands-free, air-gapped PXE bootstrap of Chef clients, adapted for 4.0.0 from the project's own
`Cobbler and Chef <https://cobbler.github.io/blog/2026/01/28/cobbler-and-chef.html>`_ blog post. While Chef itself
doesn't change anything on the managed system in this walkthrough, it gets the node registered and ready for Chef to
take over, which is as far as Cobbler's job goes.

Installing Cobbler
==================

No stable package repository exists yet for the 4.0.0 series, so follow :doc:`/installation-guide` (the Docker-based
RPM/DEB build scripts are the easiest path) to install Cobbler. You will also need ``dhcp-server`` and ``bind`` from
your distribution.

Firewall configuration
======================

To allow Cobbler (and the other services running on the host) to offer their services, execute the following commands:

.. code-block:: console

    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=http
    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=https
    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=tftp
    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=dhcp
    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=dhcpv6
    root@cobbler:~$ firewall-cmd --permanent --zone=public --add-service=dns
    root@cobbler:~$ firewall-cmd --reload

Cobbler configuration
=====================

Cobbler's built-in authentication defaults to username and password both set to ``cobbler``; harden this before going to
production. The default password Cobbler installs onto systems is the ``default_password_crypted`` key in
``/etc/cobbler/settings.yaml``, an OpenSSL hash generated with ``openssl passwd -1`` -- change this too.

A handful of settings need adjusting for Cobbler to generate a working PXE tree with its related services (see
:ref:`settings-ref` for all of these):

- ``server``: the IP/FQDN of Cobbler inside your installation network(s).
- ``anamon_enabled``: allows Red Hat-based installers to send installation logs to Cobbler for inspection.
- ``next_server_v4``/``next_server_v6``: the IP DHCP announces as the TFTP server; set to the Cobbler server's own IP
  for this guide.
- ``manage_dhcp_v4``: ``true``, so clients in the network get addresses dynamically assigned.
- ``manage_dns``: ``true``, so hostnames are turned into A records.
- ``manage_forward_zones``/``manage_reverse_zones``: the forward zone and reverse network range to manage, e.g.
  ``["cobbler.local"]`` and ``["192.168.100.0/24"]``.

Enabling services
=================

To allow ``dhcpd`` to listen on the right interface, set ``DHCPD_INTERFACE`` in ``/etc/sysconfig/dhcpd``:

.. code-block:: text

    DHCPD_INTERFACE="eth1"

Enable Cobbler with ``systemctl enable --now cobblerd``.

DHCP and DNS configuration are no longer plain files under ``/etc/cobbler/`` -- they are rendered from the ``Template``
item tagged ``active`` for ``dhcpv4``/``named_primary`` respectively (see :ref:`templating`). Export the built-in
templates, adjust subnet/routers/DNS servers/``dynamic-bootp`` range (for DHCP) and the logging path (for named), place
them under ``autoinstall_templates_dir`` (``/var/lib/cobbler/templates`` by default), and register your copies:

.. code-block:: console

    root@cobbler:~$ cobbler template content --name=built-in-dhcp > my-dhcp.template
    root@cobbler:~$ # edit my-dhcp.template: subnet, routers, domain-name-servers, dynamic-bootp range
    root@cobbler:~$ cp my-dhcp.template /var/lib/cobbler/templates/
    root@cobbler:~$ cobbler template add --name=my-dhcp --template-type=cheetah --uri-path=my-dhcp.template --tags=dhcpv4,active
    root@cobbler:~$ cobbler template content --name=built-in-named > my-named.template
    root@cobbler:~$ # edit my-named.template: set the logging path to /var/log/named/default.log
    root@cobbler:~$ cp my-named.template /var/lib/cobbler/templates/
    root@cobbler:~$ cobbler template add --name=my-named --template-type=cheetah --uri-path=my-named.template --tags=named_primary,active

To have everything working after a reboot, enable the HTTP, TFTP, DNS and DHCP services to autostart:

.. code-block:: console

    root@cobbler:~$ systemctl enable --now tftp.service
    root@cobbler:~$ systemctl enable --now apache2.service
    root@cobbler:~$ systemctl enable --now dhcpd.service
    root@cobbler:~$ systemctl enable --now named.service

Bootloader setup
================

Working bootloaders are a hard requirement for systems to boot. Install the needed packages, then let Cobbler fetch and
lay out the bootloaders itself:

.. code-block:: console

    root@cobbler:~$ zypper in grub2-i386-efi grub2-x86_64-efi ipxe syslinux
    root@cobbler:~$ cobbler mkloaders
    root@cobbler:~$ cobbler sync

Importing operating system media
================================

Download the installation media (Fedora 44 in this example) and import it:

.. code-block:: console

    root@cobbler:~$ mkdir /var/lib/cobbler/os-images /var/lib/cobbler/os-images-mounted
    root@cobbler:~$ cd /var/lib/cobbler/os-images/
    root@cobbler:~$ wget https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/iso/Fedora-Server-dvd-x86_64-44-1.2.iso
    root@cobbler:~$ mkdir /var/lib/cobbler/os-images-mounted/fedora-44
    root@cobbler:~$ echo "/var/lib/cobbler/os-images/Fedora-Server-dvd-x86_64-44-1.2.iso /var/lib/cobbler/os-images-mounted/fedora-44 iso9660 loop 0 0" >> /etc/fstab
    root@cobbler:~$ mount -a
    root@cobbler:~$ cobbler import --name="fedora-44" --path="/var/lib/cobbler/os-images-mounted/fedora-44"
    root@cobbler:~$ cobbler distro edit --name="fedora-44-x86_64" --kernel-options-json='{}'

``cobbler import`` guesses a default ``kernel_options`` value from the distro signatures (e.g. ``repo=$tree``); the edit
above clears it. Note that for a map-typed flag like ``--kernel-options``, clearing it takes
``--kernel-options-json='{}'`` -- an empty string (the old ``--kernel-options=""``) is now a parse error.

Add the repositories so installs don't need to reach the internet. ``--keep-updated`` is a plain boolean flag now, so
simply omit it to leave a repo unmanaged by ``cobbler reposync``:

.. code-block:: console

    root@cobbler:~$ cobbler repo add --arch=x86_64 --breed=yum --mirror=https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/os/ --name=fedora44
    root@cobbler:~$ cobbler repo add --arch=x86_64 --breed=yum --mirror=https://dl.fedoraproject.org/pub/fedora/linux/updates/44/Everything/x86_64/ --name=fedora44-updates

``cobbler reposync`` is not needed here, since these repos are referenced from the kickstart file but not themselves
mirrored by Cobbler.

Setting up the RPM mirror
=========================

A small Python script to download the Chef Open-Source clients from their API is available as a `GitHub Gist
<https://gist.github.com/SchoolGuy/2fcd4452d347303ae892fadbdf1f8d3b>`_. Download it, then fetch and index the RPMs
(replace the placeholders, such as ``LICENSE_ID``, with your actual values):

.. code-block:: console

    root@cobbler:~$ curl -o /usr/local/bin/chef-download https://gist.githubusercontent.com/SchoolGuy/2fcd4452d347303ae892fadbdf1f8d3b/raw/chef-download.py
    root@cobbler:~$ chmod +x /usr/local/bin/chef-download
    root@cobbler:~$ zypper in createrepo
    root@cobbler:~$ mkdir -p /srv/www/rpms/rhel /srv/www/rpms/suse
    root@cobbler:~$ chef-download --endpoint=download-nice --product=chef --platform=el --platform-version=8 --architecture=x86_64 --version=latest --license-id=free-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxx
    root@cobbler:~$ createrepo /srv/www/rpms/suse/
    root@cobbler:~$ createrepo /srv/www/rpms/rhel/

Serve them from a dedicated Apache vhost:

.. code-block:: apache

    <VirtualHost *:80>
        DocumentRoot "/srv/www/rpms"
        ServerName rpm.cobbler.local

        <Directory "/srv/www/rpms">
            Options Indexes MultiViews
            AllowOverride None
            Require all granted
        </Directory>
    </VirtualHost>

Also add a ``ServerName cobbler.cobbler.local`` directive to the Cobbler vhost.

Chef server setup
=================

Reserve a DNS/DHCP entry for the Chef server VM on the Cobbler server. ``distro``/``profile``/``system`` references must
be UIDs, not names, so look the UID up first; network configuration is set separately via ``cobbler interface add``,
since interfaces are a first-class item collection in 4.0.0, no longer flat ``--mac``/``--ip-address``/``--dns-name``
flags on ``system add``:

.. code-block:: console

    root@cobbler:~$ cobbler distro add --name=fake --kernel=/var/lib/cobbler/kernel --initrd=/var/lib/cobbler/initrd
    root@cobbler:~$ FAKE_DISTRO_UID=$(cobbler distro report --name=fake | awk -F': *' '/^uid /{print $2}')
    root@cobbler:~$ cobbler profile add --name=fake --distro="$FAKE_DISTRO_UID"
    root@cobbler:~$ FAKE_PROFILE_UID=$(cobbler profile report --name=fake | awk -F': *' '/^uid /{print $2}')
    root@cobbler:~$ cobbler system add --name="chef.cobbler.local" --profile="$FAKE_PROFILE_UID"
    root@cobbler:~$ cobbler interface add --system-name="chef.cobbler.local" --name=default --static --mac-address="52:54:00:f2:61:40" --ipv4-address="192.168.100.10" --dns-name="chef.cobbler.local"
    root@cobbler:~$ cobbler sync

Now edit the Cobbler named template (the ``my-named`` template registered above) to allow queries from your libvirtd
network and listen on any interface -- this is only a test setup; in production, limit the networks that can query your
named server.

On the Chef VM (Rocky Linux 9), run:

.. code-block:: console

    root@chef:~$ dnf install libnsl nginx
    root@chef:~$ wget -O chef-server.rpm "https://chefdownload-community.chef.io/stable/chef-server/download?license_id=free-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxx&m=x86_64&p=sles&pv=15&v=latest"
    root@chef:~$ dnf install chef-server.rpm
    root@chef:~$ chef-server-ctl reconfigure
    root@chef:~$ chef-server-ctl user-create USER_NAME FIRST_NAME LAST_NAME EMAIL 'PASSWORD' --filename FILE_NAME
    root@chef:~$ chef-server-ctl org-create short_name 'full_organization_name' --association_user user_name --filename ORGANIZATION-validator.pem
    root@chef:~$ firewall-cmd --permanent --zone=public --add-service=http
    root@chef:~$ firewall-cmd --permanent --zone=public --add-service=https
    root@chef:~$ firewall-cmd --reload

Installing Chef Workstation
===========================

On openSUSE Leap, installing Chef Workstation and bootstrapping a repo looks like:

.. code-block:: console

    root@chef-workstation:~$ wget -O chef-workstation.rpm "https://packages.chef.io/files/stable/chef-workstation/0.4.2/el/6/chef-workstation-0.4.2-1.el6.x86_64.rpm?licenseId=free-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxx"
    root@chef-workstation:~$ zypper in chef-workstation.rpm
    root@chef-workstation:~$ cd <projects directory>
    root@chef-workstation:~$ knife configure init-config
    root@chef-workstation:~$ cd ~/.chef
    root@chef-workstation:~$ scp root@chef.cobbler.local:/root/admin.pem .
    root@chef-workstation:~$ knife ssl fetch
    root@chef-workstation:~$ knife client list
    root@chef-workstation:~$ chef generate repo chef-repo
    root@chef-workstation:~$ cd chef-repo

Integrating Chef with Cobbler
=============================

Back on the Cobbler server, the default sample kickstart template (``built-in-sample.ks``, what ``fedora-44-x86_64``
uses by default) isn't a plain file under ``/var/lib/cobbler/templates`` anymore either -- export, edit and re-register
it the same way as the DHCP/named templates above, then point the profile's (not distro's) ``--autoinstall`` at its
name:

.. code-block:: console

    root@cobbler:~$ cobbler template content --name=built-in-sample.ks > my-sample.ks
    root@cobbler:~$ # make the edits below, then:
    root@cobbler:~$ cp my-sample.ks /var/lib/cobbler/templates/
    root@cobbler:~$ cobbler template add --name=my-sample.ks --template-type=cheetah --uri-path=my-sample.ks
    root@cobbler:~$ cobbler profile edit --name="fedora-44-x86_64" --autoinstall=my-sample.ks

Make the following changes:

- Comment out the shipped ``auth --useshadow --enablemd5`` line.
- Replace the deprecated ``install`` directive with ``url --url=$tree``.
- Add the Fedora updates repo and the custom Chef repo before ``%pre``:

  .. code-block:: text

      repo --name=updates
      repo --name=chef --baseurl="http://rpm.cobbler.local/rhel" --install

- Add ``libxcrypt-compat`` and ``chef`` to ``%packages``.
- Disable ``systemd-resolved`` in both ``%pre`` and ``%post`` so the node can resolve ``cobbler.local``:

  .. code-block:: text

      %pre
      systemctl stop systemd-resolved 2>/dev/null || true
      ...

      %post
      systemctl disable systemd-resolved
      systemctl mask systemd-resolved
      rm -f /etc/resolv.conf
      cat <<EOF > /etc/resolv.conf
      search cobbler.local
      nameserver 192.168.100.2
      EOF
      ...

- Finally, bootstrap ``chef-client`` as the last step of ``%post``:

  .. code-block:: bash

      mkdir -p /etc/chef
      cat <<EOF > /etc/chef/client.rb
      chef_server_url "https://chef.cobbler.local/organizations/cobbler"
      validation_client_name "cobbler-validator"
      validation_key "/etc/chef/cobbler-validator.pem"
      log_level :info
      node_name "$name"
      EOF
      curl -o /etc/chef/cobbler-validator.pem http://cobbler.cobbler.local/cobbler/pub/cobbler-validator.pem
      knife ssl fetch -c /etc/chef/client.rb
      chef-client -c /etc/chef/client.rb --override-runlist=""

Copy the Chef validator certificate from the Chef server to where the snippet above expects it:

.. code-block:: console

    root@cobbler:~$ scp root@192.168.100.10:/root/cobbler-validator.pem /srv/www/cobbler/pub/

Testing the setup
=================

Add a system, matching it to the profile and interface by UID as shown in `Chef server setup`_, then PXE-boot it and
watch the anamon logs on the Cobbler server. Once it completes, verify it registered with Chef:

.. code-block:: console

    root@chef-workstation:~$ knife node list
    server01.cobbler.local

Conclusion
##########

Hopefully this should get you started in linking up your provisioning configuration with your CMS implementation. The
detailed walkthroughs above cover Puppet and Chef, but the same principles -- package installation via a repo and
kickstart snippet, then ongoing configuration via either Cobbler's own templating or the CMS itself -- apply to any CMS.
Just let us know what you are interested in, or perhaps take a shot at creating a patch for it.
