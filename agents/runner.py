import logging
from django.utils import timezone
from conversations.models import Contact, Handover, Message
from conversations.services import apply_details, compute_status, window_open
from notifications.notify import notify_staff
from whatsapp.client import send_text
from .engine import ask
from .prompts import FALLBACK

log = logging.getLogger(__name__)


def reply(contact: Contact, text: str) -> bool:
    ok, wa_id, err = send_text(contact.business, contact.wa_phone, text)
    Message.objects.create(contact=contact, wa_msg_id=wa_id, direction="out", sender="bot", body=text,
                           delivery_status="sent" if ok else "failed", error_code=err or "")
    if ok:
        contact.last_bot_msg_at = timezone.now()
    return ok


def handle_inbound(message_id: int):
    msg = Message.objects.select_related("contact__business").get(pk=message_id)
    contact, business = msg.contact, msg.contact.business
    if contact.handover_active:
        return  # staff own this chat; AI stays silent, messages are still saved
    if msg.msg_type != "text":
        reply(contact, "Sorry, I can only read text messages right now. Please type your question.")
        contact.save()
        return

    history = list(contact.messages.order_by("-created_at")[:12])[::-1]
    try:
        result = ask(business, contact, history)
    except Exception:
        log.exception("AI failed")
        result = {"reply": FALLBACK, "details": {}, "needs_staff": True, "pause_ai": False,
                  "reason": "AI error", "wants_consultation": False}

    apply_details(contact, result["details"])
    needs_staff = result["needs_staff"]
    compute_status(contact, needs_staff, result["wants_consultation"])

    if window_open(contact):
        reply(contact, result["reply"])
    else:
        needs_staff = True  # free-form messages are not allowed outside the 24h window
        result["reason"] = "window closed: " + result["reason"]
    if result["pause_ai"]:
        contact.handover_active = True
    contact.save()

    if needs_staff:
        if not Handover.objects.filter(contact=contact, resolved_at__isnull=True).exists():
            Handover.objects.create(contact=contact, reason=(result["reason"] or "needs staff")[:200])
        notify_staff(business, contact, result["reason"] or "needs staff", "handover")
    elif contact.status == Contact.Status.READY:
        notify_staff(business, contact, "ready for consultation", "ready")
