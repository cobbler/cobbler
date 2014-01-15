from django.conf.urls import patterns

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    (r'^', include('cobbler_web.urls')),
)

