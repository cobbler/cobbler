"""
Base class for any serializable list of things...

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions

import serializable
import utils
import msg

class Collection(serializable.Serializable):

    def __init__(self,config):
        """
	Constructor.
	"""
        self.config = config
        self.clear()

    def factory_produce(self,config,seed_data):
        """
        Must override in subclass.  Factory_produce returns an Item object
        from datastructure seed_data
        """
        raise exceptions.NotImplementedError

    def filename(self):
        """
        Must override in subclass.  See Serializable
        """
        raise exceptions.NotImplementedError

    def clear(self):
        """
        Forget about objects in the collection.
        """
        if utils.app_debug:
            print "Collection::clear"
        self.listing = {}

    def find(self,name):
        """
        Return anything named 'name' in the collection, else return None if
        no objects can be found.
        """
        if utils.app_debug:
            print "Collection::find(%s)" % name
        if name in self.listing.keys():
            return self.listing[name]
        return None


    def to_datastruct(self):
        """
        Serialize the collection
        """
        if utils.app_debug:
            print "Collection::to_datastruct"
        datastruct = [x.to_datastruct() for x in self.listing.values()]
        return datastruct

    def from_datastruct(self,datastruct):
        if utils.app_debug:
            print "Collection::from_datastruct(%s)" % datastruct
        if datastruct is None:
            if utils.app_debug:
                print "DEBUG: from_datastruct -> None, skipping"
            return
        for seed_data in datastruct:
            item = self.factory_produce(self.config,seed_data)
            self.add(item)

    def add(self,ref):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).
        """
        if utils.app_debug:
            print "Collection::add(%s)" % ref
        if ref is None or not ref.is_valid():
            if utils.last_error() is None or utils.last_error() == "":
                utils.set_error("bad_param")
            return False
        self.listing[ref.name] = ref
        return True


    def printable(self):
        """
        Creates a printable representation of the collection suitable
        for reading by humans or parsing from scripts.  Actually scripts
        would be better off reading the YAML in the config files directly.
        """
        if utils.app_debug:
            print "Collection::printable"
        values = map(lambda(a): a.printable(), sorted(self.listing.values()))
        if len(values) > 0:
           return "\n\n".join(values)
        else:
           return msg.m("empty_list")

    def __iter__(self):
        """
	Iterator for the collection.  Allows list comprehensions, etc
	"""
        if utils.app_debug:
            print "Collection::__iter__"
        for a in self.listing.values():
	    yield a

    def __len__(self):
        """
	Returns size of the collection
	"""
        if utils.app_debug:
            print "Collection::__len__"
        return len(self.listing.values())

