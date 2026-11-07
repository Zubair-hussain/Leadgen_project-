from django.conf import settings
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/outreach/', include('outreach.urls')),
    path('api/', include('leads.urls')),
]

if settings.DEBUG:
    # The toolbar is enabled in settings when DEBUG is on; without its URLs
    # every HTML response (including the browsable API) raises NoReverseMatch.
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))
