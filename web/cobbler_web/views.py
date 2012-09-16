from django.template.loader import get_template
from django.template import Context
from django.template import RequestContext
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views.decorators.http import require_POST

try:
    from django.views.decorators.csrf import csrf_protect
except:
    # Old Django, fudge the @csrf_protect decorator to be a pass-through 
    # that does nothing. Django decorator shell based on this page: 
    # http://passingcuriosity.com/2009/writing-view-decorators-for-django/
    def csrf_protect(f):
        def _dec(view_func):
            def _view(request,*args,**kwargs):
                return view_func(request,*args,**kwargs)
            _view.__name__ = view_func.__name__
            _view.__dict__ = view_func.__dict__
            _view.__doc__  = view_func.__doc__
            return _view
        if f is None:
            return _dec
        else:
            return _dec(f)

import xmlrpclib
import time
import simplejson
import string
import distutils
import exceptions
import time

import cobbler.item_distro    as item_distro
import cobbler.item_profile   as item_profile
import cobbler.item_system    as item_system
import cobbler.item_repo      as item_repo
import cobbler.item_image     as item_image
import cobbler.item_mgmtclass as item_mgmtclass
import cobbler.item_package   as item_package
import cobbler.item_file      as item_file
import cobbler.settings       as item_settings
import cobbler.field_info     as field_info
import cobbler.utils          as utils

url_cobbler_api = None
remote = None
username = None

#==================================================================================

def index(request):
   """
   This is the main greeting page for cobbler web.
   """
   if not test_user_authenticated(request): return login(request,next="/cobbler_web")

   t = get_template('index.tmpl')
   html = t.render(RequestContext(request,{
        'version' : remote.extended_version(request.session['token'])['version'],
        'username': username,
   }))
   return HttpResponse(html)

#========================================================================

