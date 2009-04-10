from django.conf.urls.defaults import *
from views import *

# Uncomment the next two lines to enable the admin:
# from cobbler_web.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^cobbler_web/$', index),
    (r'^cobbler_web/distro/search$', search, {'what':'distro'}),
    (r'^cobbler_web/profile/search$', search, {'what':'profile'}),
    (r'^cobbler_web/system/search$', search, {'what':'system'}),
    (r'^cobbler_web/repo/search$', search, {'what':'repo'}),
    (r'^cobbler_web/image/search$', search, {'what':'image'}),
    (r'^cobbler_web/distro/list$', distro_list),
    (r'^cobbler_web/distro/edit$', distro_edit),
    (r'^cobbler_web/distro/edit/(?P<distro_name>.+)$', distro_edit),
    (r'^cobbler_web/distro/save$', distro_save),
    (r'^cobbler_web/profile/list$', profile_list),
    (r'^cobbler_web/profile/edit$', profile_edit),
    (r'^cobbler_web/profile/edit/(?P<profile_name>.+)$', profile_edit),
    (r'^cobbler_web/subprofile/edit$', profile_edit, {'subprofile': 1}),
    (r'^cobbler_web/profile/save$', profile_save),
    (r'^cobbler_web/system/list$', system_list),
    (r'^cobbler_web/system/edit$', system_edit),
    (r'^cobbler_web/system/edit/(?P<system_name>.+)$', system_edit, {'editmode': 'edit'}),
    (r'^cobbler_web/system/save$', system_save),
    (r'^cobbler_web/repo/list$', repo_list),
    (r'^cobbler_web/repo/edit$', repo_edit),
    (r'^cobbler_web/repo/edit/(?P<repo_name>.+)$', repo_edit),
    (r'^cobbler_web/image/list$', image_list),
    (r'^cobbler_web/image/edit$', image_edit),
    (r'^cobbler_web/image/edit/(?P<image_name>.+)$', image_edit),
    (r'^cobbler_web/ksfile/list$', ksfile_list),
    (r'^cobbler_web/ksfile/edit$', ksfile_edit),
    (r'^cobbler_web/ksfile/edit/(?P<ksfile_name>.+)$', ksfile_edit),
    (r'^cobbler_web/dosearch/(?P<what>.+)$', dosearch),
    (r'^cobbler_web/random_mac$', random_mac),
    (r'^cobbler_web/random_mac/virttype/(?P<virttype>.+)$', random_mac),
)
