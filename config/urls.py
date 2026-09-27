from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),

    # Attendance App
    path("", include("attendance.urls")),

    # Accounts App
    path("accounts/", include("attendance.accounts.urls")),
]


# Media files
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )