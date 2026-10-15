from django.contrib import admin
from businesses.models import scope_queryset
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "business", "contact", "trigger", "channel", "ok", "error")
    list_filter = ("business", "trigger", "channel", "ok")

    def get_queryset(self, request):
        return scope_queryset(super().get_queryset(request), request.user)
