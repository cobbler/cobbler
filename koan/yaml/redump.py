from yaml.ordered_dict import OrderedDict
from yaml import Parser, Dumper, StringStream

def loadOrdered(stream):
    parser = Parser(StringStream(stream))
    parser.dictionary = OrderedDict
    return iter(parser)

def redump(stream):
    docs = list(loadOrdered(stream))
    dumper = Dumper()
    dumper.alphaSort = 0
    return dumper.dump(*docs)

