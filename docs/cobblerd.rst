***********************************
Cobblerd
***********************************

cobbler - a provisioning and update server

Preamble
########

We will reefer to cobblerd here as cobbler because cobblerd is short for cobbler-deamon which is basically the server.
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

Repositories contain yum mirror information.  Using cobbler to mirror repositories is an optional feature, though
provisioning and package management share a lot in common.

Images are a catch-all concept for things that do not play nicely in the "distribution" category.  Most users will not
need these records initially and these are described later in the document.

The main advantage of cobbler is that it glues together many disjoint technologies and concepts and abstracts the user
from the need to understand them.   It allows the systems administrator to concentrate on what he needs to do, and not
how it is done.

This manpage will focus on the cobbler command line tool for use in configuring cobbler. There is also mention of the
Cobbler WebUI which is usable for day-to-day operation of Cobbler once installed/configured. Docs on the API and XMLRPC
components are available online at https://cobbler.github.io

Most users will be interested in the Web UI and should set it up, though the command line is needed for initial
configuration -- in particular "cobbler check" and "cobbler import", as well as the repo mirroring features. All of
these are described later in the documentation.

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