# This is extremely crude implementation of an OrderedDict.
# If you know of a better implementation, please send it to
# the author Steve Howell.  You can find my email via
# the YAML mailing list or wiki.

class OrderedDict(dict):
    def __init__(self):
        self._keys = []

    def __setitem__(self, key, val):
        self._keys.append(key)
        dict.__setitem__(self, key, val)

    def keys(self):
        return self._keys

    def items(self):
        return [(key, self[key]) for key in self._keys]

if __name__ == '__main__':
    data = OrderedDict()
    data['z'] = 26
    data['m'] = 13
    data['a'] = 1
    for key in data.keys():
        print "The value for %s is %s" % (key, data[key])
    print data




