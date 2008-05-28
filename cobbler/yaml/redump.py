"""
pyyaml legacy
Copyright (c) 2001 Steve Howell and Friends; All Rights Reserved
(see open source license information in docs/ directory)
"""

from ordered_dict import OrderedDict
from load import Parser
from dump import Dumper
from stream import StringStream

def loadOrdered(stream):
    parser = Parser(StringStream(stream))
    parser.dictionary = OrderedDict
    return iter(parser)

def redump(stream):
    docs = list(loadOrdered(stream))
    dumper = Dumper()
    dumper.alphaSort = 0
    return dumper.dump(*docs)

