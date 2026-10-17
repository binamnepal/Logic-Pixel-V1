from datetime import timedelta
from django.utils import timezone
from . import email as email_channel
from . import telegram
from .models import Notification

DEDUPE_MINUTES = 30


def notify_staff(business, contact, reason: str, trigger: str = "handover"):
    since = timezone.now() - timedelta(minutes=DEDUPE_MINUTES)
    if Notification.objects.filter(contact=contact, trigger=trigger, ok=True, created_at__gte=since).exists():
        return  # one alert per contact per trigger every 30 minutes
    recent = "\n".join(f"{m.sender}: {m.body}" for m in contact.messages.order_by("-created_at")[:5][::-1])
    attrs = ", ".join(f"{k}: {v}" for k, v in (contact.attributes or {}).items())
    text = (f"[{business.name}] Lead needs attention\nName: {contact.name or '-'}\nPhone: {contact.wa_phone}\n"
            f"Status: {contact.get_status_display()}\nReason: {reason}\nDetails: {attrs or '-'}\n\nRecent:\n{recent}")

    def log(channel, result):
        ok, err = result
        Notification.objects.create(business=business, contact=contact, trigger=trigger,
                                    channel=channel, ok=ok, error=err[:200])

    if business.telegram_chat_id:
        log("telegram", telegram.send(business.telegram_chat_id, text))

    emails = business.get_staff_emails()
    if emails:
        subject = f"[{business.name}] {contact.get_status_display()}: {contact.name or contact.wa_phone}"
        log("email", email_channel.send(emails, subject, text))