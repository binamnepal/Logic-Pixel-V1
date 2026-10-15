import hashlib
import hmac
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import async_task
from businesses.models import Business
from conversations.models import Contact, Handover, Message, ProcessedEvent


def _valid_signature(request) -> bool:
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@csrf_exempt
def webhook(request):
    if request.method == "GET":
        if (request.GET.get("hub.mode") == "subscribe"
                and request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN):
            return HttpResponse(request.GET.get("hub.challenge", ""))
        return HttpResponseForbidden()
    if request.method != "POST":
        return HttpResponse(status=405)
    if not _valid_signature(request):
        return HttpResponseForbidden()
    try:
        payload = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            _handle_value(change.get("value", {}))
    return HttpResponse("ok")  # always 200 fast; real work is queued


def _handle_value(value: dict):
    pnid = value.get("metadata", {}).get("phone_number_id")
    business = Business.objects.filter(phone_number_id=pnid, active=True).first()
    if not business:
        return
    names = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}

    for st in value.get("statuses", []):
        Message.objects.filter(wa_msg_id=st.get("id")).update(
            delivery_status=st.get("status", ""),
            error_code=str((st.get("errors") or [{}])[0].get("code", "")))

    for e in value.get("message_echoes", []):
        _handle_echo(business, e)

    for m in value.get("messages", []):
        wamid = m.get("id")
        _, created = ProcessedEvent.objects.get_or_create(event_id=wamid)
        if not created:
            continue  # duplicate delivery
        contact, _ = Contact.objects.get_or_create(
            business=business, wa_phone=m["from"], defaults={"name": names.get(m["from"], "")[:120]})
        contact.last_contact_msg_at = timezone.now()
        contact.followup_sent = False
        contact.save(update_fields=["last_contact_msg_at", "followup_sent", "updated_at"])
        mtype = m.get("type", "text")
        body = m.get("text", {}).get("body", "") if mtype == "text" else f"[{mtype}]"
        msg = Message.objects.create(contact=contact, wa_msg_id=wamid, direction="in",
                                     sender="contact", body=body, msg_type=mtype)
        async_task("agents.runner.handle_inbound", msg.id)


def _handle_echo(business, e: dict):
    """Message typed by staff in the WhatsApp Business app (coexistence): AI goes silent."""
    wamid = e.get("id")
    if not wamid or Message.objects.filter(wa_msg_id=wamid).exists():
        return
    _, created = ProcessedEvent.objects.get_or_create(event_id=wamid)
    if not created or not e.get("to"):
        return
    contact, _ = Contact.objects.get_or_create(business=business, wa_phone=e["to"])
    etype = e.get("type", "text")
    body = e.get("text", {}).get("body", "") if etype == "text" else f"[{etype}]"
    Message.objects.create(contact=contact, wa_msg_id=wamid, direction="out", sender="staff",
                           body=body, msg_type=etype, delivery_status="sent")
    if not contact.handover_active:
        contact.handover_active = True
        contact.save(update_fields=["handover_active", "updated_at"])
    if not Handover.objects.filter(contact=contact, resolved_at__isnull=True).exists():
        Handover.objects.create(contact=contact, reason="staff replied from WhatsApp app")
