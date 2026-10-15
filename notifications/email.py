from django.core.mail import send_mail


def send(to: str, subject: str, text: str):
    """Returns (ok, error)."""
    try:
        send_mail(subject, text, None, [to], fail_silently=False)
        return True, ""
    except Exception as e:
        return False, type(e).__name__
