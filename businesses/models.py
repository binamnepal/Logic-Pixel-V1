from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class Business(models.Model):
    TYPES = [("education", "Study-abroad consultancy"), ("other", "Other")]
    name = models.CharField(max_length=120)
    business_type = models.CharField(max_length=32, choices=TYPES, default="education")
    phone_number_id = models.CharField(max_length=64, unique=True)
    access_token_enc = models.TextField(blank=True)
    knowledge_base = models.TextField(blank=True, help_text="Approved fees, countries, intakes, documents, hours.")
    bot_persona = models.TextField(blank=True, help_text="Bot name, tone, languages.")
    staff_email = models.CharField(
        max_length=500,
        blank=True,
        help_text="One or more emails, separated by commas.",
    )
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "businesses"

    def __str__(self):
        return self.name

    def get_staff_emails(self):
        return [e.strip() for e in self.staff_email.split(",") if e.strip()]

    def set_token(self, token: str):
        self.access_token_enc = Fernet(settings.FERNET_KEY.encode()).encrypt(token.encode()).decode()

    def get_token(self) -> str:
        return Fernet(settings.FERNET_KEY.encode()).decrypt(self.access_token_enc.encode()).decode()


class StaffProfile(models.Model):
    """Links a staff user to ONE business so they only see that business's data."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    business = models.ForeignKey(Business, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user} -> {self.business}"


def scope_queryset(qs, user, path="business"):
    """Superusers see everything; staff see only their business; others see nothing."""
    if user.is_superuser:
        return qs
    profile = getattr(user, "staff_profile", None)
    return qs.filter(**{path: profile.business}) if profile else qs.none()