def task_created(request):
   """
   Let's the user know what to expect for event updates.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/task_created")
   t = get_template("task_created.tmpl")
   html = t.render(RequestContext(request,{
       'version'  : remote.extended_version(request.session['token'])['version'],
       'username' : username
   }))
   return HttpResponse(html)

#========================================================================

def error_page(request,message):
   """
   This page is used to explain error messages to the user.
   """
   if not test_user_authenticated(request): return login(request)
   # FIXME: test and make sure we use this rather than throwing lots of tracebacks for
   # field errors
   t = get_template('error_page.tmpl')
   message = message.replace("<Fault 1: \"<class 'cobbler.cexceptions.CX'>:'","Remote exception: ")
   message = message.replace("'\">","")
   html = t.render(RequestContext(request,{
       'version' : remote.extended_version(request.session['token'])['version'],
       'message' : message,
       'username': username
   }))
   return HttpResponse(html)

#==================================================================================

def get_fields(what, is_subobject, seed_item=None):

    """
    Helper function.  Retrieves the field table from the cobbler objects
    and formats it in a way to make it useful for Django templating.
    The field structure indicates what fields to display and what the default
    values are, etc.
    """

    if what == "distro":
       field_data = item_distro.FIELDS
    if what == "profile":
       field_data = item_profile.FIELDS
    if what == "system":
       field_data = item_system.FIELDS
    if what == "repo":
       field_data = item_repo.FIELDS
    if what == "image":
       field_data =  item_image.FIELDS
    if what == "mgmtclass":
        field_data = item_mgmtclass.FIELDS
    if what == "package":
        field_data = item_package.FIELDS
    if what == "file":
        field_data = item_file.FIELDS
    if what == "setting":
        field_data = item_settings.FIELDS

    settings = remote.get_settings()

    fields = []
    for row in field_data:

        # if we are subprofile and see the field "distro", make it say parent
        # with this really sneaky hack here
        if is_subobject and row[0] == "distro":
            row[0] = "parent"
            row[3] = "Parent object"
            row[5] = "Inherit settings from this profile"
            row[6] = []

        elem = {
            "name"                    : row[0],
            "dname"                   : row[0].replace("*",""),
            "value"                   : "?",
            "caption"                 : row[3],
            "editable"                : row[4],
            "tooltip"                 : row[5],
            "choices"                 : row[6],
            "css_class"               : "generic",
            "html_element"            : "generic",
        }

        if not elem["editable"]:
            continue

        if seed_item is not None:
            if what == "setting":
                elem["value"] = seed_item[row[0]]
            elif row[0].startswith("*"):
                # system interfaces are loaded by javascript, not this
                elem["value"]             = ""
                elem["name"]              = row[0].replace("*","")
            elif row[0].find("widget") == -1:
                elem["value"]             = seed_item[row[0]]
        elif is_subobject:
            elem["value"]             = row[2]
        else:
            elem["value"]             = row[1]

        if elem["value"] is None:
            elem["value"] = ""

        # we'll process this for display but still need to present the original to some
        # template logic
        elem["value_raw"]             = elem["value"]

        if isinstance(elem["value"],basestring) and elem["value"].startswith("SETTINGS:"):
            key = elem["value"].replace("SETTINGS:","",1)
            elem["value"] = settings[key]

        # flatten hashes of all types, they can only be edited as text
        # as we have no HTML hash widget (yet)
        if type(elem["value"]) == type({}):
            if elem["name"] == "mgmt_parameters":
                #Render dictionary as YAML for Management Parameters field
                tokens = []
                for (x,y) in elem["value"].items():
                   if y is not None:
                      tokens.append("%s: %s" % (x,y))
                   else:
                      tokens.append("%s: " % x)
                elem["value"] = "{ %s }" % ", ".join(tokens)
            else:
                tokens = []
                for (x,y) in elem["value"].items():
                   if y is not None and y.strip() != "~":
                      y = y.replace(" ","\\ ")
                      tokens.append("%s=%s" % (x,y))
                   else:
                      tokens.append("%s" % x)
                elem["value"] = " ".join(tokens)

        name = row[0]
        if name.find("_widget") != -1:
            elem["html_element"] = "widget"
        elif name in field_info.USES_SELECT:
            elem["html_element"] = "select"
        elif name in field_info.USES_MULTI_SELECT:
            elem["html_element"] = "multiselect"
        elif name in field_info.USES_RADIO:
            elem["html_element"] = "radio"
        elif name in field_info.USES_CHECKBOX:
            elem["html_element"] = "checkbox"
        elif name in field_info.USES_TEXTAREA:
            elem["html_element"] = "textarea"
        else:
            elem["html_element"] = "text"

        elem["block_section"] = field_info.BLOCK_MAPPINGS.get(name, "General")

        # flatten lists for those that aren't using select boxes
        if type(elem["value"]) == type([]):
            if elem["html_element"] != "select":
                elem["value"] = string.join(elem["value"], sep=" ")

        # FIXME: need to handle interfaces special, they are prefixed with "*"

        fields.append(elem)

    return fields

#==================================================================================

def __tweak_field(fields,field_name,attribute,value):
    """
    Helper function to insert extra data into the field list.
    """
    # FIXME: eliminate this function.
    for x in fields:
       if x["name"] == field_name:
           x[attribute] = value

#==================================================================================


def __format_columns(column_names,sort_field):
    """
    Format items retrieved from XMLRPC for rendering by the generic_edit template
    """
    dataset = []

    # Default is sorting on name
    if sort_field is not None:
        sort_name = sort_field
    else:
        sort_name = "name"

    if sort_name.startswith("!"):
        sort_name = sort_name[1:]
        sort_order = "desc"
    else:
        sort_order = "asc"

    for fieldname in column_names:
        fieldorder = "none"
        if fieldname == sort_name:
            fieldorder = sort_order
        dataset.append([fieldname,fieldorder])
    return dataset


#==================================================================================

def __format_items(items, column_names):
    """
    Format items retrieved from XMLRPC for rendering by the generic_edit template
    """
    dataset = []
    for itemhash in items:
        row = []
        for fieldname in column_names:
            if fieldname == "name":
                html_element = "name"
            elif fieldname in [ "system", "repo", "distro", "profile", "image", "mgmtclass", "package", "file" ]:
                html_element = "editlink"
            elif fieldname in field_info.USES_CHECKBOX:
                html_element = "checkbox"
            else:
                html_element = "text"
            row.append([fieldname,itemhash[fieldname],html_element])
        dataset.append(row)
    return dataset

#==================================================================================

def genlist(request, what, page=None):
    """
    Lists all object types, complete with links to actions
    on those objects.
    """
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/list" % what)

    # get details from the session
    if page == None:
        page = int(request.session.get("%s_page" % what, 1))
    limit = int(request.session.get("%s_limit" % what, 50))
    sort_field = request.session.get("%s_sort_field" % what, "name")
    filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))
    pageditems = remote.find_items_paged(what,utils.strip_none(filters),sort_field,page,limit)

    # what columns to show for each page?
    # we also setup the batch actions here since they're dependent 
    # on what we're looking at

    # everythng gets batch delete 
    batchactions = [
        ["Delete","delete","delete"],
    ]

    if what == "distro":
       columns = [ "name" ]
       batchactions += [
           ["Build ISO","buildiso","enable"],
       ]
    if what == "profile":
       columns = [ "name", "distro" ]
       batchactions += [
           ["Build ISO","buildiso","enable"],
       ]
    if what == "system":
       # FIXME: also list network, once working
       columns = [ "name", "profile", "status", "netboot_enabled" ]
       batchactions += [
           ["Power on","power","on"],
           ["Power off","power","off"],
           ["Reboot","power","reboot"],
           ["Change profile","profile",""],
           ["Netboot enable","netboot","enable"],
           ["Netboot disable","netboot","disable"],
           ["Build ISO","buildiso","enable"],
       ]
    if what == "repo":
       columns = [ "name", "mirror" ]
       batchactions += [
           ["Reposync","reposync","go"],
       ]
    if what == "image":
       columns = [ "name", "file" ]
    if what == "network":
       columns = [ "name" ]
    if what == "mgmtclass":
        columns = [ "name" ]
    if what == "package":
        columns = [ "name", "installer" ]
    if what == "file":
        columns = [ "name" ]

    # render the list
    t = get_template('generic_list.tmpl')
    html = t.render(RequestContext(request,{
        'what'           : what,
        'columns'        : __format_columns(columns,sort_field),
        'items'          : __format_items(pageditems["items"],columns),
        'pageinfo'       : pageditems["pageinfo"],
        'filters'        : filters,
        'version'        : remote.extended_version(request.session['token'])['version'],
        'username'       : username,
        'limit'          : limit,
        'batchactions'   : batchactions,
    }))
    return HttpResponse(html)

@require_POST
@csrf_protect
def modify_list(request, what, pref, value=None):
    """
    This function is used in the generic list view
    to modify the page/column sort/number of items
    shown per page, and also modify the filters.

    This function modifies the session object to
    store these preferences persistently.
    """
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/modifylist/%s/%s" % (what,pref,str(value)))


    # what preference are we tweaking?

    if pref == "sort":

        # FIXME: this isn't exposed in the UI.

        # sorting list on columns
        old_sort = request.session.get("%s_sort_field" % what,"name")
        if old_sort.startswith("!"):
            old_sort = old_sort[1:]
            old_revsort = True
        else:
            old_revsort = False
        # User clicked on the column already sorted on,
        # so reverse the sorting list
        if old_sort == value and not old_revsort:
            value = "!" + value
        request.session["%s_sort_field" % what] = value
        request.session["%s_page" % what] = 1

    elif pref == "limit":
        # number of items to show per page
        request.session["%s_limit" % what] = int(value)
        request.session["%s_page" % what] = 1

    elif pref == "page":
        # what page are we currently on
        request.session["%s_page" % what] = int(value)

    elif pref in ("addfilter","removefilter"):
        # filters limit what we show in the lists
        # they are stored in json format for marshalling
        filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))
        if pref == "addfilter":
            (field_name, field_value) = value.split(":", 1)
            # add this filter
            filters[field_name] = field_value
        else:
            # remove this filter, if it exists
            if filters.has_key(value):
                del filters[value]
        # save session variable
        request.session["%s_filters" % what] = simplejson.dumps(filters)
        # since we changed what is viewed, reset the page
        request.session["%s_page" % what] = 1

    else:
        return error_page(request, "Invalid preference change request")

    # redirect to the list page
    return HttpResponseRedirect("/cobbler_web/%s/list" % what)

# ======================================================================

@require_POST
@csrf_protect
def generic_rename(request, what, obj_name=None, obj_newname=None):

   """
   Renames an object.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/rename/%s/%s" % (what,obj_name,obj_newname))

   if obj_name == None:
      return error_page(request,"You must specify a %s to rename" % what)
   if not remote.has_item(what,obj_name):
      return error_page(request,"Unknown %s specified" % what)
   elif not remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name):
      return error_page(request,"You do not have permission to rename this %s" % what)
   else:
      obj_id = remote.get_item_handle(what, obj_name, request.session['token'])
      remote.rename_item(what, obj_id, obj_newname, request.session['token'])
      return HttpResponseRedirect("/cobbler_web/%s/list" % what)

