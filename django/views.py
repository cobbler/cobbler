from django.template.loader import get_template
from django.template import Context
from django.template import RequestContext
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from mod_python import apache

import xmlrpclib, time, simplejson

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

def error_page(request,message):
   t = get_template('error_page.tmpl')
   html = t.render(Context({'message': message}))
   return HttpResponse(html)

def list(request, what, page=None):
    if page == None:
        page = int(request.session.get("%s_page" % what, 1))
    limit = int(request.session.get("%s_limit" % what, 50))
    sort_field = request.session.get("%s_sort_field" % what, None)
    filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))

    pageditems = remote.find_items_paged(what,filters,sort_field,page,limit)

    t = get_template('%s_list.tmpl'%what)
    html = t.render(RequestContext(request,{
        'what'      : what,
        '%ss'%what  : pageditems["items"],
        'pageinfo'  : pageditems["pageinfo"],
        'filters'   : filters,
    }))
    return HttpResponse(html)

def genlist(request, what, page=None):
    if page == None:
        page = int(request.session.get("%s_page" % what, 1))
    limit = int(request.session.get("%s_limit" % what, 50))
    sort_field = request.session.get("%s_sort_field" % what, None)
    filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))

    pageditems = remote.find_items_paged(what,filters,sort_field,page,limit)

    # Load columns from settings
    settings = remote.get_settings()
    list_columns = settings.get("web_%s_list_columns" % what,["name"])

    # Prepare list of allowed actions on a single object
    single_actions=[]
    if what in ("system","profile"):
        single_actions.append({ 'name': 'viewks',  'label':'Preview KS' })
    single_actions.append({ 'name': 'edit',    'label':'Edit' })
    single_actions.append({ 'name': 'rename',    'label':'Rename' })
    single_actions.append({ 'name': 'copy',    'label':'Copy' })

    # Prepare list of allowed actions on multiple objects
    multi_actions=[]
    multi_actions.append({ 'name': 'delete',  'label':'Delete' })
    if what in ("systems"):
        multi_actions.append({ 'name': 'netboot', 'label':'Netboot' })
        multi_actions.append({ 'name': 'profile', 'label':'Profile' })
        multi_actions.append({ 'name': 'power', 'label':'Power' })

    # Get table headers values
    fields = remote.get_fields(what, token)
    headers = []
    for list_column in list_columns:
        header={}
        header['field']=list_column
        if list_column.find("::") > 0:
            (field_name,field_key,subfield_name)=list_column.split("::",2)
            field=fields.get(field_name,{})
            subfield=field.get("fields",{}).get(subfield_name,{})
            header['label']="%s(%s)" % (subfield.get("label",""), field_key)
        else:
            field=fields.get(list_column,{})
            header['label']=field.get("label","")
        headers.append(header)

    # Get table row values
    rows = []
    for item in pageditems["items"]:
        row={}
        row['name'] = item["name"]
        row['columns'] = []
        for list_column in list_columns:
            column={}
            if list_column.find("::") > 0:
                (field_name,field_key,subfield_name)=list_column.split("::",2)
                field=fields.get(subfield_name,{})
                subfield=field.get("fields",{}).get(subfield_name,{})
                column["value"]=item.get(field_name,{}).get(field_key,{}).get(subfield_name,"")
                column["type"]=subfield.get("type","")
            else:
                field=fields.get(list_column,{})
                column["value"]=item.get(list_column,"")
                column["type"]=field.get("type","")
            row['columns'].append(column)
        rows.append(row)

    t = get_template('generic_list.tmpl')
    html = t.render(RequestContext(request,{
        'what'           : what,
        'headers'        : headers,
        'rows'           : rows,
        'single_actions' : single_actions,
        'multi_actions'  : multi_actions,
        'pageinfo'       : pageditems["pageinfo"],
        'filters'        : filters,
    }))
    return HttpResponse(html)


def modify_list(request, what, pref, value=None):
    try:
        if pref == "sort":
            old_sort=request.session.get("%s_sort_field" % what,"")
            if old_sort.startswith("!"):
                old_sort=old_sort[1:]
                old_revsort=True
            else:
                old_revsort=False
            if old_sort==value and not old_revsort:
                value="!" + value
            request.session["%s_sort_field" % what] = value
            request.session["%s_page" % what] = 1
        elif pref == "limit":
            request.session["%s_limit" % what] = int(value)
            request.session["%s_page" % what] = 1
        elif pref == "page":
            request.session["%s_page" % what] = int(value)
        else:
            raise ""
        # redirect to the list
        return HttpResponseRedirect("/cobbler_web/%s/list" % what)
    except:
        return error_page(request,"Invalid preference: %s" % pref)

