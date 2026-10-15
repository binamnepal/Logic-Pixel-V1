from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from agents.runner import reply
from conversations.models import Contact
from conversations.services import set_status, window_open


class Command(BaseCommand):
    help = "Send one follow-up to contacts silent for 12h (inside the 24h window). Run every 15-30 min."

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(hours=12)
        qs = (Contact.objects
              .filter(handover_active=False, followup_sent=False, last_contact_msg_at__lte=cutoff)
              .exclude(status__in=[Contact.Status.CLOSED, Contact.Status.READY]))
        sent = 0
        for c in qs:
            if not window_open(c):
                continue  # >24h needs an approved template; leave to staff
            if not c.last_bot_msg_at or c.last_bot_msg_at < c.last_contact_msg_at:
                continue  # they are waiting on us, not the other way round
            if reply(c, "Hello! Just checking in on your enquiry. Reply here whenever you're ready and we'll continue."):
                c.followup_sent = True
                set_status(c, Contact.Status.FOLLOWUP, "12h no reply")
                c.save()
                sent += 1
        self.stdout.write(f"follow-ups sent: {sent}")
