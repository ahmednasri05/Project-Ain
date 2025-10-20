from db.client import payloads
from datetime import datetime, timezone

def create_payload(payload_document: dict):
    payloads.insert_one(payload_document)

def read_failed_payloads():
    return payloads.find({"parse_status": False})

