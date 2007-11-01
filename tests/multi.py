import cobbler.api as capi

api = capi.BootAPI()

SYSTEMS_COUNT = 10000 

distros = api.distros()
profiles = api.profiles()
systems = api.systems()

distro = api.new_distro()
distro.set_name("d1")
distro.set_kernel("/tmp/foo")
distro.set_initrd("/tmp/foo")
distros.add(distro)

profile = api.new_profile()
profile.set_name("p1")
profile.set_distro("d1")
profiles.add(profile)
  
for x in xrange(0,SYSTEMS_COUNT):
    if (x%10==0): print "%s" % x
    system = api.new_system()
    system.set_name("system%d" % x) 
    system.set_profile("p1")
    systems.add(system,with_copy=True)

api.serialize()
