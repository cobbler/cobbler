"""
pyyaml legacy
Copyright (c) 2001 Steve Howell and Friends; All Rights Reserved
(see open source license information in docs/ directory)
"""

__version__ = "0.32"
from load import loadFile, load, Parser, l
from dump import dump, dumpToFile, Dumper, d
from stream import YamlLoaderException, StringStream, FileStream
from timestamp import timestamp
import sys
if sys.hexversion >= 0x02020000:
    from redump import loadOrdered

try:
    from ypath import ypath
except NameError:
    def ypath(expr,target='',cntx=''):
        raise NotImplementedError("ypath requires Python 2.2")

if sys.hexversion < 0x02010000:
    raise 'YAML is not tested for pre-2.1 versions of Python'
