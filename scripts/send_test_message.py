"""Fake an incoming WhatsApp message (no Meta needed).
Usage: python scripts/send_test_message.py "Hi" --phone-id TEST456 [--from 9779800000000] [--name "Test Student"]
Env: MSG_ID (to test duplicates), BASE_URL."""
import argparse, hashlib, hmac, json, os, time
import requests
from dotenv import load_dotenv

load_dotenv()
p = argparse.ArgumentParser()
p.add_argument("text", nargs="*")
p.add_argument("--phone-id", default=os.getenv("PHONE_NUMBER_ID", "TEST123"))
p.add_argument("--from", dest="sender", default="9779800000000")
p.add_argument("--name", default="Test Student")
a = p.parse_args()

text = " ".join(a.text) or "Hi, I want to study in Australia"
payload = {"entry": [{"changes": [{"field": "messages", "value": {
    "metadata": {"phone_number_id": a.phone_id},
    "contacts": [{"wa_id": a.sender, "profile": {"name": a.name}}],
    "messages": [{"from": a.sender, "id": os.getenv("MSG_ID") or f"wamid.{time.time_ns()}",
                  "type": "text", "text": {"body": text}}],
}}]}]}
body = json.dumps(payload).encode()
sig = "sha256=" + hmac.new(os.environ["META_APP_SECRET"].encode(), body, hashlib.sha256).hexdigest()
r = requests.post(os.getenv("BASE_URL", "http://127.0.0.1:8000") + "/webhook", data=body,
                  headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
print(f"phone_id={a.phone_id} ->", r.status_code, r.text)