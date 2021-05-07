Terraform Provider for Cobbler
==============================

First have a brief look at `Introduction to Terraform <https://www.terraform.io/intro/index.html>`__.

Next check out the `Cobbler Provider <https://registry.terraform.io/providers/cobbler/cobbler/latest/docs>`__\  official documentation.

- On GitHub: https://github.com/cobbler/terraform-provider-cobbler

- Releases: https://github.com/cobbler/terraform-provider-cobbler/releases


Why Terraform for Cobbler
-------------------------

.. note::

  This document is written with Cobbler 3.2 and higher in mind, so the examples used here
  can not be used for Cobbler 2.x and ``terraform-provider-cobbler`` version
  1.1.0 (and older).

There are multiple ways to add new systems, profiles, distro’s into
Cobbler, eg. through the web-interface or using shell-scripts on the
Cobbler-host itself.

One of the main advantages of using the Terraform Provider for Cobbler is
speed: you do not have to login into the web-interface or SSH to the host
itself and adapt shell-scripts.
When Terraform is installed on a VM or your local computer, it adds new assets
through the Cobbler API.

Configure Cobbler
-----------------

Configure Cobbler to have **caching disabled**.

In file ``/etc/cobbler/settings``, set ``cache_enabled: 0``.

Install Terraform
-----------------

Terraform comes as a single binary, written in Go.
Download an OS-specific package to install on your local system via the
`Terraform downloads <https://www.terraform.io/downloads.html>`__.
Unpack the ZIP-file and move the binary-file into ``/usr/local/bin``.

Make sure you’re using at least **Terraform v0.14 or higher**.
Check with ``terraform version``:

.. code::

  $ terraform version
  Terraform v0.14.5

Install terraform-provider-cobbler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since Terraform version 0.13, you can use the Cobbler provider via the
`Terraform provider registry <https://registry.terraform.io/providers/cobbler/cobbler/latest>`__.

After setting up a Cobbler Terraform repository for the first time, run
``terraform init`` in the **basedir**, so the Cobbler provider
gets installed automatically in ``tf_cobbler/.terraform/providers``.

.. code::

    $ terraform init

    Initializing the backend...

    Initializing provider plugins...
    - Reusing previous version of cobbler/cobbler from the dependency lock file
    - Installing cobbler/cobbler v2.0.2...
    - Installed cobbler/cobbler v2.0.2 (self-signed, key ID B2677721AC1E7A84)

    Partner and community providers are signed by their developers.
    If you'd like to know more about provider signing, you can read about it here:
    https://www.terraform.io/docs/plugins/signing.html

    Terraform has made some changes to the provider dependency selections recorded
    in the .terraform.lock.hcl file. Review those changes and commit them to your
    version control system if they represent changes you intended to make.

    Terraform has been successfully initialized!

    You may now begin working with Terraform. Try running "terraform plan" to see
    any changes that are required for your infrastructure. All Terraform commands
    should now work.

    If you ever set or change modules or backend configuration for Terraform,
    rerun this command to reinitialize your working directory. If you forget, other
    commands will detect it and remind you to do so if necessary.

If you ever run into this error:
``Error: Could not load plugin``, re-run ``terraform init``
in the **basedir** to reinstall / upgrade the Cobbler provider.

When you initialize a Terraform configuration for the first time with Terraform 0.14 or later,
Terraform will generate a new ``.terraform.lock.hcl`` file in the current working directory.
You should include the lock file in your version control repository to ensure that Terraform
uses the same provider versions across your team and in ephemeral remote execution environments.

Repository setup & configurations
---------------------------------

Create a git repository (for example ``tf_cobbler``) and use a phased approach
of software testing and deployment in the `DTAP <https://en.wikipedia.org/wiki/Development,_testing,_acceptance_and_production>`__-style:

-  **development** - holds development systems
-  **test** - holds test systems
-  **staging** - holds staging / acceptance systems
-  **production** - holds production systems
-  **profiles** - holds system profiles
-  **templates** - holds kickstarts and preseed templates
-  **snippets** - holds Cobbler snippets (written in Python Cheetah or Jinja2)
-  **distros** - holds OS distributions

The directory-tree would look something like this:

