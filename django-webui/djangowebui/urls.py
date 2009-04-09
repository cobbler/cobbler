from django.conf.urls.defaults import *
from views import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^django/$', index),
    (r'^django/distro/search$', search, {'what':'distro'}),
    (r'^django/profile/search$', search, {'what':'profile'}),
    (r'^django/system/search$', search, {'what':'system'}),
    (r'^django/repo/search$', search, {'what':'repo'}),
    (r'^django/image/search$', search, {'what':'image'}),
    (r'^django/distro/list$', distro_list),
    (r'^django/distro/edit$', distro_edit),
    (r'^django/distro/edit/(?P<distro_name>.+)$', distro_edit),
    (r'^django/profile/list$', profile_list),
    (r'^django/profile/edit$', profile_edit),
    (r'^django/profile/edit/(?P<profile_name>.+)$', profile_edit),
    (r'^django/subprofile/edit$', profile_edit, {'subprofile': 1}),
    (r'^django/system/list$', system_list),
    (r'^django/system/edit$', system_edit),
    (r'^django/system/edit/(?P<system_name>.+)$', system_edit, {'editmode': 'edit'}),
    (r'^django/repo/list$', repo_list),
    (r'^django/repo/edit$', repo_edit),
    (r'^django/repo/edit/(?P<repo_name>.+)$', repo_edit),
    (r'^django/image/list$', image_list),
    (r'^django/image/edit$', image_edit),
    (r'^django/image/edit/(?P<image_name>.+)$', image_edit),
    (r'^django/ksfile/list$', ksfile_list),
    (r'^django/ksfile/edit$', ksfile_edit),
    (r'^django/ksfile/edit/(?P<ksfile_name>.+)$', ksfile_edit),
)
