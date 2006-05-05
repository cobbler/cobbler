
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

