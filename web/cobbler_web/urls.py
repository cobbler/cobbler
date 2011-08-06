from django.conf.urls.defaults import *
from views import *

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', index),

    (r'^ksfile/list(/(?P<page>\d+))?$', ksfile_list),
    (r'^ksfile/edit$', ksfile_edit, {'editmode':'new'}),
    (r'^ksfile/edit/file:(?P<ksfile_name>.+)$', ksfile_edit, {'editmode':'edit'}),
    (r'^ksfile/save$', ksfile_save),

    (r'^snippet/list(/(?P<page>\d+))?$', snippet_list),
    (r'^snippet/edit$', snippet_edit, {'editmode':'new'}),
    (r'^snippet/edit/file:(?P<snippet_name>.+)$', snippet_edit, {'editmode':'edit'}),
    (r'^snippet/save$', snippet_save),

    (r'^(?P<what>\w+)/list(/(?P<page>\d+))?', genlist),
    (r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', modify_list),
    (r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', generic_edit, {'editmode': 'edit'}),
    (r'^(?P<what>\w+)/edit$', generic_edit, {'editmode': 'new'}),

    (r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', generic_rename),
    (r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', generic_copy),
    (r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', generic_delete),

    (r'^(?P<what>\w+)/multi/(?P<multi_mode>.+)/(?P<multi_arg>.+)$', generic_domulti),
    (r'^utils/random_mac$', random_mac),
    (r'^utils/random_mac/virttype/(?P<virttype>.+)$', random_mac),
    (r'^settings$', settings),
    (r'^events$', events),
    (r'^eventlog/(?P<event>.+)$', eventlog),
    (r'^task_created$', task_created),
    (r'^sync$', sync),
    (r'^reposync$',reposync),
    (r'^replicate$',replicate),
    (r'^hardlink', hardlink),
    (r'^(?P<what>\w+)/save$', generic_save),
    (r'^import/prompt$', import_prompt),
    (r'^import/run$', import_run),
    (r'^buildiso$', buildiso),
    (r'^check$', check),

    (r'^login$', login),
    (r'^do_login$', do_login),
    (r'^logout$', do_logout),
)