.. code::

   ├── .gitignore
   ├── .terraform
   │   └── prioviders
   ├── .terraform.lock.hcl
   ├── README.md
   ├── templates
   │   ├── main.tf
   │   ├── debian10.seed
   │   ├── debian10_VMware.seed
   │   ├── ...
   ├── staging
   │   ├── db-staging
   │   ├── lb-staging
   │   ├── web-staging
   │   └── ...
   ├── development
   ├── production
   │   ├── database
   │   ├── load_balancer
   │   ├── webserver
   │   ├── ...
   ├── set_links.sh
   ├── snippets
   │   ├── partitioning-VMware.file
   │   ├── main.tf
   │   ├── ...
   ├── test
   │   └── web-test
   │   ├── ...
   ├── distros
   │   └── distro-debian10-x86_64.tf
   ├── profiles
   │   └── profile-debian10-x86_64.tf
   ├── terraform.tfvars
   ├── variables.tf
   └── versions.tf

Each host-subdirectory consists of a Terraform-file named ``main.tf``,
one **symlinked** directory ``.terraform`` and files **symlinked**
from the root: ``versions.tf``, ``variables.tf``. ``.terraform.lock.hcl``
and ``terraform.tfvars``:

.. code::

   tf_cobbler/production/webserver
   .
   ├── .terraform -> ../../.terraform
   ├── .terraform.lock.hcl -> ../../.terraform.lock.hcl
   ├── main.tf
   ├── terraform.tfstate
   ├── terraform.tfstate.backup
   ├── terraform.tfvars -> ../../terraform.tfvars
   ├── variables.tf -> ../../variables.tf
   └── versions.tf -> ../../versions.tf

The files ``terraform.tfstate`` and ``terraform.tfstate.backup`` are the state files once Terraform
has run succesfully.

File ``versions.tf``
~~~~~~~~~~~~~~~~~~~~~

The block in this file specifies the required provider version and required Terraform version for the configuration.

.. code::

  terraform {
    required_version = ">= 0.14"
    required_providers {
      cobbler = {
        source = "cobbler/cobbler"
        version = "~> 2.0.1"
      }
    }
  }

Credentials
~~~~~~~~~~~

You must add the ``cobbler_username``, ``cobbler_password`` and the
``cobbler_url`` to the Cobbler API into a new file named ``terraform.tfvars``
in the basedir of your repo.

File ``terraform.tfvars``
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

   cobbler_username = "cobbler"
   cobbler_password = "<the Cobbler-password>"
   cobbler_url      = "https://cobbler.example.com/cobbler_api"

Terraform automatically loads ``.tfvars``-files to populate variables defined
in ``variables.tf``.

.. warning::
   When using a git repo, do not (force) push the file ``terraform.tfvars``,
   since it contains login credentials!

File ``variables.tf``
~~~~~~~~~~~~~~~~~~~~~

.. tip::
   We recommend you always add variable descriptions. You never know who’ll be using your code,
   and it’ll make their (and your) life a lot easier if every variable has a clear description.
   Comments are fun too.

   Excerpt from: James Turnbull, "The Terraform Book."

.. code::

   variable "cobbler_username" {
     description = "Cobbler admin user"
     default     = "some_user"
   }

   variable "cobbler_password" {
     description = "Password for the Cobbler admin"
     default     = "some_password"
   }

   variable "cobbler_url" {
     description = "Where to reach the Cobbler API"
     default     = "http://some_server/cobbler_api"
   }

   provider "cobbler" {
     username = var.cobbler_username
     password = var.cobbler_password
     url      = var.cobbler_url
   }

Example configuration - system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the ``main.tf`` for system ``webserver``, written in so called
`HCL <https://github.com/hashicorp/hcl>`__\  (HashiCorp Configuration
Language).
It has been cleaned up with the
`terraform fmt <https://www.terraform.io/docs/commands/fmt.html>`__\  command, to rewrite Terraform configuration files to a canonical format and style:

.. important::
   Make sure there is only **ONE** gateway defined on **ONE** interface!

.. code::

   resource "cobbler_system" "webserver" {
     count            = "1"
     name             = "webserver"
     profile          = "debian10-x86_64"
     hostname         = "webserver.example.com"       # Use FQDN
     autoinstall      = "debian10_VMware.seed"
     # NOTE: Extra spaces at the end are there for a reason!
     # When reading these resource states, the terraform-provider-cobbler
     # parses these fields with an extra space. Adding an extra space in the
     # next 2 lines prevents Terraform from constantly changing the resource.
     kernel_options   = "netcfg/choose_interface=eth0 "
     autoinstall_meta = "fs=ext4 swap=4096 "
     status           = "production"
     netboot_enabled  = "1"

     # Backend interface #############################
     interface {
       name          = "ens18"
       mac_address   = "0C:C4:7A:E3:C3:12"
       ip_address    = "10.11.15.106"
       netmask       = "255.255.255.0"
       dhcp_tag      = "grqproduction"
       dns_name      = "webserver.example.org"
       static_routes = ["10.11.14.0/24:10.11.15.1"]
       static        = true
       management    = true
     }

     # Public interface ##############################
     interface {
       name        = "ens18.15"
       mac_address = "0C:C4:7A:E3:C3:12"
       ip_address  = "127.28.15.106"
       netmask     = "255.255.255.128"
       gateway     = "127.28.15.1"
       dns_name    = "webserver.example.com"
       static      = true
     }
   }