def modify_filter(request, what, action, filter=None):
    try:
        if filter == None: raise ""
        # read session variable for filter
        filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))
        if action == "add":
            (field_name, field_value) = filter.split(":", 1)
            # add this filter
            filters[field_name] = field_value
        else:
            # remove this filter, if it exists
            if filters.has_key(filter):
                del filters[filter]
        # save session variable
        request.session["%s_filters" % what] = simplejson.dumps(filters)
        request.session["%s_page" % what] = 1
        # redirect to the list for this 
        return HttpResponseRedirect("/cobbler_web/%s/list" % what)
    except: 
        return error_page(request,"Invalid filter: %s" % str(filter))

def generic_rename(request, what, obj_name=None, obj_newname=None):
   if obj_name == None:
      return error_page(request,"You must specify a %s to rename" % what)
   if not remote.has_item(what,obj_name):
      return error_page(request,"Unknown %s specified" % what)
   elif not remote.check_access_no_fail(token, "modify_%s" % what, obj_name):
      return error_page(request,"You do not have permission to rename this %s" % what)
   elif obj_newname == None:
      t = get_template('generic_rename.tmpl')
      html = t.render(Context({
            'what' : what,
            'name' : obj_name
      }))
      return HttpResponse(html)
   else:
      obj_id = remote.get_item_handle(what, obj_name, token)
      remote.rename_item(what, obj_id, obj_newname, token)
      return HttpResponseRedirect("/cobbler_web/%s/list" % what)

def generic_multi(request, what, multi_mode=None):
    names = request.POST.getlist('items')

    all_items = remote.get_items(what)
    sel_items = []
    sel_names = []
    for item in all_items:
        if item['name'] in names:
            if not remote.check_access_no_fail(token, "modify_%s" % what, item["name"]):
                return error_page(request,"You do not have permission to modify one or more of the %ss you selected" % what)
            sel_items.append(item)
            sel_names.append(item['name'])

    htmlvars={
        'what'  : what,
        'names' : sel_names,
    }
    if multi_mode in ("profile","power","netboot"):
        htmlname='system_%s.tmpl' % multi_mode
        htmlvars['systems']=sel_items
        if multi_mode=="profile":
            htmlvars['profiles'] = remote.get_profiles(token)
    else:
        htmlname='generic_%s.tmpl' % multi_mode
        htmlvars['items']=sel_items

    t = get_template(htmlname)
    html=t.render(Context(htmlvars))
    return HttpResponse(html)

def generic_domulti(request, what, multi_mode=None):
    names = request.POST.get('names', '').split(" ")

    if multi_mode == "delete":
        for obj_name in names:
            remote.remove_item(what,obj_name, token)
    elif what == "system" and multi_mode == "netboot":
        netboot_enabled = request.POST.get('netboot_enabled', None)
        if netboot_enabled is None:
            raise "Cannot modify systems without specifying netboot_enabled"
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, token)
            remote.modify_system(obj_id, "netboot_enabled", netboot_enabled, token)
            remote.save_system(obj_id, token, "edit")
    elif what == "system" and multi_mode == "profile":
        profile = request.POST.get('profile', None)
        if profile is None:
            raise "Cannot modify systems without specifying profile"
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, token)
            remote.modify_system(obj_id, "profile", profile, token)
            remote.save_system(obj_id, token, "edit")
    elif what == "system" and multi_mode == "power":
        power = request.POST.get('power', None)
        if power is None:
            raise "Cannot modify systems without specifying power option"
        try:
            for obj_name in names:
                obj_id = remote.get_system_handle(obj_name, token)
                remote.power_system(obj_id, power, token)
        except:
            # TODO: something besides ignore.  We should probably
            #       print out an error message at the top of whatever
            #       page we go to next, whether it's the system list 
            #       or a results page
            pass
    else:
        raise "Unknown multiple operation on %ss: %s" % (what,str(multi_mode))
    return HttpResponseRedirect("/cobbler_web/%s/list"%what)

