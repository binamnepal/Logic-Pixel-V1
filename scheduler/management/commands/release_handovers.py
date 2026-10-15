from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from conversations.models import Handover, Message


class Command(BaseCommand):
    help = "Hand chats back to the AI when nobody has written for N hours (default 24)."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24)

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(hours=opts["hours"])
        n = 0
        for h in Handover.objects.filter(resolved_at__isnull=True).select_related("contact"):
            c = h.contact
            last = (Message.objects.filter(contact=c, sender__in=["staff", "contact"])
                    .order_by("-created_at").first())
            if last and last.created_at < cutoff:
                c.handover_active = False
                c.save(update_fields=["handover_active", "updated_at"])
                h.resolved_at, h.resolved_by = timezone.now(), "auto-release"
                h.save()
                n += 1
        self.stdout.write(f"released: {n}")