# ======================================================================

@require_POST
@csrf_protect
def generic_copy(request, what, obj_name=None, obj_newname=None):
   """
   Copies an object.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/copy/%s/%s" % (what,obj_name,obj_newname))
   # FIXME: shares all but one line with rename, merge it.
   if obj_name == None:
      return error_page(request,"You must specify a %s to rename" % what)
   if not remote.has_item(what,obj_name):
      return error_page(request,"Unknown %s specified" % what)
   elif not remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name):
      return error_page(request,"You do not have permission to copy this %s" % what)
   else:
      obj_id = remote.get_item_handle(what, obj_name, request.session['token'])
      remote.copy_item(what, obj_id, obj_newname, request.session['token'])
      return HttpResponseRedirect("/cobbler_web/%s/list" % what)

# ======================================================================

@require_POST
@csrf_protect
def generic_delete(request, what, obj_name=None):
   """
   Deletes an object.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/delete/%s" % (what,obj_name))
   # FIXME: consolidate code with above functions.
   if obj_name == None:
      return error_page(request,"You must specify a %s to delete" % what)
   if not remote.has_item(what,obj_name):
      return error_page(request,"Unknown %s specified" % what)
   elif not remote.check_access_no_fail(request.session['token'], "remove_%s" % what, obj_name):
      return error_page(request,"You do not have permission to delete this %s" % what)
   else:
      remote.remove_item(what, obj_name, request.session['token'])
      return HttpResponseRedirect("/cobbler_web/%s/list" % what)