def distro_edit(request, distro_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   distro = None
   if not distro_name is None:
      editable = remote.check_access_no_fail(token, "modify_distro", distro_name)
      distro = remote.get_distro(distro_name, True, token)
      distro['ctime'] = time.ctime(distro['ctime'])
      distro['mtime'] = time.ctime(distro['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_distro", None)

   t = get_template('distro_edit.tmpl')
   html = t.render(Context({'distro': distro, 'available_arches': available_arches, 'available_breeds': available_breeds, "editable":editable}))
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

   t = get_template('profile_list.tmpl')
   html = t.render(Context({'what':'profile', 'profiles': profiles[offset:ending], 'page': page, 'pages': range(1,num_pages+1), 'next_page':next_page, 'prev_page':prev_page}))
   return HttpResponse(html)

def profile_edit(request, profile_name=None, subprofile=0):
   available_virttypes = [['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   profile = None
   if not profile_name is None:
      editable = remote.check_access_no_fail(token, "modify_profile", profile_name)
      profile = remote.get_profile(profile_name, True, token)
      if profile.has_key('ctime'):
         profile['ctime'] = time.ctime(profile['ctime'])
      if profile.has_key('mtime'):
         profile['mtime'] = time.ctime(profile['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_profile", None)

   distros = remote.get_distros(token)
   profiles = remote.get_profiles(token)
   repos = remote.get_repos(token)
   t = get_template('profile_edit.tmpl')
   html = t.render(Context({'profile': profile, 'subprofile': subprofile, 'profiles': profiles, 'distros': distros, 'editable':editable, 'available_virttypes': available_virttypes}))
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

def system_edit(request, system_name=None, editmode="new"):
   available_virttypes = [['<<inherit>>','<<inherit>>'],['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   available_power = ['','bullpap','wti','apc_snmp','ether-wake','ipmilan','drac','ipmitool','ilo','rsa','lpar','bladecenter','virsh','integrity']
   system = None
   if not system_name is None:
      editable = remote.check_access_no_fail(token, "modify_system", system_name)
      system = remote.get_system(system_name, True, token)
      system['ctime'] = time.ctime(system['ctime'])
      system['mtime'] = time.ctime(system['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_system", None)

   distros = remote.get_distros(token)
   profiles = remote.get_profiles(token)
   repos = remote.get_repos(token)
   t = get_template('system_edit.tmpl')
   html = t.render(Context({'system': system, 'profiles': profiles, 'distros': distros, 'repos': repos, 'editmode': editmode, 'available_virttypes': available_virttypes, 'available_power': available_power, 'editable':editable}))
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

   if editmode in ('new','copy'):
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

def repo_edit(request, repo_name=None):
   available_arches = ['i386','x86','x86_64','ppc','ppc64','s390','s390x','ia64','noarch','src']
   repo = None
   if not repo_name is None:
      editable = remote.check_access_no_fail(token, "modify_repo", repo_name)
      repo = remote.get_repo(repo_name, True, token)
      repo['ctime'] = time.ctime(repo['ctime'])
      repo['mtime'] = time.ctime(repo['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_repo", None)

   t = get_template('repo_edit.tmpl')
   html = t.render(Context({'repo': repo, 'available_arches': available_arches, "editable":editable}))
   return HttpResponse(html)

def repo_save(request):
   # FIXME: error checking
   field_list = ('name','mirror','keep_updated','priority','mirror_locally','rpm_list','createrepo_flags','arch','yumopts','environment','owners','comment')

   editmode = request.POST.get('editmode', 'edit')
   repo_name = request.POST.get('name', request.POST.get('oldname', None))
   repo_oldname = request.POST.get('oldname', None)

   if repo_name == None:
      return HttpResponse("NO SYSTEM NAME SPECIFIED")

   if editmode in ('new','copy'):
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

def image_edit(request, image_name=None):
   available_arches = ['i386','x86_64']
   available_breeds = [['redhat','Red Hat Based'], ['debian','Debian'], ['ubuntu','Ubuntu'], ['suse','SuSE']]
   available_virttypes = [['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']]
   available_imagetypes = ['direct','iso','memdisk','virt-clone']

   image = None
   if not image_name is None:
      editable = remote.check_access_no_fail(token, "modify_image", image_name)
      image = remote.get_image(image_name, True, token)
      image['ctime'] = time.ctime(image['ctime'])
      image['mtime'] = time.ctime(image['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_image", None)

   t = get_template('image_edit.tmpl')
   html = t.render(Context({'image': image, 'available_arches': available_arches, 'available_breeds': available_breeds, 'available_virttypes': available_virttypes, 'available_imagetypes': available_imagetypes, "editable":editable}))
   return HttpResponse(html)

def image_save(request):
   # FIXME: error checking
   field_list = ('name','image_type','breed','os_version','arch','file','owners','virt_cpus','network_count','virt_file_size','virt_path','virt_bridge','virt_ram','virt_type','virt_auto_boot','comment')

   editmode = request.POST.get('editmode', 'edit')
   image_name = request.POST.get('name', request.POST.get('oldname', None))
   image_oldname = request.POST.get('oldname', None)

   if image_name == None:
      return HttpResponse("NO SYSTEM NAME SPECIFIED")

   if editmode in ('new','copy'):
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

   ksfile_list = []
   for ksfile in ksfiles:
      if ksfile.startswith("/var/lib/cobbler/kickstarts") or ksfile.startswith("/etc/cobbler"):
         ksfile_list.append((ksfile,ksfile.replace('/var/lib/cobbler/kickstarts/',''),'editable'))
      elif ksfile["kickstart"].startswith("http://") or ksfile["kickstart"].startswith("ftp://"):
         ksfile_list.append((ksfile,ksfile,'','viewable'))
      else:
         ksfile_list.append((ksfile,ksfile,None))

   t = get_template('ksfile_list.tmpl')
   html = t.render(Context({'what':'ksfile', 'ksfiles': ksfile_list}))
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
      deleteable = not remote.is_kickstart_in_use(ksfile_name, token)
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

###


def snippet_list(request, page=None):
   snippets = remote.get_snippets(token)

   snippet_list = []
   for snippet in snippets:
      if snippet.startswith("/var/lib/cobbler/snippets"):
         snippet_list.append((snippet,snippet.replace("/var/lib/cobbler/snippets/",""),'editable'))
      else:
         snippet_list.append((snippet,snippet,None))

   t = get_template('snippet_list.tmpl')
   html = t.render(Context({'what':'snippet', 'snippets': snippet_list}))
   return HttpResponse(html)

def snippet_edit(request, snippet_name=None, editmode='edit'):
   if editmode == 'edit':
      editable = False
   else:
      editable = True
   deleteable = False
   snippetdata = ""
   if not snippet_name is None:
      editable = remote.check_access_no_fail(token, "modify_snippet", snippet_name)
      deleteable = True
      snippetdata = remote.read_or_write_snippet(snippet_name, True, "", token)

   t = get_template('snippet_edit.tmpl')
   html = t.render(Context({'snippet_name':snippet_name, 'deleteable':deleteable, 'snippetdata':snippetdata, 'editable':editable, 'editmode':editmode}))
   return HttpResponse(html)

def snippet_save(request):
   # FIXME: error checking

   editmode = request.POST.get('editmode', 'edit')
   snippet_name = request.POST.get('snippet_name', None)
   snippetdata = request.POST.get('snippetdata', "")

   if snippet_name == None:
      return HttpResponse("NO SNIPPET NAME SPECIFIED")
   if editmode != 'edit':
      snippet_name = "/var/lib/cobbler/snippets/" + snippet_name

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.read_or_write_snippet(snippet_name, False, -1, token)
      return HttpResponseRedirect('/cobbler_web/snippet/list')
   else:
      remote.read_or_write_snippet(snippet_name,False,snippetdata,token)
      return HttpResponseRedirect('/cobbler_web/snippet/edit/%s' % snippet_name)

def network_edit(request, network_name=None, editmode='edit'):
   network = None
   if not network_name is None:
      editable = remote.check_access_no_fail(token, "modify_network", network_name)
      network = remote.get_network(network_name, True, token)
      if network.has_key('ctime'):
         network['ctime'] = time.ctime(network['ctime'])
      if network.has_key('mtime'):
         network['mtime'] = time.ctime(network['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_network", None)

   t = get_template('network_edit.tmpl')
   html = t.render(Context({'network': network, 'editable':editable}))
   return HttpResponse(html)

def network_save(request):
   # FIXME: error checking
   field_list = ('name','cidr','address','gateway','broadcast','name_servers','reserved','used_addresses','free_addresses','comment','owners')

   new_or_edit = request.POST.get('new_or_edit','new')
   editmode = request.POST.get('editmode', 'edit')
   network_name = request.POST.get('name', request.POST.get('oldname', None))
   network_oldname = request.POST.get('oldname', None)
   if network_name == None:
      return HttpResponse("NO NETWORK NAME SPECIFIED")

   if new_or_edit == 'new' or editmode == 'copy':
      network_id = remote.new_network(token)
   else:
      if editmode == 'edit':
         network_id = remote.get_network_handle(network_name, token)
      else:
         if network_name == network_oldname:
            return HttpResponse("The name was not changed, cannot %s" % editmode )
         network_id = remote.get_network_handle(network_oldname, token)

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)
   recursive = request.POST.get('recursive', False)

   if new_or_edit == 'edit' and delete1 and delete2:
      remote.remove_network(network_name, token, recursive)
      return HttpResponseRedirect('/cobbler_web/network/list')
   else:
      for field in field_list:
         value = request.POST.get(field, None)
         if field == "name" and editmode == "rename": continue
         elif value != None:
            remote.modify_network(network_id, field, value, token)

      remote.save_network(network_id, token, new_or_edit)

      if editmode == "rename":
         remote.rename_network(network_id, network_name, token)

      return HttpResponseRedirect('/cobbler_web/network/edit/%s' % network_name)

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

def generic_edit(request, what=None, obj_name=None, editmode="new"):
   obj = None

   child = False
   if what == "subprofile":
      what = "profile"
      child = True

   if not obj_name is None:
      editable = remote.check_access_no_fail(token, "modify_%s" % what, obj_name)
      obj = remote.get_item(what, obj_name)

      if obj.has_key('ctime'):
         obj['ctime'] = time.ctime(obj['ctime'])
      if obj.has_key('mtime'):
         obj['mtime'] = time.ctime(obj['mtime'])
   else:
      editable = remote.check_access_no_fail(token, "new_%s" % what, None)

   fields = remote.get_fields(what, token)
   if obj:
      for key in fields.keys():
         fields[key]["value"] = obj.get(key,"")

   # populate select lists with data stored in cobbler,
   # based on what we are currently editing
   if what == "profile":
      if (obj and obj["parent"] not in (None,"")) or child:
         fields["parent"]["list"] = remote.get_profiles(token)
         del fields["distro"]
      else:
         fields["distro"]["list"] = remote.get_distros(token)
         del fields["parent"]
      fields["repos"]["list"]  = remote.get_repos(token)

   sorted_fields = [(key, val) for key,val in fields.items()] 
   sorted_fields.sort(lambda a,b: cmp(a[1]["order"], b[1]["order"])) 

   # Enable empty name field when copying
   if editmode == "copy":
      fields["name"]["setopts"] = ""
      fields["name"]["value"] = ""
     
   t = get_template('generic_edit.tmpl')
   html = t.render(Context({'what': what, 'obj':obj, 'fields': sorted_fields, 'editmode': editmode, 'editable':editable}))
   return HttpResponse(html)

def generic_save(request,what):
    editmode = request.POST.get('editmode', 'edit')
    obj_name = request.POST.get('name', "")
    
    if obj_name == "":
        return error_page(request,"%s name field is missing" % what)
              
    if editmode == "edit":
        if not remote.has_item( what, obj_name ):
            return error_page(request,"Failed to lookup %s: %s" % (what,obj_name))
        obj_id = remote.get_item_handle( what, obj_name, token )
    else:
        if remote.has_item( what, obj_name ):
            return error_page(request,"Failed to create new %s: %s already exists." % (what,obj_name))
        obj_id = remote.new_item( what, token )

    fields = remote.get_fields(what, token)
    for field in fields.keys():
        if field == 'name' and editmode == 'edit':
            continue
        elif what == 'system' and field == "interfaces":
            interface_field_list = ('macaddress','ipaddress','dns_name','static_routes','static','virtbridge','dhcptag','subnet','bonding','bondingopts','bondingmaster','present','original')
            interfaces = request.POST.get('interface_list', "").split(",")
            for interface in interfaces:
                ifdata = {}
                for item in interface_field_list:
                    ifdata["%s-%s" % (item,interface)] = request.POST.get("%s-%s" % (item,interface), "")
                if ifdata['present-%s' % interface] == "0" and ifdata['original-%s' % interface] == "1":
                    remote.modify_system(obj_id, 'delete_interface', interface, token)
                elif ifdata['present-%s' % interface] == "1":
                    remote.modify_system(obj_id, 'modify_interface', ifdata, token)
        else:
            value = request.POST.get(field, None)
            if value != None:
                remote.modify_item(what,obj_id, field, value, token)
                
    remote.save_item(what, obj_id, token, editmode)
    return HttpResponseRedirect('/cobbler_web/%s/list' % what)
