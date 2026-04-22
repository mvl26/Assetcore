# Copyright (c) 2026, AssetCore Team
"""Lifecycle event + audit trail helpers (SHA-256 chain)."""
import hashlib
import json
import frappe
from frappe.utils import now_datetime


def _compute_hash(record: dict, prev_hash: str) -> str:
    payload = {
        "asset": record.get("asset"),
        "event_type": record.get("event_type"),
        "timestamp": str(record.get("timestamp")),
        "actor": record.get("actor"),
        "change_summary": record.get("change_summary") or "",
        "prev_hash": prev_hash or "",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _latest_prev_hash(asset: str) -> str:
    row = frappe.db.sql(
        """
        SELECT hash_sha256 FROM `tabIMM Audit Trail`
        WHERE asset = %s ORDER BY timestamp DESC, creation DESC LIMIT 1
        """,
        (asset,),
        as_dict=True,
    )
    return row[0].hash_sha256 if row else ""


def log_audit_event(
    asset: str,
    event_type: str,
    actor: str = None,
    ref_doctype: str = None,
    ref_name: str = None,
    change_summary: str = "",
    from_status: str = None,
    to_status: str = None,
) -> str:
    ts = now_datetime()
    actor = actor or frappe.session.user
    prev_hash = _latest_prev_hash(asset)
    rec = {
        "asset": asset,
        "event_type": event_type,
        "timestamp": ts,
        "actor": actor,
        "change_summary": change_summary,
    }
    h = _compute_hash(rec, prev_hash)
    doc = frappe.get_doc({
        "doctype": "IMM Audit Trail",
        "asset": asset,
        "event_type": event_type,
        "timestamp": ts,
        "actor": actor,
        "ref_doctype": ref_doctype,
        "ref_name": ref_name,
        "change_summary": change_summary,
        "from_status": from_status,
        "to_status": to_status,
        "ip_address": getattr(frappe.local, "request_ip", None),
        "hash_sha256": h,
        "prev_hash": prev_hash or None,
    }).insert(ignore_permissions=True)
    return doc.name


def create_lifecycle_event(
    asset: str,
    event_type: str,
    actor: str = None,
    from_status: str = None,
    to_status: str = None,
    root_doctype: str = None,
    root_record: str = None,
    notes: str = "",
) -> str:
    doc = frappe.get_doc({
        "doctype": "Asset Lifecycle Event",
        "asset": asset,
        "event_type": event_type,
        "timestamp": now_datetime(),
        "actor": actor or frappe.session.user,
        "from_status": from_status,
        "to_status": to_status,
        "root_doctype": root_doctype,
        "root_record": root_record,
        "notes": notes,
    }).insert(ignore_permissions=True)
    return doc.name


def verify_audit_chain(asset: str) -> dict:
    rows = frappe.db.sql(
        """
        SELECT name, asset, event_type, timestamp, actor, change_summary,
               hash_sha256, prev_hash
        FROM `tabIMM Audit Trail`
        WHERE asset = %s ORDER BY timestamp ASC, creation ASC
        """,
        (asset,),
        as_dict=True,
    )
    prev = ""
    for idx, r in enumerate(rows):
        expected = _compute_hash(r, prev)
        if expected != r.hash_sha256 or (prev and r.prev_hash != prev):
            return {"valid": False, "broken_at": r.name, "index": idx, "count": len(rows)}
        prev = r.hash_sha256
    return {"valid": True, "count": len(rows)}
