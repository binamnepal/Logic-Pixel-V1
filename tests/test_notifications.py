from unittest.mock import patch
from django.test import TestCase
from businesses.models import Business
from conversations.models import Contact
from notifications.notify import notify_staff


class NotifyTests(TestCase):
    @patch("notifications.notify.telegram.send", return_value=(True, ""))
    def test_one_alert_per_trigger_window(self, send):
        b = Business.objects.create(name="T", phone_number_id="1", access_token_enc="x", telegram_chat_id="99")
        c = Contact.objects.create(business=b, wa_phone="977")
        notify_staff(b, c, "needs staff", "handover")
        notify_staff(b, c, "needs staff", "handover")
        self.assertEqual(send.call_count, 1)
