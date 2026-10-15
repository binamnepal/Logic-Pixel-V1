import re
from django.utils import timezone
from agents.prompts import FIELDS
from .models import Contact, StatusHistory

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WINDOW_HOURS = 24


def apply_details(contact: Contact, details: dict):
    """Validate AI-extracted details; never overwrite good data with empty values."""
    attrs = dict(contact.attributes or {})
    for f in FIELDS:
        v = details.get(f)
        if not isinstance(v, str) or not v.strip():
            continue
        v = v.strip()[:120]
        if f == "email" and not EMAIL_RE.match(v):
            continue
        if f == "name":
            contact.name = v
        else:
            attrs[f] = v
    contact.attributes = attrs


def set_status(contact: Contact, new: str, reason: str = ""):
    if contact.status == new:
        return
    if contact.status == Contact.Status.READY and new != Contact.Status.CLOSED:
        return  # never downgrade Consultation Ready automatically
    StatusHistory.objects.create(contact=contact, old_status=contact.status, new_status=new, reason=reason)
    contact.status = new


def compute_status(contact: Contact, needs_staff: bool, wants_consultation: bool):
    S = Contact.Status
    a = contact.attributes or {}
    info_ok = bool(contact.name and a.get("country") and a.get("study_level"))
    if needs_staff:
        set_status(contact, S.STAFF, "needs staff")
    elif info_ok and wants_consultation:
        set_status(contact, S.READY, "info complete and wants consultation")
    elif info_ok:
        set_status(contact, S.INFO, "core info collected")


def window_open(contact: Contact) -> bool:
    if not contact.last_contact_msg_at:
        return False
    return (timezone.now() - contact.last_contact_msg_at).total_seconds() < WINDOW_HOURS * 3600