Example configuration - snippet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the ``main.tf`` for a snippet:

.. code::

  resource "cobbler_snippet" "partitioning-VMware" {
    name = "partitioning-VMware"
    body = file("partitioning-VMware.file")
  }

In the same folder a file named ``partitioning-VMware.file`` holds the actual
snippet.

Example configuration - repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

  resource "cobbler_repo" "debian10-x86_64" {
    name           = "debian10-x86_64"
    breed          = "apt"
    arch           = "x86_64"
    apt_components = ["main universe"]
    apt_dists      = ["buster buster-updates buster-security"]
    mirror         = "http://ftp.nl.debian.org/debian/"
  }

Example configuration - distro
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

  resource "cobbler_distro" "debian10-x86_64" {
    name            = "debian10-x86_64"
    breed           = "debian"
    os_version      = "buster"
    arch            = "x86_64"
    kernel          = "/var/www/cobbler/distro_mirror/debian10-x86_64/install.amd/linux"
    initrd          = "/var/www/cobbler/distro_mirror/debian10-x86_64/install.amd/initrd.gz"
  }

Example configuration - profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

  resource "cobbler_profile" "debian10-x86_64" {
    name                = "debian10-x86_64"
    distro              = "debian10-x86_64"
    autoinstall         = "debian10.seed"
    autoinstall_meta    = "release=10 swap=2048"
    kernel_options      = "fb=false ipv6.disable=1"
    name_servers        = ["1.1.1.1", "8.8.8.8"]   # Should be a list
    name_servers_search = ["example.com"]
    repos               = ["debian10-x86_64"]
  }

Example configuration - combined
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is also possible to combine multiple resources into one file.
For example, this will combine an Ubuntu Bionic distro, a profile and a system:

.. code::

  resource "cobbler_distro" "foo" {
      name = "foo"
      breed = "ubuntu"
      os_version = "bionic"
      arch = "x86_64"
      boot_loaders = ["grub"]
      kernel = "/var/www/cobbler/distro_mirror/Ubuntu-18.04/install/netboot/ubuntu-installer/amd64/linux"
      initrd = "/var/www/cobbler/distro_mirror/Ubuntu-18.04/install/netboot/ubuntu-installer/amd64/initrd.gz"
    }

    resource "cobbler_profile" "foo" {
      name = "foo"
      distro = "foo"
    }

    resource "cobbler_system" "foo" {
      name = "foo"
      profile = "foo"
      name_servers = ["8.8.8.8", "8.8.4.4"]
      comment = "I'm a system"
      interface {
        name = "ens18"
        mac_address = "aa:bb:cc:dd:ee:ff"
        static = true
        ip_address = "1.2.3.4"
        netmask = "255.255.255.0"
      }
      interface {
        name = "ens19"
        mac_address = "aa:bb:cc:dd:ee:fa"
        static = true
        ip_address = "1.2.3.5"
        netmask = "255.255.255.0"
      }
    }

File ``set_links.sh``
~~~~~~~~~~~~~~~~~~~~~

The file ``set_links.sh`` is used to symlink to the default variables.
We need these in every subdirectory.

.. code:: shell

  #!/bin/sh

  ln -s ../../variables.tf
  ln -s ../../versions.tf
  ln -s ../../.terraform
  ln -s ../../terraform.tfvars
  ln -s ../../.terraform.lock.hcl

Adding a new system
~~~~~~~~~~~~~~~~~~~

.. code::

   git pull --rebase <-- Refresh the repository

   mkdir production/hostname
   cd production/hostname

   vi main.tf          <-- Add a-based configuration as described above.

   ../../set_links.sh  # This will create symlinks to .terraform, variables.tf and terraform.tfvars

   terraform fmt       <-- Rewrites the file "main.tf" to canonical format.

   terraform validate  <-- Validates the .tf file (optional).

   terraform plan      <-- Create the execution plan.

   terraform apply     <-- Apply changes, eg. add this system to the (remote) Cobbler.


When ``terraform apply`` gives errors it is safe to run
``rm terraform.tfstate*`` in the “hostname” directory and run ``terraform apply``
again.
