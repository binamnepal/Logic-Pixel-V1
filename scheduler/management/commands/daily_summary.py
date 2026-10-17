from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from businesses.models import Business
from conversations.models import Contact, Handover
from notifications import email as email_channel
from notifications import telegram


class Command(BaseCommand):
    help = "Send each business a daily summary (new leads, ready leads, waiting handovers)."

    def handle(self, *args, **opts):
        since = timezone.now() - timedelta(hours=24)
        for b in Business.objects.filter(active=True):
            new = Contact.objects.filter(business=b, created_at__gte=since).count()
            ready = Contact.objects.filter(business=b, status=Contact.Status.READY).count()
            waiting = Handover.objects.filter(contact__business=b, resolved_at__isnull=True).count()
            text = (f"[{b.name}] Daily summary\nNew enquiries (24h): {new}\n"
                    f"Consultation ready: {ready}\nHandovers waiting for staff: {waiting}")
            if b.telegram_chat_id:
                telegram.send(b.telegram_chat_id, text)
            emails = b.get_staff_emails()
            if emails:
                email_channel.send(emails, f"[{b.name}] Daily summary", text)
            self.stdout.write(text)