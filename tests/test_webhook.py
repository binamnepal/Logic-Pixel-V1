import hashlib
import hmac
import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from businesses.models import Business
from conversations.models import Contact, Message

SECRET = "testsecret"


def _post(client, payload, sig=None):
    body = json.dumps(payload).encode()
    sig = sig or "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhook", data=body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sig)


def _payload(msg_id="wamid.1", echo=False):
    value = {"metadata": {"phone_number_id": "PN1"}}
    if echo:
        value["message_echoes"] = [{"id": msg_id, "to": "977980", "type": "text", "text": {"body": "hi from staff"}}]
    else:
        value["messages"] = [{"from": "977980", "id": msg_id, "type": "text", "text": {"body": "hello"}}]
    return {"entry": [{"changes": [{"field": "messages", "value": value}]}]}


@override_settings(META_APP_SECRET=SECRET, WHATSAPP_VERIFY_TOKEN="verify123")
class WebhookTests(TestCase):
    def setUp(self):
        Business.objects.create(name="T", phone_number_id="PN1", access_token_enc="x")

    def test_verification_handshake(self):
        r = self.client.get("/webhook", {"hub.mode": "subscribe", "hub.verify_token": "verify123", "hub.challenge": "42"})
        self.assertEqual(r.content, b"42")

    def test_bad_signature_rejected(self):
        self.assertEqual(_post(self.client, _payload(), sig="sha256=bad").status_code, 403)

    @patch("whatsapp.views.async_task")
    def test_duplicate_event_stored_once(self, task):
        _post(self.client, _payload())
        _post(self.client, _payload())
        self.assertEqual(Message.objects.filter(wa_msg_id="wamid.1").count(), 1)
        self.assertEqual(task.call_count, 1)

    @patch("whatsapp.views.async_task")
    def test_staff_echo_pauses_ai(self, task):
        _post(self.client, _payload(msg_id="wamid.2", echo=True))
        self.assertTrue(Contact.objects.get(wa_phone="977980").handover_active)
