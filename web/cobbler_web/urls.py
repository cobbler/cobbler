from django.conf.urls import url
import views

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = (
    url(r'^$', views.index),

    url(r'^setting/list$', views.setting_list),
    url(r'^setting/edit/(?P<setting_name>.+)$', views.setting_edit),
    url(r'^setting/save$', views.setting_save),

    url(r'^ksfile/list(/(?P<page>\d+))?$', views.ksfile_list),
    url(r'^ksfile/edit$', views.ksfile_edit, {'editmode':'new'}),
    url(r'^ksfile/edit/file:(?P<ksfile_name>.+)$', views.ksfile_edit, {'editmode':'edit'}),
    url(r'^ksfile/save$', views.ksfile_save),

    url(r'^snippet/list(/(?P<page>\d+))?$', views.snippet_list),
    url(r'^snippet/edit$', views.snippet_edit, {'editmode':'new'}),
    url(r'^snippet/edit/file:(?P<snippet_name>.+)$', views.snippet_edit, {'editmode':'edit'}),
    url(r'^snippet/save$', views.snippet_save),

    url(r'^(?P<what>\w+)/list(/(?P<page>\d+))?', views.genlist),
    url(r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', views.modify_list),
    url(r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', views.generic_edit, {'editmode': 'edit'}),
    url(r'^(?P<what>\w+)/edit$', views.generic_edit, {'editmode': 'new'}),

    url(r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_rename),
    url(r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_copy),
    url(r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', views.generic_delete),

    url(r'^(?P<what>\w+)/multi/(?P<multi_mode>.+)/(?P<multi_arg>.+)$', views.generic_domulti),
    url(r'^utils/random_mac$', views.random_mac),
    url(r'^utils/random_mac/virttype/(?P<virttype>.+)$', views.random_mac),
    url(r'^events$', views.events),
    url(r'^eventlog/(?P<event>.+)$', views.eventlog),
    url(r'^task_created$', views.task_created),
    url(r'^sync$', views.sync),
    url(r'^reposync$',views.reposync),
    url(r'^replicate$',views.replicate),
    url(r'^hardlink', views.hardlink),
    url(r'^(?P<what>\w+)/save$', views.generic_save),
    url(r'^import/prompt$', views.import_prompt),
    url(r'^import/run$', views.import_run),
    url(r'^buildiso$', views.buildiso),
    url(r'^check$', views.check),

    url(r'^login$', views.login),
    url(r'^do_login$', views.do_login),
    url(r'^logout$', views.do_logout),
)
