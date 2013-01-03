from django.conf.urls import *
from django.views.generic.simple import redirect_to

cobbler_web_urls = patterns("",
                            url(r'^$', 'cobbler_web.views.index'),

                            url(r'^setting/list$', 'cobbler_web.views.setting_list'),
                            url(r'^setting/edit/(?P<setting_name>.+)$', 'cobbler_web.views.setting_edit'),
                            url(r'^setting/save$', 'cobbler_web.views.setting_save'),

                            url(r'^ksfile/list(/(?P<page>\d+))?$', 'cobbler_web.views.ksfile_list'),
                            url(r'^ksfile/edit$', 'cobbler_web.views.ksfile_edit', {'editmode':'new'}),
                            url(r'^ksfile/edit/file:(?P<ksfile_name>.+)$', 'cobbler_web.views.ksfile_edit', {'editmode':'edit'}),
                            url(r'^ksfile/save$', 'cobbler_web.views.ksfile_save'),

                            url(r'^snippet/list(/(?P<page>\d+))?$', 'cobbler_web.views.snippet_list'),
                            url(r'^snippet/edit$', 'cobbler_web.views.snippet_edit', {'editmode':'new'}),
                            url(r'^snippet/edit/file:(?P<snippet_name>.+)$', 'cobbler_web.views.snippet_edit', {'editmode':'edit'}),
                            url(r'^snippet/save$', 'cobbler_web.views.snippet_save'),

                            url(r'^(?P<what>\w+)/list(/(?P<page>\d+))?', 'cobbler_web.views.genlist'),
                            url(r'^(?P<what>\w+)/modifylist/(?P<pref>[!\w]+)/(?P<value>.+)$', 'cobbler_web.views.modify_list'),
                            url(r'^(?P<what>\w+)/edit/(?P<obj_name>.+)$', 'cobbler_web.views.generic_edit', {'editmode': 'edit'}),
                            url(r'^(?P<what>\w+)/edit$', 'cobbler_web.views.generic_edit', {'editmode': 'new'}),

                            url(r'^(?P<what>\w+)/rename/(?P<obj_name>.+)/(?P<obj_newname>.+)$', 'cobbler_web.views.generic_rename'),
                            url(r'^(?P<what>\w+)/copy/(?P<obj_name>.+)/(?P<obj_newname>.+)$', 'cobbler_web.views.generic_copy'),
                            url(r'^(?P<what>\w+)/delete/(?P<obj_name>.+)$', 'cobbler_web.views.generic_delete'),

                            url(r'^(?P<what>\w+)/multi/(?P<multi_mode>.+)/(?P<multi_arg>.+)$', 'cobbler_web.views.generic_domulti'),
                            url(r'^utils/random_mac$', 'cobbler_web.views.random_mac'),
                            url(r'^utils/random_mac/virttype/(?P<virttype>.+)$', 'cobbler_web.views.random_mac'),
                            url(r'^events$', 'cobbler_web.views.events'),
                            url(r'^eventlog/(?P<event>.+)$', 'cobbler_web.views.eventlog'),
                            url(r'^task_created$', 'cobbler_web.views.task_created'),
                            url(r'^sync$', 'cobbler_web.views.sync'),
                            url(r'^reposync$', 'cobbler_web.views.reposync'),
                            url(r'^replicate$', 'cobbler_web.views.replicate'),
                            url(r'^hardlink', 'cobbler_web.views.hardlink'),
                            url(r'^(?P<what>\w+)/save$', 'cobbler_web.views.generic_save'),
                            url(r'^import/prompt$', 'cobbler_web.views.import_prompt'),
                            url(r'^import/run$', 'cobbler_web.views.import_run'),
                            url(r'^buildiso$', 'cobbler_web.views.buildiso'),
                            url(r'^check$', 'cobbler_web.views.check'),

                            url(r'^login$', 'cobbler_web.views.login'),
                            url(r'^do_login$', 'cobbler_web.views.do_login'),
                            url(r'^logout$', 'cobbler_web.views.do_logout'))

urlpatterns = patterns('',
                       url(r"^$", redirect_to, {"url": "/cobbler_web/"}),
                       url(r"^cobbler_web/", include(cobbler_web_urls)))
