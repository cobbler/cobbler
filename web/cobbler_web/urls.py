from django.conf.urls.defaults import *
from views import *

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', index),

    (r'^ksfile/list(/(?P<page>\d+))?$', ksfile_list),
    (r'^ksfile/edit$', ksfile_edit, {'editmode':'new'}),
    (r'^ksfile/edit/(?P<ksfile_name>.+)$', ksfile_edit, {'editmode':'edit'}),
    (r'^ksfile/save$', ksfile_save),

    (r'^snippet/list(/(?P<page>\d+))?$', snippet_list),
    (r'^snippet/edit$', snippet_edit, {'editmode':'new'}),
    (r'^snippet/edit/(?P<snippet_name>.+)$', snippet_edit, {'editmode':'edit'}),
    (r'^snippet/save$', snippet_save),

    (r'^(?P<what>\w+)/list(/(?P<page>\d+))?', genlist),
    (r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', modify_list),

    #(r'^(?P<what>\w+)/addfilter/(?P<filter>.+)$', modify_filter, {'action':'add'}),
    #(r'^(?P<what>\w+)/removefilter/(?P<filter>.+)$', modify_filter, {'action':'remove'}),

    (r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', generic_edit, {'editmode': 'edit'}),
    (r'^(?P<what>\w+)/edit$', generic_edit, {'editmode': 'new'}),

    # FIXME: copy/edit/rename should not be edit type actions

    #(r'^(?P<what>\w+)/rename/(?P<obj_name>[^/]+)$', generic_rename),
    #(r'^(?P<what>\w+)/copy/(?P<obj_name>[^/]+)$', generic_rename),

    (r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', generic_rename),
    (r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', generic_copy),
    (r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', generic_delete),

    #(r'^(?P<what>\w+)/rename/(?P<obj_name>[^/]+)/(?P<obj_newname>[^/]+)$', generic_rename),
    #(r'^(?P<what>\w+)/(?P<multi_mode>[\w\-]+)/multi$', generic_multi),
    #(r'^(?P<what>\w+)/(?P<multi_mode>[\w\-]+)/domulti$', generic_domulti),
    #(r'^distro/edit$', distro_edit),
    #(r'^distro/edit/(?P<distro_name>.+)$', distro_edit),
    #(r'^distro/save$', distro_save),
    #(r'^profile/edit$', profile_edit),
    #(r'^profile/edit/(?P<profile_name>.+)$', profile_edit),
    #(r'^subprofile/edit$', profile_edit, {'subprofile': 1}),
    #(r'^profile/save$', profile_save),
    #(r'^system/edit$', system_edit),
    #(r'^system/edit/(?P<system_name>.+)$', system_edit, {'editmode': 'edit'}),
    #(r'^system/save$', system_save),
    #(r'^network/edit$', network_edit),
    #(r'^network/edit/(?P<network_name>.+)$', network_edit),
    #(r'^network/save$', network_save),
    #(r'^repo/edit$', repo_edit),
    #(r'^repo/edit/(?P<repo_name>.+)$', repo_edit),
    #(r'^repo/save$', repo_save),
    #(r'^image/edit$', image_edit),
    #(r'^image/edit/(?P<image_name>.+)$', image_edit),
    #(r'^image/save$', image_save),
    #(r'^random_mac$', random_mac),
    #(r'^random_mac/virttype/(?P<virttype>.+)$', random_mac),
    (r'^settings$', settings),
    (r'^sync$', dosync),
    #(r'^(?P<what>\w+)/edit$', generic_edit),
    #(r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', generic_edit, {'editmode': 'edit'}),
    (r'^(?P<what>\w+)/save$', generic_save),
)
