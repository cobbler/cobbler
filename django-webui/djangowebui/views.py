from django.template.loader import get_template
from django.template import Context
from django.template import RequestContext
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from mod_python import apache

import xmlrpclib, time

my_uri = "http://127.0.0.1/cobbler_api"
remote = None
token = None
username = None

def authenhandler(req):
    global remote
    global token
    global username

    password = req.get_basic_auth_pw()
    username = req.user     
    try:
        remote = xmlrpclib.Server(my_uri, allow_none=True)
        token = remote.login(username, password)
        remote.update(token)
        return apache.OK
    except:
        return apache.HTTP_UNAUTHORIZED

def index(request):
   t = get_template('index.tmpl')
   html = t.render(Context({'version': remote.version(token), 'username':username}))
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

def list(request, what=None, filter_name=None, sort_field=None, limit=None, page=None):
    pagename="%s_list" % what

    # Merge and save preferences
    webuipref = remote.get_userpref(token,"webui",pagename)
    if sort_field is not None:
        # if this sort was already applied we need to reverse sort?
        old_field=webuipref.get("sort_field","")
        old_revsort=False
        if old_field.startswith("!"):
            old_field=old_field[1:]
            old_revsort=True
        if old_field == sort_field:
            old_revsort=not old_revsort
        if old_revsort:
            sort_field="!" + sort_field
        webuipref["sort_field"]=sort_field
    if filter_name is not None:
        webuipref["filter"]=filter_name
    if page is not None:
        webuipref["page"]=page
    if limit is not None:
        webuipref["items_per_page"]=limit
    remote.modify_userpref(token,"set_webui",webuipref)
    findmatchtype="all"
    findcriteria={}
    if webuipref.has_key("filter"):
        filter = remote.get_userpref(token,"filter",{'what':what, 'name':webuipref["filter"]})
        if type(filter)==dict:
            findmatchtype=filter["matchtype"]
            findcriteria=filter["criteria"]
    
    sort_field=webuipref.get("sort_field",None)
    page=webuipref.get("page",None)
    items_per_page=webuipref.get("items_per_page",None)

    pageditems = remote.find_items_paged(what,findmatchtype,findcriteria,sort_field,page,items_per_page)

    t = get_template('%s.tmpl'%pagename)
    html = t.render(RequestContext(request,{
        'what'      : what,
        '%ss'%what  : pageditems["items"],
        'pageinfo'  : pageditems["pageinfo"]
    }))
    return HttpResponse(html)

def __setup__pagination(object_list, page):
   # TODO: currently hardcoded at 50 results per page
   #       not sure if this was a setting in the old webui
   #       (if not it should be)

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

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
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

def profile_list(request, profiles=None, page=None):
   if profiles is None:
      profiles = remote.get_profiles(token)

   if page is None and len(profiles) > 50:
      return HttpResponseRedirect('/cobbler_web/profile/list/1')

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
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
         elif field in ('enable_menu'):
            # checkbox fields are weird...
            if field in request.POST:
               remote.modify_profile(profile_id, field, "1", token)
            else:
               remote.modify_profile(profile_id, field, "0", token)
         elif value != None:
            remote.modify_profile(profile_id, field, value, token)

      remote.save_profile(profile_id, token, new_or_edit)

      if editmode == "rename":
         remote.rename_profile(profile_id, profile_name, token)

      return HttpResponseRedirect('/cobbler_web/profile/edit/%s' % profile_name)

def system_list(request, systems=None, page=None):
   if systems is None:
      systems = remote.get_systems(token)

   if page is None and len(systems) > 50:
      return HttpResponseRedirect('/cobbler_web/system/list/1')

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
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

   profiles = []
   if multi_mode == "profile":
      profiles = remote.get_profiles(token)

   t = get_template('system_%s.tmpl' % multi_mode)
   html = t.render(Context({'systems':sel_systems, 'profiles':profiles, 'items':sel_names}))
   return HttpResponse(html)

