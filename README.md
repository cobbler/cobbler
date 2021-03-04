# Cobbler

[![Publish Python distributions to TestPyPI](https://github.com/cobbler/cobbler/actions/workflows/release_master.yml/badge.svg?branch=master)](https://github.com/cobbler/cobbler/actions/workflows/release_master.yml)
[![PyPI version](https://badge.fury.io/py/cobbler.svg)](https://badge.fury.io/py/cobbler)
![PyPI - Downloads](https://img.shields.io/pypi/dm/cobbler)
[![Documentation Status](https://readthedocs.org/projects/cobbler/badge/?version=latest)](https://cobbler.readthedocs.io/en/latest/)
[![Gitter chat](https://badges.gitter.im/cobbler/gitter.png)](https://gitter.im/cobbler/community)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/c8c0c787c4854aba925d361eacc15811)](https://www.codacy.com/gh/cobbler/cobbler/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=cobbler/cobbler&amp;utm_campaign=Badge_Grade)
[![codecov](https://codecov.io/gh/cobbler/cobbler/branch/master/graph/badge.svg)](https://codecov.io/gh/cobbler/cobbler)


Cobbler is a Linux installation server that allows for rapid setup of network installation environments. It glues
together and automates many associated Linux tasks so you do not have to hop between lots of various commands and
applications when rolling out new systems, and, in some cases, changing existing ones. It can help with installation,
DNS, DHCP, package updates, power management, configuration management orchestration, and much more.

[![asciicast](https://asciinema.org/a/351156.svg)](https://asciinema.org/a/351156)

Read more at [https://cobbler.github.io](https://cobbler.github.io)

To view the man-pages, install the RPM and run `man cobbler` or run `perldoc cobbler.pod` from a source checkout.

To build the RPM, run `make rpms`. Developers, try `make webtest` to do a local `make install` that preserves your
configuration.

If you want to contribute you may find more information under [CONTRIBUTING.md](CONTRIBUTING.md).

The documentation can be found at [Readthedocs](https://cobbler.readthedocs.io)
