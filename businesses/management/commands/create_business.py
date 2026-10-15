from django.core.management.base import BaseCommand
from businesses.models import Business


class Command(BaseCommand):
    help = "Create or update a business: create_business NAME PHONE_NUMBER_ID TOKEN [--email x] [--telegram id]"

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument("phone_number_id")
        parser.add_argument("token")
        parser.add_argument("--email", default="")
        parser.add_argument("--telegram", default="")
        parser.add_argument("--type", default="education")

    def handle(self, *a, **o):
        b, created = Business.objects.get_or_create(
            phone_number_id=o["phone_number_id"], defaults={"name": o["name"]})
        b.name, b.business_type = o["name"], o["type"]
        b.staff_email, b.telegram_chat_id = o["email"], o["telegram"]
        b.set_token(o["token"])
        b.save()
        self.stdout.write(f"{'created' if created else 'updated'}: {b}")
