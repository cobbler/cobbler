***************
Developer Guide
***************


Patch process
#############

You'd like to contribute features or fixes to Cobbler? Great! We'd love to have them.

It is highly recommended that you have a GitHub account if you would like to contribute code. Create an account, log
in, and then go to https://github.com/cobbler/cobbler to "fork" the project.

Create a new branch named after the feature you are working on. Do the work on your local machine, please make sure your
work passes Cobbler's coding standards by using ``make qa``. Only then push to your personal GitHub branch
(e.g. https://github.com/yourname/cobbler).

Then use the "submit pull request" feature of GitHub to request that the official repo pull in your changes. Be sure to
include a full description of what your change does in the comments, including what you have tested (and other things
that you may have not been able to test well and need help with).

If the patch needs more work, we'll let you know in the comments.

Do not mix work on different features in different pull requests/branches if at all possible as this makes it difficult
to take only some of the work at one time, and to quickly slurp in some changes why others get hammered out.

Once we merge in your pull request, you can remove the branch from your repo if you like. The AUTHORS file is created
automatically when we release.

Setup
#####

The preferred development platform is the latest openSUSE Leap or Tumbleweed. You'll also have to disable SELinux to
get Cobbler up and running.

For CentOS you will need the EPEL repository:
``http://download.fedoraproject.org/pub/epel/7/x86_64/repoview/epel-release.html``

Install development dependencies:

.. code-block:: shell

    # yum install git make openssl python-sphinx python36-coverage python36-devel python36-distro python36-future python36-pyflakes python36-pycodestyle python36-setuptools rpm-build

Install runtime dependencies:

.. code-block:: shell

    # yum install httpd mod_wsgi python36-PyYAML python36-netaddr python36-simplejson
    # pip3 install Cheetah3

Initially, to run Cobbler without using packages:

.. code-block:: shell

    # git clone https://github.com/<your username>/cobbler.git
    # cd cobbler
    # make install

For each successive run, do not run make install again. To avoid blowing away your configuration, run:

.. code-block:: shell

    # make webtest

This will install Cobbler and restart apache/cobblerd, but move your configuration files and settings aside and restore
them, rather than blindly overwriting them.

You can now run Cobbler commands and access the web interface.

Tests
#####

We are using pytest and are executing our tests inside Docker because of the high overhead (TFTP, Apache 2, ...), this
also has the advantage that we can easily debug the tests locally.

Build RPMs/DEBs using Docker
############################

1. Make sure docker and docker-compose are installed
2. Use docker-compose to build rpms for the various distros

.. code-block::

   make clean
   docker-compose build --parallel
   docker-compose up

3. RPMs are in rpm-build/

Branches
########

Cobbler has a development branch called "master" (where the action is), and branches for all releases that are in
maintenance mode. All work on new features should be done against the master branch. If you want to address bugs then
please target the latest release branch, the maintainers will then cherry-pick those changes into the master branch.

.. code-block:: shell

    # git branch -r
    # git checkout <branch>
    # git checkout -b <new branch name>


Standards
#########

We're not overly picky, but please follow the python PEP8 standards we want to adhere to (see Makefile).

- Always use under_scores, not camelCase.
- Always four (4) spaces, not tabs.
- Avoid one line if statements.
- Validate your code by using ``make qa``.
- Keep things simple, keep in mind that this is a tool for sysadmins and not python developers.
- Use modules that are easily available (e.g. EPEL) but preferably in the base OS, otherwise they have to be packaged
  with the app, which usually runs afoul of distribution packaging guidelines.
- Cobbler is since the 3.x.x release Python3 only.
- Koan has no new release currently but starting with the next we will also only support Python3.
- Older releases will of course stay with Python2.

You're also welcome to hang out in #cobbler and #cobbler-devel on irc.freenode.net, as there are folks around to answer
questions, etc. But it isn't that active anymore please drop also in our Cobbler Gitter channel there we will probably
answer faster.

Contributing to the website
###########################

The GitHub-based git repository for the https://cobbler.github.io website itself is at
https://github.com/cobbler/cobbler.github.io.

If you want to contribute changes to the website, you will need Jekyll (http://jekyllrb.com).

You will probably want to:

- edit the files as markdown
- run the docker container
- check if your changes didn't break anything

Debugging
#########

If you need to debug a remote process, rpdb provides some very nice capabilities beyond the standard python debugger,
just insert a ``import rpdb; rpdb.set_trace()`` on the desired line run cobbler and then do a ``nc 127.0.0.1 4444``.

