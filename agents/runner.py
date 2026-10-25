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
    """Send a WhatsApp text, store it, and LOG any failure (never fail silently)."""
    try:
        ok, wa_id, err = send_text(contact.business, contact.wa_phone, text)
    except Exception as exc:
        log.exception("send_text crashed for contact %s", contact.pk)
        ok, wa_id, err = False, None, str(exc)[:200]

    if ok:
        log.info("Sent reply to contact %s (wa id %s)", contact.pk, wa_id)
        contact.last_bot_msg_at = timezone.now()
    else:
        log.error("WhatsApp send FAILED for contact %s (%s): %s",
                  contact.pk, contact.wa_phone, err)

    Message.objects.create(
        contact=contact, wa_msg_id=wa_id, direction="out", sender="bot", body=text,
        delivery_status="sent" if ok else "failed", error_code=err or "",
    )
    return ok


def handle_inbound(message_id: int):
    msg = Message.objects.select_related("contact__business").get(pk=message_id)
    contact, business = msg.contact, msg.contact.business
    log.info("handle_inbound: message %s from contact %s", message_id, contact.pk)

    if contact.handover_active:
        log.info("Skipping contact %s: handover_active is True (AI silent)", contact.pk)
        return  # staff own this chat; AI stays silent, messages are still saved

    if msg.msg_type != "text":
        reply(contact, "Sorry, I can only read text messages right now. Please type your question.")
        contact.save()
        return

    history = list(contact.messages.order_by("-created_at")[:12])[::-1]
    try:
        result = ask(business, contact, history)
    except Exception:
        log.exception("AI failed for contact %s", contact.pk)
        result = {"reply": FALLBACK, "details": {}, "needs_staff": True, "pause_ai": False,
                  "reason": "AI error", "wants_consultation": False}

    apply_details(contact, result["details"])
    needs_staff = result["needs_staff"]
    compute_status(contact, needs_staff, result["wants_consultation"])

    if window_open(contact):
        sent = reply(contact, result["reply"])
        if not sent:
            needs_staff = True
            result["reason"] = "WhatsApp send failed (check token / recipient list): " + (result["reason"] or "")
    else:
        log.warning("24h window closed for contact %s; reply NOT sent", contact.pk)
        needs_staff = True  # free-form messages are not allowed outside the 24h window
        result["reason"] = "window closed: " + (result["reason"] or "")

    if result["pause_ai"]:
        contact.handover_active = True
    contact.save()

    if needs_staff:
        if not Handover.objects.filter(contact=contact, resolved_at__isnull=True).exists():
            Handover.objects.create(contact=contact, reason=(result["reason"] or "needs staff")[:200])
        try:
            notify_staff(business, contact, result["reason"] or "needs staff", "handover")
        except Exception:
            log.exception("notify_staff failed for contact %s", contact.pk)
    elif contact.status == Contact.Status.READY:
        try:
            notify_staff(business, contact, "ready for consultation", "ready")
        except Exception:
            log.exception("notify_staff (ready) failed for contact %s", contact.pk)