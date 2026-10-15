from django.contrib import admin
from django.utils import timezone
from businesses.models import scope_queryset
from .models import Contact, Handover, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    readonly_fields = ("direction", "sender", "body", "delivery_status", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "wa_phone", "business", "country", "status", "handover_active", "last_contact_msg_at")
    list_filter = ("business", "status", "handover_active")
    search_fields = ("name", "wa_phone")
    inlines = [MessageInline]
    actions = ["take_over", "hand_back_to_ai"]

    @admin.display(description="Country")
    def country(self, obj):
        return (obj.attributes or {}).get("country", "")

    def get_queryset(self, request):
        return scope_queryset(super().get_queryset(request), request.user)

    @admin.action(description="Take over (AI goes silent)")
    def take_over(self, request, queryset):
        queryset.update(handover_active=True)

    @admin.action(description="Hand back to AI")
    def hand_back_to_ai(self, request, queryset):
        Handover.objects.filter(contact__in=queryset, resolved_at__isnull=True).update(
            resolved_at=timezone.now(), resolved_by=request.user.get_username())
        queryset.update(handover_active=False)


@admin.register(Handover)
class HandoverAdmin(admin.ModelAdmin):
    list_display = ("contact", "reason", "started_at", "resolved_at", "resolved_by")

    def get_queryset(self, request):
        return scope_queryset(super().get_queryset(request), request.user, path="contact__business")
