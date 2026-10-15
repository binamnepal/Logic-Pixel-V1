import requests
from django.conf import settings


def send(chat_id: str, text: str):
    """Returns (ok, error)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, "no TELEGRAM_BOT_TOKEN"
    try:
        r = requests.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)
        return r.ok, "" if r.ok else r.text[:200]
    except Exception as e:
        return False, type(e).__name__
