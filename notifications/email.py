from django.core.mail import send_mail


def send(to, subject: str, text: str):
    """`to` can be one address or a list. Returns (ok, error)."""
    recipients = [to] if isinstance(to, str) else list(to)
    recipients = [r for r in recipients if r]
    if not recipients:
        return False, "NoRecipients"
    try:
        send_mail(subject, text, None, recipients, fail_silently=False)
        return True, ""
    except Exception as e:
        return False, type(e).__name__