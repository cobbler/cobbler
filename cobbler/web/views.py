
from future import standard_library
standard_library.install_aliases()
from builtins import str
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

import simplejson
import time
import xmlrpc.client

import cobbler.items.distro as item_distro
import cobbler.items.file as item_file
import cobbler.items.image as item_image
import cobbler.items.mgmtclass as item_mgmtclass
import cobbler.items.package as item_package
import cobbler.items.profile as item_profile
import cobbler.items.repo as item_repo
import cobbler.items.system as item_system
import cobbler.settings as item_settings
import cobbler.utils as utils
from cobbler.web import field_ui_info

url_cobbler_api = None
remote = None
username = None

# ==================================================================================


def index(request):
    """
    This is the main greeting page for Cobbler web.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web", expired=True)

    html = render(request, 'index.tmpl', {
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
    })
    return HttpResponse(html)

# ========================================================================


def task_created(request):
    """
    Let's the user know what to expect for event updates.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/task_created", expired=True)

    html = render(request, "task_created.tmpl", {
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ========================================================================


def error_page(request, message):
    """
    This page is used to explain error messages to the user.
    """
    if not test_user_authenticated(request):
        return login(request, expired=True)

    # FIXME: test and make sure we use this rather than throwing lots of tracebacks for
    # field errors
    message = message.replace("<Fault 1: \"<class 'cobbler.cexceptions.CX'>:'", "Remote exception: ")
    message = message.replace("'\">", "")

    html = render(request, 'error_page.tmpl', {
        'version': remote.extended_version(request.session['token'])['version'],
        'message': message,
        'username': username
    })
    return HttpResponse(html)

# ==================================================================================


def _get_field_html_element(field_name):

    if field_name in field_ui_info.USES_SELECT:
        return "select"
    elif field_name in field_ui_info.USES_MULTI_SELECT:
        return "multiselect"
    elif field_name in field_ui_info.USES_RADIO:
        return "radio"
    elif field_name in field_ui_info.USES_CHECKBOX:
        return "checkbox"
    elif field_name in field_ui_info.USES_TEXTAREA:
        return "textarea"
    else:
        return "text"


def get_fields(what, is_subobject, seed_item=None):

    """
    Helper function.  Retrieves the field table from the Cobbler objects
    and formats it in a way to make it useful for Django templating.
    The field structure indicates what fields to display and what the default
    values are, etc.
    """

    if what == "distro":
        fields = item_distro.FIELDS
    if what == "profile":
        fields = item_profile.FIELDS
    if what == "system":
        fields = item_system.FIELDS
    if what == "repo":
        fields = item_repo.FIELDS
    if what == "image":
        fields = item_image.FIELDS
    if what == "mgmtclass":
        fields = item_mgmtclass.FIELDS
    if what == "package":
        fields = item_package.FIELDS
    if what == "file":
        fields = item_file.FIELDS
    if what == "setting":
        fields = item_settings.FIELDS

    settings = remote.get_settings()

    ui_fields = []
    for field in fields:

        ui_field = {
            "name": field[0],
            "dname": field[0],
            "value": "?",
            "caption": field[3],
            "editable": field[4],
            "tooltip": field[5],
            "choices": field[6],
            "css_class": "generic",
            "html_ui_fieldent": "generic",
        }

        if not ui_field["editable"]:
            continue

        name = field[0]
        if seed_item is not None:
            ui_field["value"] = seed_item[name]
        elif is_subobject:
            ui_field["value"] = field[2]
        else:
            ui_field["value"] = field[1]

        if ui_field["value"] is None:
            ui_field["value"] = ""

        # we'll process this for display but still need to present the original to some
        # template logic
        ui_field["value_raw"] = ui_field["value"]

        if isinstance(ui_field["value"], str) and ui_field["value"].startswith("SETTINGS:"):
            key = ui_field["value"].replace("SETTINGS:", "", 1)
            ui_field["value"] = settings[key]

        # flatten dicts of all types, they can only be edited as text
        # as we have no HTML dict widget (yet)
        if isinstance(ui_field["value"], dict):
            if ui_field["name"] == "mgmt_parameters":
                # Render dictionary as YAML for Management Parameters field
                tokens = []
                for (x, y) in list(ui_field["value"].items()):
                    if y is not None:
                        tokens.append("%s: %s" % (x, y))
                    else:
                        tokens.append("%s: " % x)
                ui_field["value"] = "{ %s }" % ", ".join(tokens)
            else:
                tokens = []
                for (x, y) in list(ui_field["value"].items()):
                    if isinstance(y, str) and y.strip() != "~":
                        y = y.replace(" ", "\\ ")
                        tokens.append("%s=%s" % (x, y))
                    elif isinstance(y, list):
                        for item in y:
                            item = item.replace(" ", "\\ ")
                            tokens.append("%s=%s" % (x, item))
                    elif y is not None:
                        tokens.append("%s" % x)
                ui_field["value"] = " ".join(tokens)

        name = field[0]
        ui_field["html_element"] = _get_field_html_element(name)

        # flatten lists for those that aren't using select boxes
        if isinstance(ui_field["value"], list):
            if ui_field["html_element"] != "select":
                ui_field["value"] = " ".join(ui_field["value"])

        ui_fields.append(ui_field)

    return ui_fields


def get_network_interface_fields():
    """
    Create network interface fields UI metadata based on network interface
    fields metadata

    @return list network interface fields UI metadata
    """

    fields = item_system.NETWORK_INTERFACE_FIELDS

    fields_ui = []
    for field in fields:

        field_ui = {
            "name": field[0],
            "dname": field[0],
            "value": "?",
            "caption": field[3],
            "editable": field[4],
            "tooltip": field[5],
            "choices": field[6],
            "css_class": "generic",
            "html_element": "generic",
        }

        if not field_ui["editable"]:
            continue

        # system's network interfaces are loaded later by javascript,
        # initial value on web UI is always empty string
        field_ui["value"] = ""

        # we'll process this for display but still need to present the original
        # to some template logic
        field_ui["value_raw"] = field_ui["value"]

        name = field[0]
        field_ui["html_element"] = _get_field_html_element(name)

        fields_ui.append(field_ui)

    return fields_ui


def _create_sections_metadata(what, sections_data, fields):

    sections = {}
    section_index = 0
    for section_data in sections_data:
        for section_name, section_fields in list(section_data.items()):
            skey = "%d_%s" % (section_index, section_name)
            sections[skey] = {}
            sections[skey]['name'] = section_name
            sections[skey]['fields'] = []

            for section_field in section_fields:
                found = False
                for field in fields:
                    if field["name"] == section_field:
                        sections[skey]['fields'].append(field)
                        found = True
                        break
                if not found:
                    raise Exception("%s field %s referenced in UI section definition does not exist in UI fields definition" % (what, section_field))

            section_index += 1

    return sections

# ==================================================================================


def __tweak_field(fields, field_name, attribute, value):
    """
    Helper function to insert extra data into the field list.
    """
    # FIXME: eliminate this function.
    for x in fields:
        if x["name"] == field_name:
            x[attribute] = value

# ==================================================================================


def __format_columns(column_names, sort_field):
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
        dataset.append([fieldname, fieldorder])
    return dataset


# ==================================================================================


def __format_items(items, column_names):
    """
    Format items retrieved from XMLRPC for rendering by the generic_edit template
    """
    dataset = []
    for item_dict in items:
        row = []
        for fieldname in column_names:
            if fieldname == "name":
                html_element = "name"
            elif fieldname in ["system", "repo", "distro", "profile", "image", "mgmtclass", "package", "file"]:
                html_element = "editlink"
            elif fieldname in field_ui_info.USES_CHECKBOX:
                html_element = "checkbox"
            else:
                html_element = "text"
            row.append([fieldname, item_dict[fieldname], html_element])
        dataset.append(row)
    return dataset

# ==================================================================================


def genlist(request, what, page=None):
    """
    Lists all object types, complete with links to actions
    on those objects.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/list" % what, expired=True)

    # get details from the session
    if page is None:
        page = int(request.session.get("%s_page" % what, 1))
    limit = int(request.session.get("%s_limit" % what, 50))
    sort_field = request.session.get("%s_sort_field" % what, "name")
    filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))
    pageditems = remote.find_items_paged(what, utils.strip_none(filters), sort_field, page, limit)

    # what columns to show for each page?
    # we also setup the batch actions here since they're dependent
    # on what we're looking at

    profiles = []

    # everythng gets batch delete
    batchactions = [
        ["Delete", "delete", "delete"],
    ]

    if what == "distro":
        columns = ["name"]
        batchactions += [
            ["Build ISO", "buildiso", "enable"],
        ]
    if what == "profile":
        columns = ["name", "distro"]
        batchactions += [
            ["Build ISO", "buildiso", "enable"],
        ]
    if what == "system":
        # FIXME: also list network, once working
        columns = ["name", "profile", "status", "netboot_enabled"]
        profiles = sorted(remote.get_profiles(), key=lambda x: x['name'])
        batchactions += [
            ["Power on", "power", "on"],
            ["Power off", "power", "off"],
            ["Reboot", "power", "reboot"],
            ["Change profile", "profile", ""],
            ["Netboot enable", "netboot", "enable"],
            ["Netboot disable", "netboot", "disable"],
            ["Build ISO", "buildiso", "enable"],
        ]
    if what == "repo":
        columns = ["name", "mirror"]
        batchactions += [
            ["Reposync", "reposync", "go"],
        ]
    if what == "image":
        columns = ["name", "file"]
    if what == "network":
        columns = ["name"]
    if what == "mgmtclass":
        columns = ["name"]
    if what == "package":
        columns = ["name", "installer"]
    if what == "file":
        columns = ["name"]

    # render the list
    html = render(request, 'generic_list.tmpl', {
        'what': what,
        'columns': __format_columns(columns, sort_field),
        'items': __format_items(pageditems["items"], columns),
        'pageinfo': pageditems["pageinfo"],
        'filters': filters,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
        'limit': limit,
        'batchactions': batchactions,
        'profiles': profiles,
    })
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
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/modifylist/%s/%s" % (what, pref, str(value)), expired=True)

    # what preference are we tweaking?

    if pref == "sort":

        # FIXME: this isn't exposed in the UI.

        # sorting list on columns
        old_sort = request.session.get("%s_sort_field" % what, "name")
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

    elif pref in ("addfilter", "removefilter"):
        # filters limit what we show in the lists
        # they are stored in json format for marshalling
        filters = simplejson.loads(request.session.get("%s_filters" % what, "{}"))
        if pref == "addfilter":
            (field_name, field_value) = value.split(":", 1)
            # add this filter
            filters[field_name] = field_value
        else:
            # remove this filter, if it exists
            if value in filters:
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
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/rename/%s/%s" % (what, obj_name, obj_newname), expired=True)

    if obj_name is None:
        return error_page(request, "You must specify a %s to rename" % what)
    if not remote.has_item(what, obj_name):
        return error_page(request, "Unknown %s specified" % what)
    elif not remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name):
        return error_page(request, "You do not have permission to rename this %s" % what)
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
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/copy/%s/%s" % (what, obj_name, obj_newname), expired=True)
    # FIXME: shares all but one line with rename, merge it.
    if obj_name is None:
        return error_page(request, "You must specify a %s to rename" % what)
    if not remote.has_item(what, obj_name):
        return error_page(request, "Unknown %s specified" % what)
    elif not remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name):
        return error_page(request, "You do not have permission to copy this %s" % what)
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
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/delete/%s" % (what, obj_name), expired=True)
    # FIXME: consolidate code with above functions.
    if obj_name is None:
        return error_page(request, "You must specify a %s to delete" % what)
    if not remote.has_item(what, obj_name):
        return error_page(request, "Unknown %s specified" % what)
    elif not remote.check_access_no_fail(request.session['token'], "remove_%s" % what, obj_name):
        return error_page(request, "You do not have permission to delete this %s" % what)
    else:
        # check whether object is to be deleted recursively
        recursive = simplejson.loads(request.POST.get("recursive", "false"))
        try:
            remote.xapi_object_edit(what, obj_name, "remove", {'name': obj_name, 'recursive': recursive}, request.session['token'])
        except Exception as e:
            return error_page(request, str(e))
        return HttpResponseRedirect("/cobbler_web/%s/list" % what)


# ======================================================================


@require_POST
@csrf_protect
def generic_domulti(request, what, multi_mode=None, multi_arg=None):
    """
    Process operations like profile reassignment, netboot toggling, and deletion
    which occur on all items that are checked on the list page.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/multi/%s/%s" % (what, multi_mode, multi_arg), expired=True)

    names = request.POST.get('names', '').strip().split()
    if names == "":
        return error_page(request, "Need to select some '%s' objects first" % what)

    if multi_mode == "delete":
        # check whether the objects are to be deleted recursively
        recursive = simplejson.loads(request.POST.get("recursive_batch", "false"))
        for obj_name in names:
            try:
                remote.xapi_object_edit(what, obj_name, "remove", {'name': obj_name, 'recursive': recursive}, request.session['token'])
            except Exception as e:
                return error_page(request, str(e))

    elif what == "system" and multi_mode == "netboot":
        netboot_enabled = multi_arg  # values: enable or disable
        if netboot_enabled is None:
            return error_page(request, "Cannot modify systems without specifying netboot_enabled")
        if netboot_enabled == "enable":
            netboot_enabled = True
        elif netboot_enabled == "disable":
            netboot_enabled = False
        else:
            return error_page(request, "Invalid netboot option, expect enable or disable")
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, request.session['token'])
            remote.modify_system(obj_id, "netboot_enabled", netboot_enabled, request.session['token'])
            remote.save_system(obj_id, request.session['token'], "edit")

    elif what == "system" and multi_mode == "profile":
        profile = multi_arg
        if profile is None:
            return error_page(request, "Cannot modify systems without specifying profile")
        for obj_name in names:
            obj_id = remote.get_system_handle(obj_name, request.session['token'])
            remote.modify_system(obj_id, "profile", profile, request.session['token'])
            remote.save_system(obj_id, request.session['token'], "edit")

    elif what == "system" and multi_mode == "power":
        power = multi_arg
        if power is None:
            return error_page(request, "Cannot modify systems without specifying power option")
        options = {"systems": names, "power": power}
        remote.background_power_system(options, request.session['token'])

    elif what == "system" and multi_mode == "buildiso":
        options = {"systems": names, "profiles": []}
        remote.background_buildiso(options, request.session['token'])

    elif what == "profile" and multi_mode == "buildiso":
        options = {"profiles": names, "systems": []}
        remote.background_buildiso(options, request.session['token'])

    elif what == "distro" and multi_mode == "buildiso":
        if len(names) > 1:
            return error_page(request, "You can only select one distro at a time to build an ISO for")
        options = {"standalone": True, "distro": str(names[0])}
        remote.background_buildiso(options, request.session['token'])

    elif what == "repo" and multi_mode == "reposync":
        options = {"repos": names, "tries": 3}
        remote.background_reposync(options, request.session['token'])

    else:
        return error_page(request, "Unknown batch operation on %ss: %s" % (what, str(multi_mode)))

    # FIXME: "operation complete" would make a lot more sense here than a redirect
    return HttpResponseRedirect("/cobbler_web/%s/list" % what)

# ======================================================================


def import_prompt(request):
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/import/prompt", expired=True)

    html = render(request, 'import.tmpl', {
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
    })
    return HttpResponse(html)

# ======================================================================


def check(request):
    """
    Shows a page with the results of 'cobbler check'
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/check", expired=True)

    results = remote.check(request.session['token'])

    html = render(request, 'check.tmpl', {
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
        'results': results
    })
    return HttpResponse(html)

# ======================================================================


@require_POST
@csrf_protect
def buildiso(request):
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/buildiso", expired=True)
    remote.background_buildiso({}, request.session['token'])
    return HttpResponseRedirect('/cobbler_web/task_created')

# ======================================================================


@require_POST
@csrf_protect
def import_run(request):
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/import/prompt", expired=True)
    options = {
        "name": request.POST.get("name", ""),
        "path": request.POST.get("path", ""),
        "breed": request.POST.get("breed", ""),
        "arch": request.POST.get("arch", "")
    }
    remote.background_import(options, request.session['token'])
    return HttpResponseRedirect('/cobbler_web/task_created')

# ======================================================================


def aifile_list(request, page=None):
    """
    List all automatic OS installation templates and link to their edit pages.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/aifile/list", expired=True)

    aifiles = remote.get_autoinstall_templates(request.session['token'])

    aifile_list = []
    for aifile in aifiles:
        aifile_list.append((aifile, 'editable'))

    html = render(request, 'aifile_list.tmpl', {
        'what': 'aifile',
        'ai_files': aifile_list,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
        'item_count': len(aifile_list[0]),
    })
    return HttpResponse(html)

# ======================================================================


@csrf_protect
def aifile_edit(request, aifile_name=None, editmode='edit'):
    """
    This is the page where an automatic OS installation file is edited.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/aifile/edit/file:%s" % aifile_name, expired=True)
    if editmode == 'edit':
        editable = False
    else:
        editable = True
    deleteable = False
    aidata = ""
    if aifile_name is not None:
        editable = remote.check_access_no_fail(request.session['token'], "modify_autoinst", aifile_name)
        deleteable = not remote.is_autoinstall_in_use(aifile_name, request.session['token'])
        aidata = remote.read_autoinstall_template(aifile_name, request.session['token'])

    html = render(request, 'aifile_edit.tmpl', {
        'aifile_name': aifile_name,
        'deleteable': deleteable,
        'aidata': aidata,
        'editable': editable,
        'editmode': editmode,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ======================================================================


@require_POST
@csrf_protect
def aifile_save(request):
    """
    This page processes and saves edits to an automatic OS installation file.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/aifile/list", expired=True)
    # FIXME: error checking

    aifile_name = request.POST.get('aifile_name', None)
    aidata = request.POST.get('aidata', "").replace('\r\n', '\n')

    if aifile_name is None:
        return HttpResponse("NO AUTOMATIC INSTALLATION FILE NAME SPECIFIED")

    delete1 = request.POST.get('delete1', None)
    delete2 = request.POST.get('delete2', None)

    if delete1 and delete2:
        remote.remove_autoinstall_template(aifile_name, request.session['token'])
        return HttpResponseRedirect('/cobbler_web/aifile/list')
    else:
        remote.write_autoinstall_template(aifile_name, aidata, request.session['token'])
        return HttpResponseRedirect('/cobbler_web/aifile/list')

# ======================================================================


def snippet_list(request, page=None):
    """
    This page lists all available snippets and has links to edit them.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/snippet/list", expired=True)

    snippets = remote.get_autoinstall_snippets(request.session['token'])
    snippet_list = []
    for snippet in snippets:
        snippet_list.append((snippet, 'editable'))

    html = render(request, 'snippet_list.tmpl', {
        'what': 'snippet',
        'snippets': snippet_list,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ======================================================================


@csrf_protect
def snippet_edit(request, snippet_name=None, editmode='edit'):
    """
    This page edits a specific snippet.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/edit/file:%s" % snippet_name, expired=True)
    if editmode == 'edit':
        editable = False
    else:
        editable = True
    deleteable = False
    snippetdata = ""
    if snippet_name is not None:
        editable = remote.check_access_no_fail(request.session['token'], "modify_snippet", snippet_name)
        deleteable = True
        snippetdata = remote.read_autoinstall_snippet(snippet_name, request.session['token'])

    html = render(request, 'snippet_edit.tmpl', {
        'snippet_name': snippet_name,
        'deleteable': deleteable,
        'snippetdata': snippetdata,
        'editable': editable,
        'editmode': editmode,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ======================================================================


@require_POST
@csrf_protect
def snippet_save(request):
    """
    This snippet saves a snippet once edited.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/snippet/list", expired=True)
    # FIXME: error checking

    editmode = request.POST.get('editmode', 'edit')
    snippet_name = request.POST.get('snippet_name', None)
    snippetdata = request.POST.get('snippetdata', "").replace('\r\n', '\n')

    if snippet_name is None:
        return HttpResponse("NO SNIPPET NAME SPECIFIED")

    if editmode != 'edit':
        if snippet_name.find("/var/lib/cobbler/snippets/") != 0:
            snippet_name = "/var/lib/cobbler/snippets/" + snippet_name

    delete1 = request.POST.get('delete1', None)
    delete2 = request.POST.get('delete2', None)

    if delete1 and delete2:
        remote.remove_autoinstall_snippet(snippet_name, request.session['token'])
        return HttpResponseRedirect('/cobbler_web/snippet/list')
    else:
        remote.write_autoinstall_snippet(snippet_name, snippetdata, request.session['token'])
        return HttpResponseRedirect('/cobbler_web/snippet/list')

# ======================================================================


def setting_list(request):
    """
    This page presents a list of all the settings to the user.  They are not editable.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/setting/list", expired=True)
    settings = remote.get_settings()
    skeys = list(settings.keys())
    skeys.sort()

    results = []
    for k in skeys:
        results.append([k, settings[k]])

    html = render(request, 'settings.tmpl', {
        'settings': results,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
    })
    return HttpResponse(html)


@csrf_protect
def setting_edit(request, setting_name=None):
    if not setting_name:
        return HttpResponseRedirect('/cobbler_web/setting/list')
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/setting/edit/%s" % setting_name, expired=True)

    settings = remote.get_settings()
    if setting_name not in settings:
        return error_page(request, "Unknown setting: %s" % setting_name)

    cur_setting = {
        'name': setting_name,
        'value': settings[setting_name],
    }

    fields = get_fields('setting', False, seed_item=cur_setting)

    # build UI tabs metadata
    sections_data = field_ui_info.SETTING_UI_FIELDS_MAPPING
    sections = _create_sections_metadata('setting', sections_data, fields)

    html = render(request, 'generic_edit.tmpl', {
        'what': 'setting',
        'sections': sections,
        'subobject': False,
        'editmode': 'edit',
        'editable': True,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
        'name': setting_name,
    })
    return HttpResponse(html)


@csrf_protect
def setting_save(request):
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/setting/list", expired=True)

    # load request fields and see if they are valid
    setting_name = request.POST.get('name', "")
    setting_value = request.POST.get('value', None)

    if setting_name == "":
        return error_page(request, "The setting name was not specified")

    settings = remote.get_settings()
    if setting_name not in settings:
        return error_page(request, "Unknown setting: %s" % setting_name)

    if remote.modify_setting(setting_name, setting_value, request.session['token']):
        return error_page(request, "There was an error saving the setting")

    return HttpResponseRedirect("/cobbler_web/setting/list")

# ======================================================================


def events(request):
    """
    This page presents a list of all the events and links to the event log viewer.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/events", expired=True)
    events = remote.get_events()

    events2 = []
    for id in list(events.keys()):
        (ttime, name, state, read_by) = events[id]
        events2.append([id, time.asctime(time.localtime(ttime)), name, state])

    events2 = sorted(events2)

    html = render(request, 'events.tmpl', {
        'results': events2,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ======================================================================


def eventlog(request, event=0):
    """
    Shows the log for a given event.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/eventlog/%s" % str(event), expired=True)
    event_info = remote.get_events()
    if event not in event_info:
        return HttpResponse("event not found")

    data = event_info[event]
    eventname = data[0]
    eventtime = data[1]
    eventstate = data[2]
    eventlog = remote.get_event_log(event)

    html = render(request, 'eventlog.tmpl', {
        'eventlog': eventlog,
        'eventname': eventname,
        'eventstate': eventstate,
        'eventid': event,
        'eventtime': eventtime,
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username
    })
    return HttpResponse(html)

# ======================================================================


def random_mac(request, virttype="xenpv"):
    """
    Used in an ajax call to fill in a field with a mac address.
    """
    # FIXME: not exposed in UI currently
    if not test_user_authenticated(request):
        return login(request, expired=True)
    random_mac = remote.get_random_mac(virttype, request.session['token'])
    return HttpResponse(random_mac)

# ======================================================================


@require_POST
@csrf_protect
def sync(request):
    """
    Runs 'cobbler sync' from the API when the user presses the sync button.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/sync", expired=True)
    remote.background_sync({"verbose": "True"}, request.session['token'])
    return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================


@require_POST
@csrf_protect
def reposync(request):
    """
    Syncs all repos that are configured to be synced.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/reposync", expired=True)
    remote.background_reposync({"names": "", "tries": 3}, request.session['token'])
    return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================


@require_POST
@csrf_protect
def hardlink(request):
    """
    Hardlinks files between repos and install trees to save space.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/hardlink", expired=True)
    remote.background_hardlink({}, request.session['token'])
    return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================


@require_POST
@csrf_protect
def replicate(request):
    """
    Replicate configuration from the central Cobbler server, configured
    in /etc/cobbler/settings (note: this is uni-directional!)

    FIXME: this is disabled because we really need a web page to provide options for
    this command.

    """
    # settings = remote.get_settings()
    # options = settings # just load settings from file until we decide to ask user (later?)
    # remote.background_replicate(options, request.session['token'])
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/replicate", expired=True)
    return HttpResponseRedirect("/cobbler_web/task_created")

# ======================================================================


def __names_from_dicts(lod, optional=True):
    """
    Tiny helper function.
    Get the names out of an array of dictionaries that the remote interface
    returns.
    """
    results = []
    if optional:
        results.append("<<None>>")
    for x in lod:
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
    if obj_name is not None:
        target = "/%s" % obj_name
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/edit%s" % (what, target), expired=True)

    obj = None

    child = False
    if what == "subprofile":
        what = "profile"
        child = True

    if obj_name is not None:
        editable = remote.check_access_no_fail(request.session['token'], "modify_%s" % what, obj_name)
        obj = remote.get_item(what, obj_name, False)
    else:
        editable = remote.check_access_no_fail(request.session['token'], "new_%s" % what, None)
        obj = None

    interfaces = {}
    if what == "system":
        if obj:
            interfaces = obj.get("interfaces", {})
        else:
            interfaces = {}

    fields = get_fields(what, child, obj)
    if what == "system":
        fields += get_network_interface_fields()

    # create the autoinstall pulldown list
    autoinstalls = remote.get_autoinstall_templates()
    autoinstall_list = ["", "<<inherit>>"]
    for autoinstall in autoinstalls:
        autoinstall_list.append(autoinstall)

    # populate some select boxes
    if what == "profile":
        if (obj and obj["parent"] not in (None, "")) or child:
            __tweak_field(fields, "parent", "choices", __names_from_dicts(remote.get_profiles()))
        else:
            __tweak_field(fields, "distro", "choices", __names_from_dicts(remote.get_distros()))
        __tweak_field(fields, "autoinstall", "choices", autoinstall_list)
        __tweak_field(fields, "repos", "choices", __names_from_dicts(remote.get_repos()))
        __tweak_field(fields, "mgmt_classes", "choices", __names_from_dicts(remote.get_mgmtclasses(), optional=False))

    elif what == "system":
        __tweak_field(fields, "profile", "choices", __names_from_dicts(remote.get_profiles()))
        __tweak_field(fields, "image", "choices", __names_from_dicts(remote.get_images(), optional=True))
        __tweak_field(fields, "autoinstall", "choices", autoinstall_list)
        __tweak_field(fields, "mgmt_classes", "choices", __names_from_dicts(remote.get_mgmtclasses(), optional=False))

    elif what == "mgmtclass":
        __tweak_field(fields, "packages", "choices", __names_from_dicts(remote.get_packages()))
        __tweak_field(fields, "files", "choices", __names_from_dicts(remote.get_files()))

    elif what == "distro":
        __tweak_field(fields, "arch", "choices", remote.get_valid_archs())
        __tweak_field(fields, "os_version", "choices", remote.get_valid_os_versions())
        __tweak_field(fields, "breed", "choices", remote.get_valid_breeds())
        __tweak_field(fields, "mgmt_classes", "choices", __names_from_dicts(remote.get_mgmtclasses(), optional=False))

    elif what == "image":
        __tweak_field(fields, "arch", "choices", remote.get_valid_archs())
        __tweak_field(fields, "breed", "choices", remote.get_valid_breeds())
        __tweak_field(fields, "os_version", "choices", remote.get_valid_os_versions())
        __tweak_field(fields, "autoinst", "choices", autoinstall_list)

    # if editing save the fields in the session for comparison later
    if editmode == "edit":
        request.session['%s_%s' % (what, obj_name)] = fields

    # build UI tabs metadata
    if what == "distro":
        sections_data = field_ui_info.DISTRO_UI_FIELDS_MAPPING
    elif what == "file":
        sections_data = field_ui_info.FILE_UI_FIELDS_MAPPING
    elif what == "image":
        sections_data = field_ui_info.IMAGE_UI_FIELDS_MAPPING
    elif what == "mgmtclass":
        sections_data = field_ui_info.MGMTCLASS_UI_FIELDS_MAPPING
    elif what == "package":
        sections_data = field_ui_info.PACKAGE_UI_FIELDS_MAPPING
    elif what == "profile":
        sections_data = field_ui_info.PROFILE_UI_FIELDS_MAPPING
    elif what == "repo":
        sections_data = field_ui_info.REPO_UI_FIELDS_MAPPING
    elif what == "system":
        sections_data = field_ui_info.SYSTEM_UI_FIELDS_MAPPING
    sections = _create_sections_metadata(what, sections_data, fields)

    inames = list(interfaces.keys())
    inames.sort()

    html = render(request, 'generic_edit.tmpl', {
        'what': what,
        'sections': sections,
        'subobject': child,
        'editmode': editmode,
        'editable': editable,
        'interfaces': interfaces,
        'interface_names': inames,
        'interface_length': len(inames),
        'version': remote.extended_version(request.session['token'])['version'],
        'username': username,
        'name': obj_name
    })
    return HttpResponse(html)

# ======================================================================


@require_POST
@csrf_protect
def generic_save(request, what):
    """
    Saves an object back using the Cobbler API after clearing any 'generic_edit' page.
    """
    if not test_user_authenticated(request):
        return login(request, next="/cobbler_web/%s/list" % what, expired=True)

    # load request fields and see if they are valid
    editmode = request.POST.get('editmode', 'edit')
    obj_name = request.POST.get('name', "")
    subobject = request.POST.get('subobject', "False")

    if subobject == "False":
        subobject = False
    else:
        subobject = True

    if obj_name == "":
        return error_page(request, "Required field name is missing")

    prev_fields = []
    if "%s_%s" % (what, obj_name) in request.session and editmode == "edit":
        prev_fields = request.session["%s_%s" % (what, obj_name)]

    # grab the remote object handle
    # for edits, fail in the object cannot be found to be edited
    # for new objects, fail if the object already exists
    if editmode == "edit":
        if not remote.has_item(what, obj_name):
            return error_page(request, "Failure trying to access item %s, it may have been deleted." % (obj_name))
        obj_id = remote.get_item_handle(what, obj_name, request.session['token'])
    else:
        if remote.has_item(what, obj_name):
            return error_page(request, "Could not create a new item %s, it already exists." % (obj_name))
        obj_id = remote.new_item(what, request.session['token'])

    # system needs either profile or image to be set
    # fail if both are not set
    if what == "system":
        profile = request.POST.getlist('profile')
        image = request.POST.getlist('image')
        if "<<None>>" in profile and "<<None>>" in image:
            return error_page(request, "Please provide either a valid profile or image for the system")

    # walk through our fields list saving things we know how to save
    fields = get_fields(what, subobject)

    for field in fields:

        if field['name'] == 'name' and editmode == 'edit':
            # do not attempt renames here
            continue
        else:
            # check and see if the value exists in the fields stored in the session
            prev_value = None
            for prev_field in prev_fields:
                if prev_field['name'] == field['name']:
                    prev_value = prev_field['value']
                    break

            value = request.POST.get(field['name'], None)
            # Checkboxes return the value of the field if checked, otherwise None
            # convert to True/False
            if field["html_element"] == "checkbox":
                if value == field['name']:
                    value = True
                else:
                    value = False

            # Multiselect fields are handled differently
            if field["html_element"] == "multiselect":
                values = request.POST.getlist(field['name'])
                value = []
                if '<<inherit>>' in values:
                    value = '<<inherit>>'
                else:
                    for single_value in values:
                        if single_value != "<<None>>":
                            value.insert(0, single_value)

            if value is not None:
                if value == "<<None>>":
                    value = ""
                if value is not None and (not subobject or field['name'] != 'distro') and value != prev_value:
                    try:
                        remote.modify_item(what, obj_id, field['name'], value, request.session['token'])
                    except Exception as e:
                        return error_page(request, str(e))

    # special handling for system interface fields
    # which are the only objects in Cobbler that will ever work this way
    if what == "system":
        network_interface_fields = get_network_interface_fields()
        interfaces = request.POST.get('interface_list', "").split(",")
        for interface in interfaces:
            if interface == "":
                continue
            ifdata = {}
            for field in network_interface_fields:
                ifdata["%s-%s" % (field["name"], interface)] = request.POST.get("%s-%s" % (field["name"], interface), "")
            ifdata = utils.strip_none(ifdata)
            # FIXME: I think this button is missing.
            present = request.POST.get("present-%s" % interface, "")
            original = request.POST.get("original-%s" % interface, "")
            try:
                if present == "0" and original == "1":
                    remote.modify_system(obj_id, 'delete_interface', interface, request.session['token'])
                elif present == "1":
                    remote.modify_system(obj_id, 'modify_interface', ifdata, request.session['token'])
            except Exception as e:
                return error_page(request, str(e))

    try:
        remote.save_item(what, obj_id, request.session['token'], editmode)
    except Exception as e:
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

    remote = xmlrpc.client.Server(url_cobbler_api, allow_none=True)

    # if we have a token, get the associated username from
    # the remote server via XMLRPC. We then compare that to
    # the value stored in the session.  If everything matches up,
    # the user is considered successfully authenticated
    if 'token' in request.session and request.session['token'] != '':
        try:
            if remote.token_check(request.session['token']):
                token_user = remote.get_user_from_token(request.session['token'])
                if 'username' in request.session and request.session['username'] == token_user:
                    username = request.session['username']
                    return True
        except:
            # just let it fall through to the 'return False' below
            pass
    return False


use_passthru = -1


@csrf_protect
def login(request, next=None, message=None, expired=False):
    global use_passthru
    if use_passthru < 0:
        token = remote.login("", utils.get_shared_secret())
        auth_module = remote.get_authn_module_name(token)
        use_passthru = auth_module == 'authentication.passthru'

    if use_passthru:
        return accept_remote_user(request, next)

    if expired and not message:
        message = "Sorry, either you need to login or your session expired."
    return render(request, 'login.tmpl', {'next': next, 'message': message})


def accept_remote_user(request, nextsite):
    global username

    username = request.META['REMOTE_USER']
    token = remote.login(username, utils.get_shared_secret())

    request.session['username'] = username
    request.session['token'] = token
    if nextsite:
        return HttpResponseRedirect(nextsite)
    else:
        return HttpResponseRedirect("/cobbler_web")


@require_POST
@csrf_protect
def do_login(request):
    global remote
    global username
    global url_cobbler_api

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    nextsite = request.POST.get('next', None)

    if url_cobbler_api is None:
        url_cobbler_api = utils.local_get_cobbler_api_url()

    remote = xmlrpc.client.Server(url_cobbler_api, allow_none=True)

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
        return login(request, nextsite, message="Login failed, please try again")


@require_POST
@csrf_protect
def do_logout(request):
    request.session['username'] = ""
    request.session['token'] = ""
    return HttpResponseRedirect("/cobbler_web")
