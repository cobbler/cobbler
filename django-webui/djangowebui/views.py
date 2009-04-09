from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse

import xmlrpclib, time

my_uri = "http://127.0.0.1/cobbler_api"
remote = xmlrpclib.Server(my_uri)
token = remote.login('testing', 'testing')

def index(request):
   t = get_template('index.tmpl')
   html = t.render(Context({'version': remote.version(token)}))
   return HttpResponse(html)

def search(request, what):
   t = get_template('search.tmpl')
   html = t.render(Context({'what':what, 'item_count':["1","2","3","4","5"]}))
   return HttpResponse(html)

def distro_list(request):
   distros = remote.get_distros(token)
   t = get_template('distro_list.tmpl')
   html = t.render(Context({'distros': distros}))
   return HttpResponse(html)

def distro_edit(request, distro_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   distro = None
   if not distro_name is None:
      distro = remote.get_distro(distro_name, True, token)
      distro['ctime'] = time.ctime(distro['ctime'])
      distro['mtime'] = time.ctime(distro['mtime'])
   t = get_template('distro_edit.tmpl')
   html = t.render(Context({'distro': distro, 'available_arches': available_arches, 'available_breeds': available_breeds, "editable":True}))
   return HttpResponse(html)

def profile_list(request):
   profiles = remote.get_profiles(token)
   for profile in profiles:
      if profile["kickstart"]:
         if profile["kickstart"].startswith("http://") or profile["kickstart"].startswith("ftp://"):
            profile["web_kickstart"] = profile.kickstart
         elif profile["kickstart"].startswith("nfs://"):
            profile["nfs_kickstart"] = profile.kickstart
   t = get_template('profile_list.tmpl')
   html = t.render(Context({'profiles': profiles}))
   return HttpResponse(html)

def profile_edit(request, profile_name=None, subprofile=0):
   available_virttypes = [['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   profile = None
   if not profile_name is None:
      profile = remote.get_profile(profile_name, True, token)
      profile['ctime'] = time.ctime(profile['ctime'])
      profile['mtime'] = time.ctime(profile['mtime'])
   distros = remote.get_distros(token)
   profiles = remote.get_profiles(token)
   repos = remote.get_repos(token)
   t = get_template('profile_edit.tmpl')
   html = t.render(Context({'profile': profile, 'subprofile': subprofile, 'profiles': profiles, 'distros': distros, 'editable':True, 'available_virttypes': available_virttypes}))
   return HttpResponse(html)

def system_list(request):
   systems = remote.get_systems(token)
   t = get_template('system_list.tmpl')
   html = t.render(Context({'systems': systems}))
   return HttpResponse(html)

def system_edit(request, system_name=None, editmode="new"):
   available_virttypes = [['<<inherit>>','<<inherit>>'],['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   available_power = ['','bullpap','wti','apc_snmp','ether-wake','ipmilan','drac','ipmitool','ilo','rsa','lpar','bladecenter','virsh','integrity']
   system = None
   if not system_name is None:
      system = remote.get_system(system_name, True, token)
      system['ctime'] = time.ctime(system['ctime'])
      system['mtime'] = time.ctime(system['mtime'])
   distros = remote.get_distros(token)
   profiles = remote.get_profiles(token)
   repos = remote.get_repos(token)
   t = get_template('system_edit.tmpl')
   html = t.render(Context({'system': system, 'profiles': profiles, 'distros': distros, 'repos': repos, 'editmode': editmode, 'available_virttypes': available_virttypes, 'available_power': available_power, 'editable':True}))
   return HttpResponse(html)

def repo_list(request):
   repos = remote.get_repos(token)
   t = get_template('repo_list.tmpl')
   html = t.render(Context({'repos': repos}))
   return HttpResponse(html)

def repo_edit(request, repo_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   repo = None
   if not repo_name is None:
      repo = remote.get_repo(repo_name, True, token)
   t = get_template('repo_edit.tmpl')
   html = t.render(Context({'repo': repo, 'available_arches': available_arches, 'available_breeds': available_breeds, "editable":True}))
   return HttpResponse(html)

def image_list(request):
   images = remote.get_images(token)
   t = get_template('image_list.tmpl')
   html = t.render(Context({'images': images}))
   return HttpResponse(html)

def image_edit(request, image_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   image = None
   if not image_name is None:
      image = remote.get_image(image_name, True, token)
   t = get_template('image_edit.tmpl')
   html = t.render(Context({'image': image, 'available_arches': available_arches, 'available_breeds': available_breeds, "editable":True}))
   return HttpResponse(html)

def ksfile_list(request):
   ksfiles = remote.get_kickstart_templates(token)
   t = get_template('ksfile_list.tmpl')
   html = t.render(Context({'ksfiles': ksfiles}))
   return HttpResponse(html)

def ksfile_edit(request, ksfile_name=None):
   """
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   ksfile = None
   if not ksfile_name is None:
      ksfile = remote.get_ksfile(ksfile_name, True, token)
   t = get_template('ksfile_edit.tmpl')
   html = t.render(Context({'ksfile': ksfile, 'available_arches': available_arches, 'available_breeds': available_breeds, "editable":True}))
   """
   return HttpResponse("NOT IMPLEMENTED YET")

