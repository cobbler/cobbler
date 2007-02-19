"""optik

A powerful, extensible, and easy-to-use command-line parser for Python.

By Greg Ward <gward@python.net>

See http://optik.sourceforge.net/

Cheetah modifications:  added "Cheetah.Utils.optik." prefix to
  all intra-Optik imports.
"""

# Copyright (c) 2001 Gregory P. Ward.  All rights reserved.
# See the README.txt distributed with Optik for licensing terms.

__revision__ = "$Id: __init__.py,v 1.2 2002/09/12 06:56:51 hierro Exp $"

__version__ = "1.3"


# Re-import these for convenience
from Cheetah.Utils.optik.option import Option
from Cheetah.Utils.optik.option_parser import \
     OptionParser, SUPPRESS_HELP, SUPPRESS_USAGE, STD_HELP_OPTION
from Cheetah.Utils.optik.errors import OptionValueError


# Some day, there might be many Option classes.  As of Optik 1.3, the
# preferred way to instantiate Options is indirectly, via make_option(),
# which will become a factory function when there are many Option
# classes.
make_option = Option
