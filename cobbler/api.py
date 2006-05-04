"""
python API module for BootConf
see source for bootconf.py for a good API reference

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions
import os
import traceback

import config
import util
import sync
import check
from msg import *

class BootAPI:


    def __init__(self):
       """
       Constructor...
       """
       self.last_error = ''
       self.config = config.BootConfig(self)
       self.utils  = util.BootUtil(self,self.config)
       # if the file already exists, load real data now
       try:
           if self.config.files_exist():
              self.config.deserialize()
       except:
           # traceback.print_exc()
           print m("no_cfg")
           try:
               self.config.serialize()
           except:
               traceback.print_exc()
       if not self.config.files_exist():
           self.config.serialize()


    def clear(self):
       """
       Forget about current list of profiles, distros, and systems
       """
       self.config.clear()


    def get_systems(self):
       """
       Return the current list of systems
       """
       return self.config.get_systems()


    def get_profiles(self):
       """
       Return the current list of profiles
       """
       return self.config.get_profiles()


    def get_distros(self):
       """
       Return the current list of distributions
       """
       return self.config.get_distros()


    def new_system(self):
       """
       Return a blank, unconfigured system, unattached to a collection
       """
       return System(self,None)


    def new_distro(self):
       """
       Create a blank, unconfigured distro, unattached to a collection.
       """
       return Distro(self,None)


    def new_profile(self):
       """
       Create a blank, unconfigured profile, unattached to a collection
       """
       return Profile(self,None)


    def check(self):
       """
       See if all preqs for network booting are valid.  This returns
       a list of strings containing instructions on things to correct.
       An empty list means there is nothing to correct, but that still
       doesn't mean there are configuration errors.  This is mainly useful
       for human admins, who may, for instance, forget to properly set up
       their TFTP servers for PXE, etc.
       """
       return check.BootCheck(self).run()


    def sync(self,dry_run=True):
       """
       Take the values currently written to the configuration files in
       /etc, and /var, and build out the information tree found in
       /tftpboot.  Any operations done in the API that have not been
       saved with serialize() will NOT be synchronized with this command.
       """
       self.config.deserialize();
       configurator = sync.BootSync(self)
       return configurator.sync(dry_run)


    def serialize(self):
       """
       Save the config file(s) to disk.
       """
       self.config.serialize()

    def deserialize(self):
       """
       Load the current configuration from config file(s)
       """
       self.config.deserialize()

#-----------------------------------------

"""
An Item is a serializable thing that can appear in a Collection
"""
class Item:


    def set_name(self,name):
        """
        All objects have names, and with the exception of System
        they aren't picky about it.
        """
        self.name = name
        return True

    def set_kernel_options(self,options_string):
        """
	Kernel options are a comma delimited list of key value pairs,
	like 'a=b,c=d,e=f'
	"""
        self.kernel_options = options_string
        return True

    def to_datastruct(self):
        """
	Returns an easily-marshalable representation of the collection.
	i.e. dictionaries/arrays/scalars.
	"""
        raise exceptions.NotImplementedError

    def is_valid(self):
        """
	The individual set_ methods will return failure if any set is
	rejected, but the is_valid method is intended to indicate whether
	the object is well formed ... i.e. have all of the important
	items been set, are they free of conflicts, etc.
	"""
        return False

#------------------------------------------

class Distro(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.kernel = None
        self.initrd = None
        self.kernel_options = ""
        if seed_data is not None:
           self.name = seed_data['name']
           self.kernel = seed_data['kernel']
           self.initrd = seed_data['initrd']
           self.kernel_options = seed_data['kernel_options']

    def set_kernel(self,kernel):
        """
	Specifies a kernel.  The kernel parameter is a full path, a filename
	in the configured kernel directory (set in /etc/cobbler.conf) or a
	directory path that would contain a selectable kernel.  Kernel
	naming conventions are checked, see docs in the utils module
	for find_kernel.
	"""
        if self.api.utils.find_kernel(kernel):
            self.kernel = kernel
            return True
        self.api.last_error = m("no_kernel")
        return False

    def set_initrd(self,initrd):
        """
	Specifies an initrd image.  Path search works as in set_kernel.
	File must be named appropriately.
	"""
        if self.api.utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        self.api.last_error = m("no_initrd")
        return False

    def is_valid(self):
        """
	A distro requires that the kernel and initrd be set.  All
	other variables are optional.
	"""
        for x in (self.name,self.kernel,self.initrd):
            if x is None: return False
        return True

    def to_datastruct(self):
        return {
           'name': self.name,
           'kernel': self.kernel,
           'initrd' : self.initrd,
           'kernel_options' : self.kernel_options
        }

    def printable(self):
        """
	Human-readable representation.
	"""
        kstr = self.api.utils.find_kernel(self.kernel)
        istr = self.api.utils.find_initrd(self.initrd)
        if kstr is None:
            kstr = "%s (NOT FOUND!)" % self.kernel
        elif os.path.isdir(self.kernel):
            kstr = "%s (FOUND BY SEARCH)" % kstr
        if istr is None:
            istr = "%s (NOT FOUND)" % self.initrd
        elif os.path.isdir(self.initrd):
            istr = "%s (FOUND BY SEARCH)" % istr
        buf = ""
        buf = buf + "distro      : %s\n" % self.name
        buf = buf + "kernel      : %s\n" % kstr
        buf = buf + "initrd      : %s\n" % istr
        buf = buf + "kernel opts : %s" % self.kernel_options
        return buf

#---------------------------------------------

class Profile(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.distro = None # a name, not a reference
        self.kickstart = None
        self.kernel_options = ''
        self.xen_name = 'xenguest'
        self.xen_file_size = 5 # GB
        self.xen_ram = 2048    # MB
        self.xen_mac = ''
        self.xen_paravirt = True
        if seed_data is not None:
           self.name            = seed_data['name']
           self.distro          = seed_data['distro']
           self.kickstart       = seed_data['kickstart']
           self.kernel_options  = seed_data['kernel_options']
           self.xen_name        = seed_data['xen_name']
           if not self.xen_name or self.xen_name == '':
              self.xen_name = self.name
           self.xen_ram         = seed_data['xen_ram']
           self.xen_file_size   = seed_data['xen_file_size']
           self.xen_mac         = seed_data['xen_mac']
           self.xen_paravirt    = seed_data['xen_paravirt']

    def set_distro(self,distro_name):
        """
	Sets the distro.  This must be the name of an existing
	Distro object in the Distros collection.
	"""
        if self.api.get_distros().find(distro_name):
            self.distro = distro_name
            return True
        self.last_error = m("no_distro")
        return False

    def set_kickstart(self,kickstart):
        """
	Sets the kickstart.  This must be a NFS, HTTP, or FTP URL.
	Minor checking of the URL is performed here.
	"""
        if self.api.utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        self.last_error = m("no_kickstart")
        return False

    def set_xen_name(self,str):
        """
	For Xen only.
	Specifies what xenguest install should use for --name.
        xen-net-install may do conflict resolution, so this is mostly
        a hint...  To keep the shell happy, the 'str' cannot
	contain wildcards or slashes and may be subject to some other
        untainting later.
	"""
        # no slashes or wildcards
        for bad in [ '/', '*', '?' ]:
            if str.find(bad) != -1:
                return False
        self.xen_name = str
        return True

    def set_xen_file_size(self,num):
        """
	For Xen only.
	Specifies the size of the Xen image in gigabytes.  xen-net-install
	may contain some logic to ignore 'illogical' values of this size,
	though there are no guarantees.  0 tells xen-net-install to just
	let it pick a semi-reasonable size.  When in doubt, specify the
	size you want.
	"""
        # num is a non-negative integer (0 means default)
        try:
            inum = int(num)
            if inum != float(num):
                return False
            self.xen_file_size = inum
            if inum >= 0:
                return True
            return False
        except:
            return False

    def set_xen_mac(self,mac):
        """
	For Xen only.
	Specifies the mac address (or possibly later, a range) that
	xen-net-install should try to set on the domU.  Seeing these
	have a good chance of conflicting with other domU's, especially
	on a network, this setting is fairly experimental at this time.
	It's recommended that it *not* be used until we can get
	decent use cases for how this might work.
	"""
        # mac needs to be in mac format AA:BB:CC:DD:EE:FF or a range
        # ranges currently *not* supported, so we'll fail them
        if self.api.utils.is_mac(mac):
            self.xen_mac = mac
            return True
        else:
            return False

    def set_xen_paravirt(self,truthiness):
        """
	For Xen only.
	Specifies whether the system is a paravirtualized system or not.
	For ordinary computers, you want to pick 'true'.  Method accepts string
	'true'/'false' in all cases, or Python True/False.
	"""
        # truthiness needs to be True or False, or (lcased) string equivalents
        try:
            if (truthiness == False or truthiness.lower() == 'false'):
                self.xen_paravirt = False
            elif (truthiness == True or truthiness.lower() == 'true'):
                self.xen_paravirt = True
            else:
                return False
        except:
            return False
        return True

    def is_valid(self):
        """
	A profile only needs a name and a distro.  Kickstart info,
	as well as Xen info, are optional.  (Though I would say provisioning
	without a kickstart is *usually* not a good idea).
	"""
        for x in (self.name, self.distro):
            if x is None:
                return False
        return True

    def to_datastruct(self):
        return {
            'name' : self.name,
            'distro' : self.distro,
            'kickstart' : self.kickstart,
            'kernel_options'  : self.kernel_options,
            'xen_name'        : self.xen_name,
            'xen_file_size'   : self.xen_file_size,
            'xen_ram'         : self.xen_ram,
            'xen_mac'         : self.xen_mac,
            'xen_paravirt'    : self.xen_paravirt
        }

    def printable(self):
        buf = ""
        buf = buf + "profile         : %s\n" % self.name
        buf = buf + "distro          : %s\n" % self.distro
        buf = buf + "kickstart       : %s\n" % self.kickstart
        buf = buf + "kernel opts     : %s" % self.kernel_options
        buf = buf + "xen name        : %s" % self.xen_name
        buf = buf + "xen file size   : %s" % self.xen_file_size
        buf = buf + "xen ram         : %s" % self.xen_ram
        buf = buf + "xen mac         : %s" % self.xen_mac
        buf = buf + "xen paravirt    : %s" % self.xen_paravirt
        return buf

#---------------------------------------------

class System(Item):

    def __init__(self,api,seed_data):
        self.api = api
        self.name = None
        self.profile = None # a name, not a reference
        self.kernel_options = ""
        if seed_data is not None:
           self.name = seed_data['name']
           self.profile = seed_data['profile']
           self.kernel_options = seed_data['kernel_options']


    def set_name(self,name):
        """
        A name can be a resolvable hostname (it instantly resolved and replaced with the IP),
        any legal ipv4 address, or any legal mac address. ipv6 is not supported yet but _should_ be.
        See utils.py
        """
        new_name = self.api.utils.find_system_identifier(name)
        if new_name is None or new_name == False:
            self.api.last_error = m("bad_sys_name")
            return False
        self.name = name  # we check it add time, but store the original value.
        return True

    def set_profile(self,profile_name):
        """
	Set the system to use a certain named profile.  The profile
	must have already been loaded into the Profiles collection.
	"""
        if self.api.get_profiles().find(profile_name):
            self.profile = profile_name
            return True
        return False

    def is_valid(self):
        """
	A system is valid when it contains a valid name and a profile.
	"""
        if self.name is None:
            self.api.last_error = m("bad_sys_name")
            return False
        if self.profile is None:
            return False
        return True

    def to_datastruct(self):
        return {
           'name'   : self.name,
           'profile'  : self.profile,
           'kernel_options' : self.kernel_options
        }

    def printable(self):
        buf = ""
        buf = buf + "system       : %s\n" % self.name
        buf = buf + "profile      : %s\n" % self.profile
        buf = buf + "kernel opts  : %s" % self.kernel_options
        return buf

#--------------------------------------

"""
Base class for any serializable lists of things...
"""
class Collection:
    _item_factory = None

    def __init__(self, api, seed_data):
        """
	Constructor.  Requires an API reference.  seed_data
	is a hash of data to feed into the collection, that would
	come from the config file in /var.
	"""
        self.api = api
        self.listing = {}
        if seed_data is not None:
           for x in seed_data:
               self.add(self._item_factory(self.api, x))

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


    def add(self,ref):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).
        """
        if ref is None or not ref.is_valid():
            if self.api.last_error is None or self.api.last_error == "":
                self.api.last_error = m("bad_param")
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


#--------------------------------------------

"""
A distro represents a network bootable matched set of kernels
and initrd files
"""
class Distros(Collection):
    _item_factory = Distro

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        # first see if any Groups use this distro
        for k,v in self.api.get_profiles().listing.items():
            if v.distro == name:
               self.api.last_error = m("orphan_profiles")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        self.api.last_error = m("delete_nothing")
        return False


#--------------------------------------------

"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Xen, there are many
additional options, with client-side defaults (not kept here).
"""
class Profiles(Collection):
    _item_factory = Profile

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        for k,v in self.api.get_systems().listing.items():
           if v.profile == name:
               self.api.last_error = m("orphan_system")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        self.api.last_error = m("delete_nothing")
        return False


#--------------------------------------------

"""
Systems are hostnames/MACs/IP names and the associated profile
they belong to.
"""
class Systems(Collection):
    _item_factory = System

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        if self.find(name):
            del self.listing[name]
            return True
        self.api.last_error = m("delete_nothing")
        return False