# ======================================================================

@require_POST
@csrf_protect
def generic_domulti(request, what, multi_mode=None, multi_arg=None):

    """
    Process operations like profile reassignment, netboot toggling, and deletion
    which occur on all items that are checked on the list page.
    """
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/multi/%s/%s" % (what,multi_mode,multi_arg))

    # FIXME: cleanup
    # FIXME: COMMENTS!!!11111???

    names = request.POST.get('names', '').strip().split()
    if names == "":
        return error_page(request, "Need to select some systems first")

    if multi_mode == "delete":
         for obj_name in names:
            remote.remove_item(what,obj_name, request.session['token'])
    elif what == "system" and multi_mode == "netboot":
        netboot_enabled = multi_arg # values: enable or disable
        if netboot_enabled is None:
            return error_page(request,"Cannot modify systems without specifying netboot_enabled")
        if netboot_enabled == "enable":
            netboot_enabled = True
        elif netboot_enabled == "disable":
            netboot_enabled = False
        else:
            return error_page(request,"Invalid netboot option, expect enable or disable")
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, request.session['token'])
            remote.modify_system(obj_id, "netboot_enabled", netboot_enabled, request.session['token'])
            remote.save_system(obj_id, request.session['token'], "edit")
    elif what == "system" and multi_mode == "profile":
        profile = multi_arg
        if profile is None:
            return error_page(request,"Cannot modify systems without specifying profile")
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, request.session['token'])
            remote.modify_system(obj_id, "profile", profile, request.session['token'])
            remote.save_system(obj_id, request.session['token'], "edit")
    elif what == "system" and multi_mode == "power":
        # FIXME: power should not loop, but send the list of all systems
        # in one set.
        power = multi_arg
        if power is None:
            return error_page(request,"Cannot modify systems without specifying power option")
        options = { "systems" : names, "power" : power }
        remote.background_power_system(options, request.session['token'])
    elif what == "system" and multi_mode == "buildiso":
        options = { "systems" : names, "profiles" : [] }
        remote.background_buildiso(options, request.session['token'])
    elif what == "profile" and multi_mode == "buildiso":
        options = { "profiles" : names, "systems" : [] }
        remote.background_buildiso(options, request.session['token'])
    elif what == "distro" and multi_mode == "buildiso":
        if len(names) > 1:
            return error_page(request,"You can only select one distro at a time to build an ISO for")
        options = { "standalone" : True, "distro": str(names[0]) }
        remote.background_buildiso(options, request.session['token'])
    elif what == "repo" and multi_mode == "reposync":
        options = { "repos" : names, "tries" : 3 }
        remote.background_reposync(options,request.session['token'])
    else:
        return error_page(request,"Unknown batch operation on %ss: %s" % (what,str(multi_mode)))

    # FIXME: "operation complete" would make a lot more sense here than a redirect
    return HttpResponseRedirect("/cobbler_web/%s/list"%what)

# ======================================================================

def import_prompt(request):
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/import/prompt")
   t = get_template('import.tmpl')
   html = t.render(RequestContext(request,{
       'version'  : remote.extended_version(request.session['token'])['version'],
       'username' : username,
   }))
   return HttpResponse(html)

# ======================================================================

def check(request):
   """
   Shows a page with the results of 'cobbler check'
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/check")
   results = remote.check(request.session['token'])
   t = get_template('check.tmpl')
   html = t.render(RequestContext(request,{
       'version': remote.extended_version(request.session['token'])['version'],
       'username' : username,
       'results'  : results
   }))
   return HttpResponse(html)

# ======================================================================

@require_POST
@csrf_protect
def buildiso(request):
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/buildiso")
    remote.background_buildiso({},request.session['token'])
    return HttpResponseRedirect('/cobbler_web/task_created')

# ======================================================================

@require_POST
@csrf_protect
def import_run(request):
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/import/prompt")
    options = {
        "name"  : request.POST.get("name",""),
        "path"  : request.POST.get("path",""),
        "breed" : request.POST.get("breed",""),
        "arch"  : request.POST.get("arch","")
        }
    remote.background_import(options,request.session['token'])
    return HttpResponseRedirect('/cobbler_web/task_created')

# ======================================================================

def ksfile_list(request, page=None):
   """
   List all kickstart templates and link to their edit pages.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/ksfile/list")
   ksfiles = remote.get_kickstart_templates(request.session['token'])

   ksfile_list = []
   for ksfile in ksfiles:
      if ksfile.startswith("/var/lib/cobbler/kickstarts") or ksfile.startswith("/etc/cobbler"):
         ksfile_list.append((ksfile,ksfile.replace('/var/lib/cobbler/kickstarts/',''),'editable'))
      elif ksfile.startswith("http://") or ksfile.startswith("ftp://"):
         ksfile_list.append((ksfile,ksfile,'','viewable'))
      else:
         ksfile_list.append((ksfile,ksfile,None))

   t = get_template('ksfile_list.tmpl')
   html = t.render(RequestContext(request,{
       'what':'ksfile',
       'ksfiles': ksfile_list,
       'version': remote.extended_version(request.session['token'])['version'],
       'username': username,
       'item_count': len(ksfile_list[0]),
   }))
   return HttpResponse(html)

