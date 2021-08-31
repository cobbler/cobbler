***********************************
Cobblerd
***********************************

Cobbler - a provisioning and update server

Preamble
########

We will refer to `cobblerd` here as "cobbler" because `cobblerd` is short for cobbler-daemon which is basically the server.
The CLI will be referred to as Cobbler-CLI and Koan as Koan.

Description
###########

Cobbler manages provisioning using a tiered concept of Distributions, Profiles, Systems, and (optionally) Images and
Repositories.

Distributions contain information about what kernel and initrd are used, plus metadata (required kernel parameters,
etc).

Profiles associate a Distribution with an automated installation template file and optionally customize the metadata
further.

Systems associate a MAC, IP, and other networking details with a profile and optionally customize the metadata further.

Repositories contain yum mirror information. Using cobbler to mirror repositories is an optional feature, though
provisioning and package management share a lot in common.

Images are a catch-all concept for things that do not play nicely in the "distribution" category. Most users will not
need these records initially and these are described later in the document.

The main advantage of cobbler is that it glues together many disjoint technologies and concepts and abstracts the user
from the need to understand them. It allows the systems administrator to concentrate on what he needs to do, and not
how it is done.

This manpage will focus on the cobbler command line tool for use in configuring cobbler. There is also mention of the
Cobbler WebUI which is usable for day-to-day operation of Cobbler once installed/configured. Docs on the API and XML-RPC
components are available online at `https://cobbler.github.io <https://cobbler.github.io>`_ or
`https://cobbler.readthedocs.io <https://cobbler.readthedocs.io>`_.

Most users will be interested in the Web UI and should set it up, though the command line is needed for initial
configuration -- in particular ``cobbler check`` and ``cobbler import``, as well as the repo mirroring features. All of
these are described later in the documentation.

Setup
#####

After installing, run ``cobbler check`` to verify that cobbler's ecosystem is configured correctly. Cobbler check will
direct you on how to modify it's config files using a text editor.

Any problems detected should be corrected, with the potential exception of DHCP related warnings where you will need to
use your judgement as to whether they apply to your environment. Run ``cobbler sync`` after making any changes to the
configuration files to ensure those changes are applied to the environment.

It is especially important that the server name field be accurate in ``/etc/cobbler/settings.yaml``, without this field
being correct, automatic installation trees will not be found, and automated installations will fail.

For PXE, if DHCP is to be run from the cobbler server, the DHCP configuration file should be changed as suggested by
``cobbler check``. If DHCP is not run locally, the ``next-server`` field on the DHCP server should at minimum point to
the cobbler server's IP and the filename should be set to ``pxelinux.0``. Alternatively, cobbler can also generate your
DHCP configuration file if you want to run DHCP locally -- this is covered in a later section. If you don't already have
a DHCP setup managed by some other tool, allowing cobbler to manage your DHCP environment will prove to be useful as it
can manage DHCP reservations and other data. If you already have a DHCP setup, moving an existing setup to be managed
from within cobbler is relatively painless -- though usage of the DHCP management feature is entirely optional. If you
are not interested in network booting via PXE and just want to use Koan to install virtual systems or replace existing
ones, DHCP configuration can be totally ignored. Koan also has a live CD (see Koan's manpage) capability that can be
used to simulate PXE environments.

Autoinstallation (AutoYaST/Kickstart)
#####################################

For help in building kickstarts, try using the ``system-config-kickstart`` tool, or install a new system and look at the
``/root/anaconda-ks.cfg`` file left over from the installer. General kickstart questions can also be asked at
kickstart-list@redhat.com. Cobbler ships some autoinstall templates in ``/etc/cobbler`` that may also be helpful.

For AutoYaST guides and help please refer to `the opensuse project <https://doc.opensuse.org/projects/autoyast/>`_.

Also see the website or documentation for additional documentation, user contributed tips, and so on.

Options
#######

-B --daemonize
    If you pass no options this is the default one. The Cobbler-Server runs in the background.

-F --no-daemonize
    The Cobbler-Server runs in the foreground.

-f --log-file
    Choose a destination for the logfile (currently has no effect).

-l --log-level
    Choose a loglevel for the application (currently has no effect).

--c --config
    The location of the Cobbler configuration file.

--disable-automigration
    If given, do no execute automigration from older settings filles to the most recent.
