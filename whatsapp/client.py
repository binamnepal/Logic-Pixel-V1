import logging
import uuid
import requests

log = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


def send_text(business, to: str, body: str):
    """Returns (ok, wa_message_id, error_code)."""
    token = business.get_token()

    # TEST MODE: dummy token means no real WhatsApp send, just print the reply
    if token == "dummy-token":
        print(f"\n[TEST MODE] Reply to {to}:\n{body}\n")
        return True, f"test-{uuid.uuid4().hex[:12]}", None

    try:
        r = requests.post(
            f"{GRAPH}/{business.phone_number_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body[:4000]}},
            timeout=20,
        )
        data = r.json()
        if r.ok:
            return True, data["messages"][0]["id"], None
        log.error("WhatsApp send failed: %s", data)
        return False, None, str(data.get("error", {}).get("code", r.status_code))
    except Exception as e:
        log.exception("WhatsApp send error")
        return False, None, type(e).__name__