def system_domulti(request, multi_mode=None):
   items = request.POST.get('items', '').split(" ")
   netboot_enabled = request.POST.get('netboot_enabled', None)
   profile = request.POST.get('profile', None)
   power = request.POST.get('power', None)

   for system_name in items:
      system_id = remote.get_system_handle(system_name, token)
      if multi_mode == "delete":
         remote.remove_system(system_name, token)
      elif multi_mode == "netboot":
         if netboot_enabled is None:
            raise "Cannot modify systems without specifying netboot_enabled"
         remote.modify_system(system_id, "netboot_enabled", netboot_enabled, token)
         remote.save_system(system_id, token, "edit")
      elif multi_mode == "profile":
         if profile is None:
            raise "Cannot modify systems without specifying profile"
         remote.modify_system(system_id, "profile", profile, token)
         remote.save_system(system_id, token, "edit")
      elif multi_mode == "power":
         if power is None:
            raise "Cannot modify systems without specifying power option"
         try:
            remote.power_system(system_id, power, token)
         except:
            # TODO: something besides ignore.  We should probably
            #       print out an error message at the top of whatever
            #       page we go to next, whether it's the system list 
            #       or a results page
            pass
      else:
         raise "Unknowm multiple operation on systems: %s" % str(multi_mode)
      
   return HttpResponseRedirect("/cobbler_web/system/list")