# ======================================================================

@csrf_protect
def ksfile_edit(request, ksfile_name=None, editmode='edit'):
   """
   This is the page where a kickstart file is edited.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/ksfile/edit/file:%s" % ksfile_name)
   if editmode == 'edit':
      editable = False
   else:
      editable = True
   deleteable = False
   ksdata = ""
   if not ksfile_name is None:
      editable = remote.check_access_no_fail(request.session['token'], "modify_kickstart", ksfile_name)
      deleteable = not remote.is_kickstart_in_use(ksfile_name, request.session['token'])
      ksdata = remote.read_or_write_kickstart_template(ksfile_name, True, "", request.session['token'])

   t = get_template('ksfile_edit.tmpl')
   html = t.render(RequestContext(request,{
       'ksfile_name' : ksfile_name,
       'deleteable'  : deleteable,
       'ksdata'      : ksdata,
       'editable'    : editable,
       'editmode'    : editmode,
       'version'     : remote.extended_version(request.session['token'])['version'],
       'username'    : username
   }))
   return HttpResponse(html)

# ======================================================================

@require_POST
@csrf_protect
def ksfile_save(request):
   """
   This page processes and saves edits to a kickstart file.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/ksfile/list")
   # FIXME: error checking

   editmode = request.POST.get('editmode', 'edit')
   ksfile_name = request.POST.get('ksfile_name', None)
   ksdata = request.POST.get('ksdata', "").replace('\r\n','\n')

   if ksfile_name == None:
      return HttpResponse("NO KSFILE NAME SPECIFIED")
   if editmode != 'edit':
      ksfile_name = "/var/lib/cobbler/kickstarts/" + ksfile_name

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.read_or_write_kickstart_template(ksfile_name, False, -1, request.session['token'])
      return HttpResponseRedirect('/cobbler_web/ksfile/list')
   else:
      remote.read_or_write_kickstart_template(ksfile_name,False,ksdata,request.session['token'])
      return HttpResponseRedirect('/cobbler_web/ksfile/edit/file:%s' % ksfile_name)

# ======================================================================

def snippet_list(request, page=None):
   """
   This page lists all available snippets and has links to edit them.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/snippet/list")
   snippets = remote.get_snippets(request.session['token'])

   snippet_list = []
   for snippet in snippets:
      if snippet.startswith("/var/lib/cobbler/snippets"):
         snippet_list.append((snippet,snippet.replace("/var/lib/cobbler/snippets/",""),'editable'))
      else:
         snippet_list.append((snippet,snippet,None))

   t = get_template('snippet_list.tmpl')
   html = t.render(RequestContext(request,{
       'what'     : 'snippet',
       'snippets' : snippet_list,
       'version'  : remote.extended_version(request.session['token'])['version'],
       'username' : username
   }))
   return HttpResponse(html)

# ======================================================================

@csrf_protect
def snippet_edit(request, snippet_name=None, editmode='edit'):
   """
   This page edits a specific snippet.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/edit/file:%s" % snippet_name)
   if editmode == 'edit':
      editable = False
   else:
      editable = True
   deleteable = False
   snippetdata = ""
   if not snippet_name is None:
      editable = remote.check_access_no_fail(request.session['token'], "modify_snippet", snippet_name)
      deleteable = True
      snippetdata = remote.read_or_write_snippet(snippet_name, True, "", request.session['token'])

   t = get_template('snippet_edit.tmpl')
   html = t.render(RequestContext(request,{
       'snippet_name' : snippet_name,
       'deleteable'   : deleteable,
       'snippetdata'  : snippetdata,
       'editable'     : editable,
       'editmode'     : editmode,
       'version'      : remote.extended_version(request.session['token'])['version'],
       'username'     : username
   }))
   return HttpResponse(html)

# ======================================================================

