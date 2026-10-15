from django.db import models
from businesses.models import Business
from conversations.models import Contact


class Notification(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL)
    trigger = models.CharField(max_length=32)
    channel = models.CharField(max_length=16)
    ok = models.BooleanField(default=False)
    error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
