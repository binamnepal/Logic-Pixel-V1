Student -> WhatsApp -> Meta -> /webhook -> verify signature -> dedupe -> save -> 200
 -> django-q task agents.runner.handle_inbound -> AI (agents/engine.py) -> save details/status
 -> reply (whatsapp/client.py) -> notify staff (notifications/) when a rule matches.