def repo_list(request, repos=None, page=None):
   if repos is None:
      repos = remote.get_repos(token)

   if page is None and len(repos) > 50:
      return HttpResponseRedirect('/cobbler_web/repo/list/1')

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(repos,page)

   if offset > len(repos):
      return HttpResponseRedirect('/cobbler_web/repo/list/%d' % num_pages)

   t = get_template('repo_list.tmpl')
   html = t.render(Context({'what':'repo', 'repos': repos[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
   return HttpResponse(html)

def repo_edit(request, repo_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64','noarch','src']
   repo = None
   if not repo_name is None:
      repo = remote.get_repo(repo_name, True, token)
      repo['ctime'] = time.ctime(repo['ctime'])
      repo['mtime'] = time.ctime(repo['mtime'])
   t = get_template('repo_edit.tmpl')
   html = t.render(Context({'repo': repo, 'available_arches': available_arches, "editable":True}))
   return HttpResponse(html)

def repo_save(request):
   # FIXME: error checking
   field_list = ('name','mirror','keep_updated','priority','mirror_locally','rpm_list','createrepo_flags','arch','yumopts','environment','owners','comment')

   editmode = request.POST.get('editmode', 'edit')
   repo_name = request.POST.get('name', request.POST.get('oldname', None))
   repo_oldname = request.POST.get('oldname', None)

   if repo_name == None:
      return HttpResponse("NO SYSTEM NAME SPECIFIED")

   if editmode == 'copy':
      repo_id = remote.new_repo(token)
   else:
      if editmode == 'edit':
         repo_id = remote.get_repo_handle(repo_name, token)
      else:
         if repo_name == repo_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode)
         repo_id = remote.get_repo_handle(repo_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.remove_repo(repo_name, token)
      return HttpResponseRedirect('/cobbler_web/repo/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == 'name' and editmode == 'rename': continue
         elif field in ('keep_updated','mirror_locally'):
            if field in request.POST:
               remote.modify_repo(repo_id, field, "1", token)
            else:
               remote.modify_repo(repo_id, field, "0", token)
         elif value != None:
            remote.modify_repo(repo_id, field, value, token)

      remote.save_repo(repo_id, token, editmode)

      if editmode == 'rename':
         remote.rename_repo(repo_id, repo_name, token)

      return HttpResponseRedirect('/cobbler_web/repo/edit/%s' % repo_name)

def image_list(request, images=None, page=None):
   if images is None:
      images = remote.get_images(token)

   if page is None and len(images) > 50:
      return HttpResponseRedirect('/cobbler_web/image/list/1')

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(images,page)

   if offset > len(images):
      return HttpResponseRedirect('/cobbler_web/image/list/%d' % num_pages)

   t = get_template('image_list.tmpl')
   html = t.render(Context({'what':'image', 'images': images[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
   return HttpResponse(html)

def image_edit(request, image_name=None):
   available_arches = ['i386','x86_64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   available_virttypes = [['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   available_imagetypes = ['direct','iso','memdisk','virt-clone']

   image = None
   if not image_name is None:
      image = remote.get_image(image_name, True, token)
      image['ctime'] = time.ctime(image['ctime'])
      image['mtime'] = time.ctime(image['mtime'])
   t = get_template('image_edit.tmpl')
   html = t.render(Context({'image': image, 'available_arches': available_arches, 'available_breeds': available_breeds, 'available_virttypes': available_virttypes, 'available_imagetypes': available_imagetypes, "editable":True}))
   return HttpResponse(html)

def image_save(request):
   # FIXME: error checking
   field_list = ('name','image_type','breed','os_version','arch','file','owners','virt_cpus','network_count','virt_file_size','virt_path','virt_bridge','virt_ram','virt_type','virt_auto_boot','comment')

   editmode = request.POST.get('editmode', 'edit')
   image_name = request.POST.get('name', request.POST.get('oldname', None))
   image_oldname = request.POST.get('oldname', None)

   if image_name == None:
      return HttpResponse("NO SYSTEM NAME SPECIFIED")

   if editmode == 'copy':
      image_id = remote.new_image(token)
   else:
      if editmode == 'edit':
         image_id = remote.get_image_handle(image_name, token)
      else:
         if image_name == image_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode)
         image_id = remote.get_image_handle(image_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if delete1 and delete2:
      remote.remove_image(image_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/image/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == 'name' and editmode == 'rename': continue
         elif field in ('netboot_enabled'):
            # checkbox fields are weird...
            if field in request.POST:
               remote.modify_system(system_id, field, "1", token)
            else:
               remote.modify_system(system_id, field, "0", token)
         elif value != None:
            remote.modify_image(image_id, field, value, token)

      remote.save_image(image_id, token, editmode)

      if editmode == 'rename':
         remote.rename_image(image_id, image_name, token)

      return HttpResponseRedirect('/cobbler_web/image/edit/%s' % image_name)

def ksfile_list(request, page=None):
   ksfiles = remote.get_kickstart_templates(token)

   if page is None and len(ksfiles) > 50:
      return HttpResponseRedirect('/cobbler_web/ksfiles/list/1')

   try:
      page = int(page)
      if page < 1:
         page = 1
   except:
      page = 1

   (num_pages,prev_page,next_page,offset,ending) = __setup__pagination(ksfiles,page)

   if offset > len(ksfiles):
      return HttpResponseRedirect('/cobbler_web/ksfiles/list/%d' % num_pages)

   ksfile_list = []
   for ksfile in ksfiles:
      if ksfile.startswith("/var/lib/cobbler/kickstarts") or ksfile.startswith("/etc/cobbler"):
         ksfile_list.append((ksfile,'editable'))
      elif ksfile["kickstart"].startswith("http://") or ksfile["kickstart"].startswith("ftp://"):
         ksfile_list.append((ksfile,'viewable'))
      else:
         ksfile_list.append((ksfile,None))

   t = get_template('ksfile_list.tmpl')
   html = t.render(Context({'what':'ksfile', 'ksfiles': ksfile_list[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
   return HttpResponse(html)

def ksfile_edit(request, ksfile_name=None, editmode='edit'):
   if editmode == 'edit':
      editable = False
   else:
      editable = True
   deleteable = False
   ksdata = ""
   if not ksfile_name is None:
      editable = remote.check_access_no_fail(token, "modify_kickstart", ksfile_name)
      deleteable = remote.is_kickstart_in_use(ksfile_name, token)
      ksdata = remote.read_or_write_kickstart_template(ksfile_name, True, "", token)

   t = get_template('ksfile_edit.tmpl')
   html = t.render(Context({'ksfile_name':ksfile_name, 'deleteable':deleteable, 'ksdata':ksdata, 'editable':editable, 'editmode':editmode}))
   return HttpResponse(html)

def ksfile_save(request):
   # FIXME: error checking

   editmode = request.POST.get('editmode', 'edit')
   ksfile_name = request.POST.get('ksfile_name', None)
   ksdata = request.POST.get('ksdata', "")

   if ksfile_name == None:
      return HttpResponse("NO KSFILE NAME SPECIFIED")
   if editmode != 'edit':
      ksfile_name = "/var/lib/cobbler/kickstarts/" + ksfile_name

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.read_or_write_kickstart_template(ksfile_name, False, -1, token)
      return HttpResponseRedirect('/cobbler_web/ksfile/list')
   else:
      remote.read_or_write_kickstart_template(ksfile_name,False,ksdata,token)
      return HttpResponseRedirect('/cobbler_web/ksfile/edit/%s' % ksfile_name)

def settings(request):
   settings = remote.get_settings()
   t = get_template('settings.tmpl')
   html = t.render(Context({'settings': remote.get_settings()}))
   return HttpResponse(html)

def random_mac(request, virttype="xenpv"):
   random_mac = remote.get_random_mac(virttype, token)
   return HttpResponse(random_mac)

def dosync(request):
   remote.sync(token)
   return HttpResponseRedirect("/cobbler_web/")
