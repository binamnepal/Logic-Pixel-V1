"""Fake an incoming WhatsApp message (no Meta needed).
Usage: python scripts/send_test_message.py "Hi, I want to study in Australia"
Env: PHONE_NUMBER_ID (default TEST123), MSG_ID (to test duplicates), BASE_URL."""
import hashlib, hmac, json, os, sys, time
import requests
from dotenv import load_dotenv

load_dotenv()
text = " ".join(sys.argv[1:]) or "Hi, I want to study in Australia"
payload = {"entry": [{"changes": [{"field": "messages", "value": {
    "metadata": {"phone_number_id": os.getenv("PHONE_NUMBER_ID", "TEST123")},
    "contacts": [{"wa_id": "9779800000000", "profile": {"name": "Test Student"}}],
    "messages": [{"from": "9779800000000", "id": os.getenv("MSG_ID") or f"wamid.{time.time_ns()}",
                  "type": "text", "text": {"body": text}}],
}}]}]}
body = json.dumps(payload).encode()
sig = "sha256=" + hmac.new(os.environ["META_APP_SECRET"].encode(), body, hashlib.sha256).hexdigest()
r = requests.post(os.getenv("BASE_URL", "http://127.0.0.1:8000") + "/webhook", data=body,
                  headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
print(r.status_code, r.text)
