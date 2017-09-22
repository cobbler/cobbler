from django.conf.urls import url, include

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = (
    url(r'^', include('cobbler_web.urls')),
)

