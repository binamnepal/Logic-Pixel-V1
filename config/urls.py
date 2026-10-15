from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", lambda r: JsonResponse({"ok": True})),
    path("webhook", include("whatsapp.urls")),
]
