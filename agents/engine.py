import json
import logging
import time
import requests
from django.conf import settings
from .prompts import FALLBACK, build_system

log = logging.getLogger(__name__)
RETRY_STATUS = {429, 500, 502, 503, 504}


def _post(model, messages, json_mode=True):
    body = {"model": model, "messages": messages, "temperature": 0.3}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return requests.post(
        f"{settings.AI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
        json=body,
        timeout=30,
    )


def _call(model, messages):
    last = None
    json_mode = True
    for attempt in range(3):
        try:
            r = _post(model, messages, json_mode)
        except (requests.Timeout, requests.ConnectionError) as e:
            last = e
            time.sleep(2)
            continue
        if r.status_code == 400 and json_mode and "json" in r.text.lower():
            log.warning("JSON mode rejected, retrying without it: %s", r.text[:200])
            json_mode = False
            continue
        if r.status_code in RETRY_STATUS and attempt < 2:
            time.sleep(2)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"AI {r.status_code} (model={model}): {r.text[:400]}")
        return r.json()["choices"][0]["message"]["content"]
    raise last or RuntimeError("AI request failed")


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


def ask(business, contact, history) -> dict:
    known = {k: v for k, v in {"name": contact.name, **(contact.attributes or {})}.items() if v}
    messages = [{"role": "system", "content": build_system(business, known)}] + [
        {"role": "user" if m.sender == "contact" else "assistant", "content": m.body}
        for m in history if m.body]
    try:
        raw = _call(settings.AI_MODEL, messages)
    except Exception:
        if not settings.AI_FALLBACK_MODEL:
            raise
        raw = _call(settings.AI_FALLBACK_MODEL, messages)
    data = _parse(raw)
    return {
        "reply": str(data.get("reply") or FALLBACK),
        "needs_staff": bool(data.get("needs_staff")),
        "pause_ai": bool(data.get("pause_ai")),
        "reason": str(data.get("reason") or ""),
        "wants_consultation": bool(data.get("wants_consultation")),
        "details": data.get("details") if isinstance(data.get("details"), dict) else {},
    }