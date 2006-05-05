
"""
Base class for any serializable lists of things...
"""
class Collection:
    _item_factory = None

    def __init__(self):
        """
	Constructor.  Requires an API reference.  seed_data
	is a hash of data to feed into the collection, that would
	come from the config file in /var.
	"""
        self.listing = {}
        # no longer done at construct time, use from_datastruct
        #if seed_data is not None:
        #   for x in seed_data:
        #       self.add(self._item_factory(self.api, x))

    def find(self,name):
        """
        Return anything named 'name' in the collection, else return None if
        no objects can be found.
        """
        if name in self.listing.keys():
            return self.listing[name]
        return None


    def to_datastruct(self):
        """
        Return datastructure representation of this collection suitable
        for feeding to a serializer (such as YAML)
        """
        return [x.to_datastruct() for x in self.listing.values()]


    def from_datastruct(self,datastruct):
        for x in datastruct:
            self._item_factory(x)

    def add(self,ref):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).
        """
        if ref is None or not ref.is_valid():
            if runtime.last_error() is None or runtime.last_error() == "":
                runtime.set_error("bad_param")
            return False
        self.listing[ref.name] = ref
        return True


    def printable(self):
        """
        Creates a printable representation of the collection suitable
        for reading by humans or parsing from scripts.  Actually scripts
        would be better off reading the YAML in the config files directly.
        """
        values = map(lambda(a): a.printable(), sorted(self.listing.values()))
        if len(values) > 0:
           return "\n\n".join(values)
        else:
           return m("empty_list")

    #def contents(self):
    #    """
    #	Access the raw contents of the collection.  Classes shouldn't
    #	be doing this (preferably) and should use the __iter__ interface.
    #    Deprecrated.
    #	 """
    #    return self.listing.values()

    def __iter__(self):
        """
	Iterator for the collection.  Allows list comprehensions, etc
	"""
        for a in self.listing.values():
	    yield a

    def __len__(self):
        """
	Returns size of the collection
	"""
        return len(self.listing.values())

