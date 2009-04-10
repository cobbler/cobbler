from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from django.http import HttpResponseRedirect

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

def dosearch(request, what):
   criteria = {}
   for i in range(1,6):
      key = request.POST.get("key%d" % i, None)
      val = request.POST.get("value%d" % i, None)
      if key not in (None, ''):
         if val != None:
            val = val.replace('"','')
         criteria[key] = val

   results = []
   if what == "distro":
      results = remote.find_distro(criteria,True,token)
      return distro_list(request, results)
   elif what == "profile":
      results = remote.find_profile(criteria,True,token)
      return profile_list(request, results)
   elif what == "system":
      results = remote.find_system(criteria,True,token)
      return system_list(request, results)
   elif what == "image":
      results = remote.find_image(criteria,True,token)
      return image_list(request, results)
   elif what == "repo":
      results = remote.find_repo(criteria,True,token)
      return repo_list(request, results)
   else:
      raise "internal error, unknown search type"

def distro_list(request, distros=None):
   if distros is None:
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

def distro_save(request):
   # FIXME: error checking
   field_list = ('name','comment','kernel','initrd','kopts','kopts','kopts_post','ksmeta','arch','breed','os_version','mgmt_classes','template_files','redhat_management_key','redhat_management_server')

   distro_name = request.POST.get('oldname', request.POST.get('name',None))
   if distro_name == None:
      return HttpResponse("NO DISTRO NAME SPECIFIED")

   if request.POST.get('new_or_edit','new') == 'new':
      distro_id = remote.new_distro(token)
   else:
      distro_id = remote.get_distro_handle(distro_name, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if delete1 and delete2:
      remote.remove_distro(distro_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/distro/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if value != None:
            remote.modify_distro(distro_id, field, value, token)

      remote.save_distro(distro_id, token, request.POST.get('new_or_edit','new'))
      return HttpResponseRedirect('/cobbler_web/distro/edit/%s' % distro_name)

def profile_list(request, profiles=None):
   if profiles is None:
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
      if profile.has_key('ctime'):
         profile['ctime'] = time.ctime(profile['ctime'])
      if profile.has_key('mtime'):
         profile['mtime'] = time.ctime(profile['mtime'])
   distros = remote.get_distros(token)
   profiles = remote.get_profiles(token)
   repos = remote.get_repos(token)
   t = get_template('profile_edit.tmpl')
   html = t.render(Context({'profile': profile, 'subprofile': subprofile, 'profiles': profiles, 'distros': distros, 'editable':True, 'available_virttypes': available_virttypes}))
   return HttpResponse(html)

def profile_save(request):
   # FIXME: error checking
   field_list = ('name','parent','profile','distro','enable_menu','kickstart','kopts','kopts_post','virt_auto_boot','virt_file_size','virt_ram','ksmeta','template_files','repos','virt_path','virt_type','virt_bridge','virt_cpus','dhcp_tag','server','owners','mgmt_classes','comment','name_servers','name_servers_search','redhat_management_key','redhat_management_server')

   profile_name = request.POST.get('oldname', request.POST.get('name',None))
   if profile_name == None:
      return HttpResponse("NO PROFILE NAME SPECIFIED")

   subprofile = int(request.POST.get('subprofile','0'))
   if request.POST.get('new_or_edit','new') == 'new':
      if subprofile:
         profile_id = remote.new_subprofile(token)
      else:
         profile_id = remote.new_profile(token)
   else:
      profile_id = remote.get_profile_handle(profile_name, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if delete1 and delete2:
      remote.remove_profile(profile_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/profile/list')
   else:
      for field in field_list:
         if field == "distro" and subprofile: continue
         elif field == "parent" and not subprofile: continue

         value = request.POST.get(field, None)
         if value != None:
            remote.modify_profile(profile_id, field, value, token)

      remote.save_profile(profile_id, token, request.POST.get('new_or_edit','new'))
      return HttpResponseRedirect('/cobbler_web/profile/edit/%s' % profile_name)

def system_list(request, systems=None):
   if systems is None:
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

def system_save(request):
   return HttpResponse("")

def repo_list(request, repos=None):
   if repos is None:
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

def image_list(request, images=None):
   if images is None:
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

def random_mac(request, virttype="xenpv"):
   random_mac = remote.get_random_mac(virttype, token)
   return HttpResponse(random_mac)
