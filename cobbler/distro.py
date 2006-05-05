class Distro(Item):

    def __init__(self,seed_data):
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
        if utils.find_kernel(kernel):
            self.kernel = kernel
            return True
        runtime.set_error("no_kernel")
        return False

    def set_initrd(self,initrd):
        """
	Specifies an initrd image.  Path search works as in set_kernel.
	File must be named appropriately.
	"""
        if utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        runtime.set_error("no_initrd")
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
        kstr = utils.find_kernel(self.kernel)
        istr = utils.find_initrd(self.initrd)
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