@require_POST
@csrf_protect
def snippet_save(request):
   """
   This snippet saves a snippet once edited.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/snippet/list")
   # FIXME: error checking

   editmode = request.POST.get('editmode', 'edit')
   snippet_name = request.POST.get('snippet_name', None)
   snippetdata = request.POST.get('snippetdata', "").replace('\r\n','\n')

   if snippet_name == None:
      return HttpResponse("NO SNIPPET NAME SPECIFIED")
   if editmode != 'edit':
      if snippet_name.find("/var/lib/cobbler/snippets/") != 0:
          snippet_name = "/var/lib/cobbler/snippets/" + snippet_name

   delete1   = request.POST.get('delete1', None)
   delete2   = request.POST.get('delete2', None)

   if delete1 and delete2:
      remote.read_or_write_snippet(snippet_name, False, -1, request.session['token'])
      return HttpResponseRedirect('/cobbler_web/snippet/list')
   else:
      remote.read_or_write_snippet(snippet_name,False,snippetdata,request.session['token'])
      return HttpResponseRedirect('/cobbler_web/snippet/edit/file:%s' % snippet_name)

# ======================================================================

def setting_list(request):
    """
    This page presents a list of all the settings to the user.  They are not editable.
    """
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/setting/list")
    settings = remote.get_settings()
    skeys = settings.keys()
    skeys.sort()

    results = []
    for k in skeys:
        results.append([k,settings[k]])

    t = get_template('settings.tmpl')
    html = t.render(RequestContext(request,{
         'settings' : results,
         'version'  : remote.extended_version(request.session['token'])['version'],
         'username' : username,
    }))
    return HttpResponse(html)

@csrf_protect
def setting_edit(request, setting_name=None):
    if not setting_name:
        return HttpResponseRedirect('/cobbler_web/setting/list')
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/setting/edit/%s" % setting_name)

    settings = remote.get_settings()
    if not settings.has_key(setting_name):
        return error_page(request,"Unknown setting: %s" % setting_name)

    cur_setting = {
        'name'  : setting_name,
        'value' : settings[setting_name],
    }

    fields = get_fields('setting', False, seed_item=cur_setting)
    sections = {}
    for field in fields:
        bmo = field_info.BLOCK_MAPPINGS_ORDER[field['block_section']]
        fkey = "%d_%s" % (bmo,field['block_section'])
        if not sections.has_key(fkey):
            sections[fkey] = {}
            sections[fkey]['name'] = field['block_section']
            sections[fkey]['fields'] = []
        sections[fkey]['fields'].append(field)

    t = get_template('generic_edit.tmpl')
    html = t.render(RequestContext(request,{
        'what'            : 'setting',
        #'fields'          : fields,
        'sections'        : sections,
        'subobject'       : False,
        'editmode'        : 'edit',
        'editable'        : True,
        'version'         : remote.extended_version(request.session['token'])['version'],
        'username'        : username,
        'name'            : setting_name,
    }))
    return HttpResponse(html)

@csrf_protect
def setting_save(request):
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/setting/list")

    # load request fields and see if they are valid
    setting_name = request.POST.get('name', "")
    setting_value = request.POST.get('value', None)

    if setting_name == "":
        return error_page(request,"The setting name was not specified")

    settings = remote.get_settings()
    if not settings.has_key(setting_name):
        return error_page(request,"Unknown setting: %s" % setting_name)

    if remote.modify_setting(setting_name, setting_value, request.session['token']):
        return error_page(request,"There was an error saving the setting")

    return HttpResponseRedirect("/cobbler_web/setting/list")

# ======================================================================

def events(request):
   """
   This page presents a list of all the events and links to the event log viewer.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/events")
   events = remote.get_events()

   events2 = []
   for id in events.keys():
      (ttime, name, state, read_by) = events[id]
      events2.append([id,time.asctime(time.localtime(ttime)),name,state])

   def sorter(a,b):
      return cmp(a[0],b[0])
   events2.sort(sorter)

   t = get_template('events.tmpl')
   html = t.render(RequestContext(request,{
       'results'  : events2,
       'version'  : remote.extended_version(request.session['token'])['version'],
       'username' : username
   }))
   return HttpResponse(html)

# ======================================================================

def eventlog(request, event=0):
   """
   Shows the log for a given event.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/eventlog/%s" % str(event))
   event_info = remote.get_events()
   if not event_info.has_key(event):
      return HttpResponse("event not found")

   data       = event_info[event]
   eventname  = data[0]
   eventtime  = data[1]
   eventstate = data[2]
   eventlog   = remote.get_event_log(event)

   t = get_template('eventlog.tmpl')
   vars = {
      'eventlog'   : eventlog,
      'eventname'  : eventname,
      'eventstate' : eventstate,
      'eventid'    : event,
      'eventtime'  : eventtime,
      'version'    : remote.extended_version(request.session['token'])['version'],
      'username'  : username
   }
   html = t.render(RequestContext(request,vars))
   return HttpResponse(html)

# ======================================================================

def random_mac(request, virttype="xenpv"):
   """
   Used in an ajax call to fill in a field with a mac address.
   """
   # FIXME: not exposed in UI currently
   if not test_user_authenticated(request): return login(request)
   random_mac = remote.get_random_mac(virttype, request.session['token'])
   return HttpResponse(random_mac)

# ======================================================================

@require_POST
@csrf_protect
def sync(request):
   """
   Runs 'cobbler sync' from the API when the user presses the sync button.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/sync")
   remote.background_sync({"verbose":"True"},request.session['token'])
   return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================

