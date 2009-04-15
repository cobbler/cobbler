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

def __setup__pagination(object_list, page):
   prev_page = page - 1
   next_page = page + 1

   num_pages = (len(object_list)-1)/50 + 1
   if num_pages > 1:
      offset = (page-1) * 50
      ending = offset + 50
      if ending > len(object_list):
         ending = len(object_list)
   else:
      offset = 0
      ending = len(object_list)

   if prev_page < 1:
      prev_page = None
   if next_page > num_pages:
      next_page = None

   return (num_pages,prev_page,next_page,offset,ending)


def distro_list(request, distros=None, page=None):
   if distros is None:
      distros = remote.get_distros(token)

   if page is None and len(distros) > 50:
      return HttpResponseRedirect('/cobbler_web/distro/list/1')
   page = int(page)
   if page < 1:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(distros,page)

   if offset > len(distros):
      return HttpResponseRedirect('/cobbler_web/distro/list/%d' % num_pages)

   t = get_template('distro_list.tmpl')
   html = t.render(Context({'what':'distro', 'distros': distros[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
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

   new_or_edit = request.POST.get('new_or_edit','new')
   editmode = request.POST.get('editmode', 'edit')
   distro_name = request.POST.get('name', request.POST.get('oldname', None))
   distro_oldname = request.POST.get('oldname', None)
   if distro_name == None:
      return HttpResponse("NO DISTRO NAME SPECIFIED")

   if new_or_edit == 'new' or editmode == 'copy':
      distro_id = remote.new_distro(token)
   else:
      if editmode == 'edit':
         distro_id = remote.get_distro_handle(distro_name, token)
      else:
         if distro_name == distro_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode)
         distro_id = remote.get_distro_handle(distro_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if new_or_edit == 'edit' and delete1 and delete2:
      remote.remove_distro(distro_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/distro/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == 'name' and editmode == 'rename': continue
         elif value != None:
            remote.modify_distro(distro_id, field, value, token)

      remote.save_distro(distro_id, token, new_or_edit)

      if editmode == 'rename':
         remote.rename_distro(distro_id, distro_name, token)

      return HttpResponseRedirect('/cobbler_web/distro/edit/%s' % distro_name)

def profile_list(request, profiles=None, page=0):
   if profiles is None:
      profiles = remote.get_profiles(token)

   if page is None and len(profiles) > 50:
      return HttpResponseRedirect('/cobbler_web/profile/list/1')
   page = int(page)
   if page < 1:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(profiles,page)

   if offset > len(profiles):
      return HttpResponseRedirect('/cobbler_web/profile/list/%d' % num_pages)

   for profile in profiles:
      if profile["kickstart"]:
         if profile["kickstart"].startswith("http://") or profile["kickstart"].startswith("ftp://"):
            profile["web_kickstart"] = profile.kickstart
         elif profile["kickstart"].startswith("nfs://"):
            profile["nfs_kickstart"] = profile.kickstart
   t = get_template('profile_list.tmpl')
   html = t.render(Context({'what':'profile', 'profiles': profiles[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
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

   new_or_edit = request.POST.get('new_or_edit','new')
   editmode = request.POST.get('editmode', 'edit')
   profile_name = request.POST.get('name', request.POST.get('oldname', None))
   profile_oldname = request.POST.get('oldname', None)
   if profile_name == None:
      return HttpResponse("NO PROFILE NAME SPECIFIED")

   subprofile = int(request.POST.get('subprofile','0'))
   if new_or_edit == 'new' or editmode == 'copy':
      if subprofile:
         profile_id = remote.new_subprofile(token)
      else:
         profile_id = remote.new_profile(token)
   else:
      if editmode == 'edit':
         profile_id = remote.get_profile_handle(profile_name, token)
      else:
         if profile_name == profile_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode )
         profile_id = remote.get_profile_handle(profile_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if new_or_edit == 'edit' and delete1 and delete2:
      remote.remove_profile(profile_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/profile/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == "distro" and subprofile: continue
         elif field == "parent" and not subprofile: continue
         elif field == "name" and editmode == "rename": continue
         if value != None:
            remote.modify_profile(profile_id, field, value, token)

      remote.save_profile(profile_id, token, new_or_edit)

      if editmode == "rename":
         remote.rename_profile(profile_id, profile_name, token)

      return HttpResponseRedirect('/cobbler_web/profile/edit/%s' % profile_name)

def system_list(request, systems=None, page=0):
   if systems is None:
      systems = remote.get_systems(token)

   if page is None and len(systems) > 50:
      return HttpResponseRedirect('/cobbler_web/system/list/1')
   page = int(page)
   if page < 1:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(systems,page)

   if offset > len(systems):
      return HttpResponseRedirect('/cobbler_web/system/list/%d' % num_pages)

   t = get_template('system_list.tmpl')
   html = t.render(Context({'what':'system', 'systems': systems[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
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
   # FIXME: error checking
   field_list = ('name','profile','kopts','kopts_post','ksmeta','owners','netboot_enabled','server','virt_file_size','virt_cpus','virt_ram','virt_type','virt_path','virt_auto_boot','comment','power_type','power_user','power_pass','power_id','power_address','name_servers','name_servers_search','gateway','hostname','redhat_management_key','redhat_management_server','mgmt_classes')
   interface_field_list = ('macaddress','ipaddress','dns_name','static_routes','static','virtbridge','dhcptag','subnet','bonding','bondingopts','bondingmaster','present','original')

   editmode = request.POST.get('editmode', 'edit')
   system_name = request.POST.get('name', request.POST.get('oldname', None))
   system_oldname = request.POST.get('oldname', None)
   interfaces = request.POST.get('interface_list', "").split(",")

   if system_name == None:
      return HttpResponse("NO SYSTEM NAME SPECIFIED")

   if editmode == 'copy':
      system_id = remote.new_system(token)
   else:
      if editmode == 'edit':
         system_id = remote.get_system_handle(system_name, token)
      else:
         if system_name == system_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode)
         system_id = remote.get_system_handle(system_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.remove_system(system_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/system/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == 'name' and editmode == 'rename': continue
         elif value != None:
            remote.modify_system(system_id, field, value, token)

      for interface in interfaces:
         ifdata = {}
         for item in interface_field_list:
            ifdata["%s-%s" % (item,interface)] = request.POST.get("%s-%s" % (item,interface), "")

         if ifdata['present-%s' % interface] == "0" and ifdata['original-%s' % interface] == "1":
            remote.modify_system(system_id, 'delete_interface', interface, token)
         elif ifdata['present-%s' % interface] == "1":
            remote.modify_system(system_id, 'modify_interface', ifdata, token)

      remote.save_system(system_id, token, editmode)

      if editmode == 'rename':
         remote.rename_system(system_id, system_name, token)

      return HttpResponseRedirect('/cobbler_web/system/edit/%s' % system_name)

def system_rename(request, system_name=None, system_newname=None):
   if system_name == None:
      return HttpResponse("You must specify a system to rename")
   elif system_newname == None:
      t = get_template('system_rename.tmpl')
      html = t.render(Context({'system':system_name}))
      return HttpResponse(html)
   else:
      system_id = remote.get_system_handle(system_name, token)
      remote.rename_system(system_id, system_newname, token)
      return HttpResponseRedirect("/cobbler_web/system/list")

def system_multi(request, multi_mode=None):
   items = request.POST.getlist('items')

   all_systems = remote.get_systems(token)
   sel_systems = []
   sel_names = []
   for system in all_systems:
      if system['name'] in items:
         sel_systems.append(system)
         sel_names.append(system['name'])

   t = get_template('system_%s.tmpl' % multi_mode)
   html = t.render(Context({'systems':sel_systems, 'items':sel_names}))
   return HttpResponse(html)

def system_domulti(request, multi_mode=None):
   items = request.POST.get('items', '').split(" ")
   netboot = request.POST.get('netboot', None)
   profile = request.POST.get('profile', None)
   power   = request.POST.get('power', None)

   for system_name in items:
      system_id = remote.get_system(system_name, token)
      if multi_mode == "delete":
         remote.remove_system(system_name, token)
      elif multi_mode == "netboot":
         if netboot is None:
            raise "Cannot modify systems without specifying netboot_enabled"
         remote.modify_system(system_id, "netboot_enabled", netboot, token)
         remote.save_system(system_id, token, "edit")
      elif multi_mode == "profile":
         if profile is None:
            raise "Cannot modify systems without specifying profile"
         remote.modify_system(system_id, "profile", profile, token)
         remote.save_system(system_id, token, "edit")
      elif multi_mode == "power":
         if power is None:
            raise "Cannot modify systems without specifying power option"
         remote.modify_system(system_id, "power", power, token)
         remote.save_system(system_id, token, "edit")
      else:
         raise "Unknowm multiple operation on systems: %s" % str(multi_mode)
      
   #return HttpResponse("doing multi: " + str(multi_mode) + " on " + str(items))
   return HttpResponseRedirect("/cobbler_web/system/list")

def repo_list(request, repos=None, page=0):
   if repos is None:
      repos = remote.get_repos(token)
   t = get_template('repo_list.tmpl')
   html = t.render(Context({'what':'repo', 'repos': repos}))
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

def image_list(request, images=None, page=0):
   if images is None:
      images = remote.get_images(token)
   t = get_template('image_list.tmpl')
   html = t.render(Context({'what':'image', 'images': images}))
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

def ksfile_list(request, page=0):
   ksfiles = remote.get_kickstart_templates(token)
   t = get_template('ksfile_list.tmpl')
   html = t.render(Context({'what':'ksfile', 'ksfiles': ksfiles}))
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
