from django.test import TestCase
from businesses.models import Business
from conversations.models import Contact
from conversations.services import apply_details, compute_status, set_status


class ServicesTests(TestCase):
    def setUp(self):
        b = Business.objects.create(name="T", phone_number_id="1", access_token_enc="x")
        self.c = Contact.objects.create(business=b, wa_phone="977")

    def test_apply_details_validates(self):
        apply_details(self.c, {"name": " Ram ", "email": "bad", "country": "Australia", "budget": None})
        self.assertEqual(self.c.name, "Ram")
        self.assertEqual(self.c.attributes["country"], "Australia")
        self.assertNotIn("email", self.c.attributes)

    def test_info_collected(self):
        apply_details(self.c, {"name": "Ram", "country": "UK", "study_level": "Bachelor"})
        compute_status(self.c, False, False)
        self.assertEqual(self.c.status, Contact.Status.INFO)

    def test_ready_never_downgraded(self):
        set_status(self.c, Contact.Status.READY)
        compute_status(self.c, True, False)
        self.assertEqual(self.c.status, Contact.Status.READY)
