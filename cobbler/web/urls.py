from django.conf.urls import patterns

import views

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^$', views.index),

    (r'^setting/list$', views.setting_list),
    (r'^setting/edit/(?P<setting_name>.+)$', views.setting_edit),
    (r'^setting/save$', views.setting_save),

    (r'^aifile/list(/(?P<page>\d+))?$', views.aifile_list),
    (r'^aifile/edit$', views.aifile_edit, {'editmode': 'new'}),
    (r'^aifile/edit/file:(?P<aifile_name>.+)$', views.aifile_edit, {'editmode': 'edit'}),
    (r'^aifile/save$', views.aifile_save),

    (r'^snippet/list(/(?P<page>\d+))?$', views.snippet_list),
    (r'^snippet/edit$', views.snippet_edit, {'editmode': 'new'}),
    (r'^snippet/edit/file:(?P<snippet_name>.+)$', views.snippet_edit, {'editmode': 'edit'}),
    (r'^snippet/save$', views.snippet_save),

    (r'^(?P<what>\w+)/list(/(?P<page>\d+))?', views.genlist),
    (r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', views.modify_list),
    (r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', views.generic_edit, {'editmode': 'edit'}),
    (r'^(?P<what>\w+)/edit$', views.generic_edit, {'editmode': 'new'}),

    (r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_rename),
    (r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_copy),
    (r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', views.generic_delete),

    (r'^(?P<what>\w+)/multi/(?P<multi_mode>.+)/(?P<multi_arg>.+)$', views.generic_domulti),
    (r'^utils/random_mac$', views.random_mac),
    (r'^utils/random_mac/virttype/(?P<virttype>.+)$', views.random_mac),
    (r'^events$', views.events),
    (r'^eventlog/(?P<event>.+)$', views.eventlog),
    (r'^task_created$', views.task_created),
    (r'^sync$', views.sync),
    (r'^reposync$', views.reposync),
    (r'^replicate$', views.replicate),
    (r'^hardlink', views.hardlink),
    (r'^(?P<what>\w+)/save$', views.generic_save),
    (r'^import/prompt$', views.import_prompt),
    (r'^import/run$', views.import_run),
    (r'^buildiso$', views.buildiso),
    (r'^check$', views.check),

    (r'^login$', views.login),
    (r'^do_login$', views.do_login),
    (r'^logout$', views.do_logout),
)