@require_POST
@csrf_protect
def reposync(request):
   """
   Syncs all repos that are configured to be synced.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/reposync")
   remote.background_reposync({ "names":"", "tries" : 3},request.session['token'])
   return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================

@require_POST
@csrf_protect
def hardlink(request):
   """
   Hardlinks files between repos and install trees to save space.
   """
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/hardlink")
   remote.background_hardlink({},request.session['token'])
   return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================

@require_POST
@csrf_protect
def replicate(request):
   """
   Replicate configuration from the central cobbler server, configured
   in /etc/cobbler/settings (note: this is uni-directional!)

   FIXME: this is disabled because we really need a web page to provide options for
   this command.

   """
   #settings = remote.get_settings()
   #options = settings # just load settings from file until we decide to ask user (later?)
   #remote.background_replicate(options, request.session['token'])
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/replicate")
   return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================

def __names_from_dicts(loh,optional=True):
   """
   Tiny helper function.
   Get the names out of an array of hashes that the remote interface returns.
   """
   results = []
   if optional:
      results.append("<<None>>")
   for x in loh:
      results.append(x["name"])
   results.sort()
   return results

# ======================================================================

@csrf_protect
def generic_edit(request, what=None, obj_name=None, editmode="new"):

   """
   Presents an editor page for any type of object.
   While this is generally standardized, systems are a little bit special.
   """
   target = ""
   if obj_name != None:
       target = "/%s" % obj_name
   if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/edit%s" % (what,target))

   obj = None

   child = False
   if what == "subprofile":
      what = "profile"
      child = True

   if not obj_name is None:
      editable = remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name)
      obj = remote.get_item(what, obj_name, False)
   else:
       editable = remote.check_access_no_fail(request.session['token'], "new_%s" % what, None)
       obj = None

   interfaces = {}
   if what == "system":
       if obj:
           interfaces = obj.get("interfaces",{})
       else:
           interfaces = {}

   fields = get_fields(what, child, obj)

   # populate some select boxes
   # FIXME: we really want to just populate with the names, right?
   if what == "profile":
      if (obj and obj["parent"] not in (None,"")) or child:
         __tweak_field(fields, "parent", "choices", __names_from_dicts(remote.get_profiles()))
      else:
         __tweak_field(fields, "distro", "choices", __names_from_dicts(remote.get_distros()))
      __tweak_field(fields, "repos", "choices",     __names_from_dicts(remote.get_repos()))
   elif what == "system":
      __tweak_field(fields, "profile", "choices",      __names_from_dicts(remote.get_profiles()))
      __tweak_field(fields, "image", "choices",        __names_from_dicts(remote.get_images(),optional=True))
   elif what == "mgmtclass":
        __tweak_field(fields, "packages", "choices", __names_from_dicts(remote.get_packages()))
        __tweak_field(fields, "files", "choices",    __names_from_dicts(remote.get_files()))

   if what in ("distro","profile","system"):
       __tweak_field(fields, "mgmt_classes", "choices", __names_from_dicts(remote.get_mgmtclasses(),optional=False))

   # if editing save the fields in the session for comparison later
   if editmode == "edit":
       request.session['%s_%s' % (what,obj_name)] = fields

   sections = {}
   for field in fields:
       bmo = field_info.BLOCK_MAPPINGS_ORDER[field['block_section']]
       fkey = "%d_%s" % (bmo,field['block_section'])
       if not sections.has_key(fkey):
           sections[fkey] = {}
           sections[fkey]['name'] = field['block_section']
           sections[fkey]['fields'] = []
       sections[fkey]['fields'].append(field)

   t = get_template('generic_edit.tmpl')
   inames = interfaces.keys()
   inames.sort()
   html = t.render(RequestContext(request,{
       'what'            : what, 
       #'fields'          : fields, 
       'sections'        : sections,
       'subobject'       : child,
       'editmode'        : editmode, 
       'editable'        : editable,
       'interfaces'      : interfaces,
       'interface_names' : inames,
       'interface_length': len(inames),
       'version'         : remote.extended_version(request.session['token'])['version'],
       'username'        : username,
       'name'            : obj_name
   }))

   return HttpResponse(html)

# ======================================================================

@require_POST
@csrf_protect
def generic_save(request,what):

    """
    Saves an object back using the cobbler API after clearing any 'generic_edit' page.
    """
    if not test_user_authenticated(request): return login(request, next="/cobbler_web/%s/list" % what)

    # load request fields and see if they are valid
    editmode  = request.POST.get('editmode', 'edit')
    obj_name  = request.POST.get('name', "")    
    subobject = request.POST.get('subobject', "False")  
  
    if subobject == "False":
       subobject = False
    else:
       subobject = True

    if obj_name == "":
        return error_page(request,"Required field name is missing")
              
    prev_fields = []
    if request.session.has_key("%s_%s" % (what,obj_name)) and editmode == "edit":
        prev_fields = request.session["%s_%s" % (what,obj_name)]

    # grab the remote object handle
    # for edits, fail in the object cannot be found to be edited
    # for new objects, fail if the object already exists
    if editmode == "edit":
        if not remote.has_item(what, obj_name):
            return error_page(request,"Failure trying to access item %s, it may have been deleted." % (obj_name))
        obj_id = remote.get_item_handle( what, obj_name, request.session['token'] )
    else:
        if remote.has_item(what, obj_name):
            return error_page(request,"Could not create a new item %s, it already exists." % (obj_name))
        obj_id = remote.new_item( what, request.session['token'] )

    # walk through our fields list saving things we know how to save
    fields = get_fields(what, subobject)

    for field in fields:

        if field['name'] == 'name' and editmode == 'edit':
            # do not attempt renames here
            continue
        elif field['name'].startswith("*"):
            # interface fields will be handled below
            continue
        else:
            # check and see if the value exists in the fields stored in the session
            prev_value = None
            for prev_field in prev_fields:
                if prev_field['name'] == field['name']:
                    prev_value = prev_field['value']
                    break

            value = request.POST.get(field['name'],None)
            # Checkboxes return the value of the field if checked, otherwise None
            # convert to True/False
            if field["html_element"] == "checkbox":
                if value==field['name']:
                    value=True
                else:
                    value=False

            # Multiselect fields are handled differently
            if field["html_element"] == "multiselect":
                values=request.POST.getlist(field['name'])
                value=[]
                if '<<inherit>>' in values:
                    value='<<inherit>>'
                else:
                    for single_value in values:
                        if single_value != "<<None>>":
                            value.insert(0,single_value)

            if value != None:
                if value == "<<None>>":
                    value = ""
                if value is not None and (not subobject or field['name'] != 'distro') and value != prev_value:
                    try:
                        remote.modify_item(what,obj_id,field['name'],value,request.session['token'])
                    except Exception, e:
                        return error_page(request, str(e))                

    # special handling for system interface fields
    # which are the only objects in cobbler that will ever work this way
    if what == "system":
        interface_field_list = []
        for field in fields:
            if field['name'].startswith("*"):
                field = field['name'].replace("*","")
                interface_field_list.append(field)
        interfaces = request.POST.get('interface_list', "").split(",")
        for interface in interfaces:
            if interface == "":
                continue
            ifdata = {}
            for item in interface_field_list:
                ifdata["%s-%s" % (item,interface)] = request.POST.get("%s-%s" % (item,interface), "")
            ifdata=utils.strip_none(ifdata)
            # FIXME: I think this button is missing.
            present  = request.POST.get("present-%s" % interface, "") 
            original = request.POST.get("original-%s" % interface, "") 
            try:
                if present == "0" and original == "1":
                    remote.modify_system(obj_id, 'delete_interface', interface, request.session['token'])
                elif present == "1":
                    remote.modify_system(obj_id, 'modify_interface', ifdata, request.session['token'])
            except Exception, e:
                return error_page(request, str(e))

    try:
        remote.save_item(what, obj_id, request.session['token'], editmode)
    except Exception, e:
        return error_page(request, str(e))

    return HttpResponseRedirect('/cobbler_web/%s/list' % what)


# ======================================================================
# Login/Logout views

def test_user_authenticated(request):
    global remote
    global username
    global url_cobbler_api

    if url_cobbler_api is None:
        url_cobbler_api = utils.local_get_cobbler_api_url()

    remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)

    # if we have a token, get the associated username from
    # the remote server via XMLRPC. We then compare that to 
    # the value stored in the session.  If everything matches up,
    # the user is considered successfully authenticated
    if request.session.has_key('token') and request.session['token'] != '':
        try:
            if remote.token_check(request.session['token']):
                token_user = remote.get_user_from_token(request.session['token'])
                if request.session.has_key('username') and request.session['username'] == token_user:
                    username = request.session['username']
                    return True
        except:
            # just let it fall through to the 'return False' below
            pass
    return False

@csrf_protect
def login(request, next=None):
    return render_to_response('login.tmpl', RequestContext(request,{'next':next}))

@require_POST
@csrf_protect
def do_login(request):
    global remote
    global username
    global url_cobbler_api

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    nextsite = request.POST.get('next',None)

    if url_cobbler_api is None:
        url_cobbler_api = utils.local_get_cobbler_api_url()

    remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)

    try:
        token = remote.login(username, password)
    except: 
        token = None

    if token:
        request.session['username'] = username
        request.session['token'] = token
        if nextsite:
           return HttpResponseRedirect(nextsite)
        else:
           return HttpResponseRedirect("/cobbler_web")
    else:
        return login(request,nextsite)

@require_POST
@csrf_protect
def do_logout(request):
    request.session['username'] = ""
    request.session['token'] = ""
    return HttpResponseRedirect("/cobbler_web")
