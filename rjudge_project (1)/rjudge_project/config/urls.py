from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "RJudge Admin"
admin.site.site_title = "RJudge Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("problems.urls")),
]

if settings.DEBUG:  # serve uploaded profile pictures during development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
