
from django.urls import path, re_path

from cobbler.web import views

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = [
    path('', views.index, name="index"),

    path('setting/list', views.setting_list, name="setting_list"),
    re_path(r'^setting/edit/(?P<setting_name>.+)$', views.setting_edit, name="setting_edit"),
    path('setting/save', views.setting_save, name="setting_save"),

    re_path(r'^aifile/list(/(?P<page>\d+))?$', views.aifile_list, name="aifile_list"),
    path('aifile/edit', views.aifile_edit, {'editmode': 'new'}, name="aifile_edit_new"),
    re_path(r'^aifile/edit/file:(?P<aifile_name>.+)$', views.aifile_edit, {'editmode': 'edit'}, name="aifile_edit"),
    path('aifile/save', views.aifile_save, name="aifile_save"),

    re_path(r'^snippet/list(/(?P<page>\d+))?$', views.snippet_list, name="snippet_list"),
    path('snippet/edit', views.snippet_edit, {'editmode': 'new'}, name="snippet_edit_new"),
    re_path(r'^snippet/edit/file:(?P<snippet_name>.+)$', views.snippet_edit, {'editmode': 'edit'}, name="snippet_edit"),
    path('snippet/save', views.snippet_save, name="snippet_save"),

    re_path(r'^(?P<what>\w+)/list(/(?P<page>\d+))?', views.genlist, name="what_list"),
    re_path(r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', views.modify_list, name="what_modifylist"),
    re_path(r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', views.generic_edit, {'editmode': 'edit'}, name="what_edit"),
    re_path(r'^(?P<what>\w+)/edit$', views.generic_edit, {'editmode': 'new'}, name="what_edit_new"),

    re_path(r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_rename, name="what_remame"),
    re_path(r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', views.generic_copy, name="what_copy"),
    re_path(r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', views.generic_delete, name="what_delete"),

    re_path(r'^(?P<what>\w+)/multi/(?P<multi_mode>.+)/(?P<multi_arg>.+)$', views.generic_domulti, name="what_domulti"),
    path('utils/random_mac', views.random_mac, name="utils_random_mac"),
    re_path(r'^utils/random_mac/virttype/(?P<virttype>.+)$', views.random_mac, name="utils_random_mac_virttype"),
    path('events', views.events, name="events"),
    re_path(r'^eventlog/(?P<event>.+)$', views.eventlog, name="events_log"),
    path('task_created', views.task_created, name="task_created"),
    path('sync', views.sync, name="sync"),
    path('reposync', views.reposync, name="reposync"),
    path('replicate', views.replicate, name="replicate"),
    path('hardlink', views.hardlink, name="hardlink"),
    re_path(r'^(?P<what>\w+)/save$', views.generic_save, name="what_save"),
    path('import/prompt', views.import_prompt, name="import_prompt"),
    path('import/run', views.import_run, name="import_run"),
    path('buildiso', views.buildiso, name="buildiso"),
    path('check', views.check, name="check"),

    path('login', views.login, name="login"),
    path('do_login', views.do_login, name="do_login"),
    path('logout', views.do_logout, name="logout"),
]
