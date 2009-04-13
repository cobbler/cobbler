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
   items = request.POST.get('items',[])

   # prepare this, just in case we need it
   t = get_template('system_%s.tmpl' % multi_mode)
   html = t.render(Context({'systems':list}))

   if multi_mode == "delete":
      confirm = request.POST.get('confirm', None)
      if confirm:
         for item in items:
            remote.remove_system(item, token)
      else:
         return HttpResponse(html)
   elif multi_mode == "netboot":
      netboot = request.POST.get('netboot', None)
      if netboot != None:
         for item in items:
            system_id = remote.get_system_handle(item, token)
            remote.modify_system(system_id, 'netboot_enabled', netboot, token)
            remote.save_system(system_id, token, 'edit')
      else:
         return HttpResponse(html)
   elif multi_mode == "profile":
      profile = request.POST.get('profile', None)
      if profile != None:
         for item in items:
            system_id = remote.get_system_handle(item, token)
            remote.modify_system(system_id, 'profile', profile, token)
            remote.save_system(system_id, token, 'edit')
      else:
         return HttpResponse(html)
   elif multi_mode == "power":
      pass

   return HttpResponseRedirect('/cobbler_web/system/list')

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
