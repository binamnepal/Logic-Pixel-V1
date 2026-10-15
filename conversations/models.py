from django.db import models
from businesses.models import Business


class Contact(models.Model):
    class Status(models.TextChoices):
        NEW = "new_enquiry", "New Enquiry"
        INFO = "info_collected", "Info Collected"
        FOLLOWUP = "followup_needed", "Follow-up Needed"
        STAFF = "staff_assistance_req", "Staff Assistance Req"
        READY = "consultation_ready", "Consultation Ready"
        CLOSED = "closed", "Closed / Not Proceeding"

    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    wa_phone = models.CharField(max_length=32)
    name = models.CharField(max_length=120, blank=True)
    attributes = models.JSONField(default=dict, blank=True)  # country, study_level, intake, ...
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW)
    handover_active = models.BooleanField(default=False)
    last_contact_msg_at = models.DateTimeField(null=True, blank=True)
    last_bot_msg_at = models.DateTimeField(null=True, blank=True)
    followup_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "wa_phone")

    def __str__(self):
        return f"{self.name or self.wa_phone} ({self.business})"


class Message(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="messages")
    wa_msg_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
    direction = models.CharField(max_length=3, choices=[("in", "in"), ("out", "out")])
    sender = models.CharField(max_length=8, choices=[("contact", "contact"), ("bot", "bot"), ("staff", "staff")])
    body = models.TextField(blank=True)
    msg_type = models.CharField(max_length=16, default="text")
    delivery_status = models.CharField(max_length=16, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class ProcessedEvent(models.Model):
    event_id = models.CharField(max_length=128, primary_key=True)
    received_at = models.DateTimeField(auto_now_add=True)


class StatusHistory(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=32, blank=True)
    new_status = models.CharField(max_length=32)
    reason = models.CharField(max_length=200, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)


class Handover(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="handovers")
    reason = models.CharField(max_length=200)
    started_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=120, blank=True)
