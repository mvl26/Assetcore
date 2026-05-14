# Copyright (c) 2026, AssetCore Team
"""Bootstrap Frappe Notification rules cho 6 module IMM.

Mỗi rule:
- subject (Jinja-rendered)
- message (Jinja HTML)
- channel: Email + System (notification log → bell)
- recipients: by role hoặc explicit field

Run: assetcore.notifications.setup.install_notifications
"""
from __future__ import annotations

import frappe


# ─── Rule definitions ────────────────────────────────────────────────────
# Mỗi rule được apply qua _upsert_notification(); nếu đã tồn tại thì update.

NOTIFICATIONS: list[dict] = [
    # ── IMM-12: Critical / High Incident → Workshop Lead + QA + Dept Head ──
    {
        "name": "IMM-12 Incident Critical High",
        "document_type": "Incident Report",
        "event": "New",
        "send_to_all_assignees": 0,
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[CRITICAL] Sự cố mới: {{ doc.name }} ({{ doc.severity }})",
        "condition": "doc.severity in ('High', 'Critical')",
        "message": """
<h3>🚨 Sự cố {{ doc.severity }} vừa được ghi nhận</h3>
<table cellpadding="6">
<tr><td><b>Mã:</b></td><td>{{ doc.name }}</td></tr>
<tr><td><b>Thiết bị:</b></td><td>{{ doc.asset }}</td></tr>
<tr><td><b>Loại:</b></td><td>{{ doc.incident_type }}</td></tr>
<tr><td><b>Mức:</b></td><td><b>{{ doc.severity }}</b></td></tr>
<tr><td><b>Mô tả:</b></td><td>{{ doc.description }}</td></tr>
<tr><td><b>Báo bởi:</b></td><td>{{ doc.reported_by }}</td></tr>
{% if doc.patient_affected %}<tr><td><b>⚠️ Ảnh hưởng BN:</b></td><td>{{ doc.patient_impact_description }}</td></tr>{% endif %}
</table>
<p><a href="/app/incident-report/{{ doc.name }}">Mở phiếu sự cố</a> · <a href="/incidents/{{ doc.name }}">Xem trên FE</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM Workshop Lead"},
            {"receiver_by_role": "IMM QA Officer"},
            {"receiver_by_role": "IMM Department Head"},
        ],
    },
    # ── IMM-08: PM Major Failure → Workshop Lead + Ops Manager ──
    {
        "name": "IMM-08 PM Major Failure",
        "document_type": "PM Work Order",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[PM] Halted Major Failure: {{ doc.name }}",
        "condition": "doc.workflow_state == 'Halted–Major Failure'",
        "message": """
<h3>⚠️ Phiếu PM dừng vì lỗi nghiêm trọng</h3>
<p>Phiếu <b>{{ doc.name }}</b> trên thiết bị <b>{{ doc.asset_ref }}</b> đã chuyển sang trạng thái <b>Halted–Major Failure</b>.</p>
<p>KTV: {{ doc.assigned_to }} — Ghi chú: {{ doc.technician_notes or '—' }}</p>
<p>Hệ thống đã tự động tạo phiếu CM. Vui lòng theo dõi.</p>
<p><a href="/app/pm-work-order/{{ doc.name }}">Mở phiếu PM</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM Workshop Lead"},
            {"receiver_by_role": "IMM Operations Manager"},
        ],
    },
    # ── IMM-09: Repair priority Critical → Workshop Lead ──
    {
        "name": "IMM-09 Repair Critical Priority",
        "document_type": "Asset Repair",
        "event": "New",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[CM] Phiếu Critical: {{ doc.name }} — {{ doc.asset_ref }}",
        "condition": "doc.priority == 'Critical'",
        "message": """
<h3>🚨 Phiếu sửa chữa CRITICAL</h3>
<p><b>{{ doc.name }}</b> — Thiết bị <b>{{ doc.asset_ref }}</b></p>
<p>SLA target: <b>{{ doc.sla_target_hours or 4 }}h</b></p>
<p>{{ doc.failure_description }}</p>
<p><a href="/app/asset-repair/{{ doc.name }}">Mở phiếu</a> · <a href="/cm/work-orders/{{ doc.name }}">FE</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM Workshop Lead"},
            {"receiver_by_role": "IMM Biomed Technician"},
        ],
    },
    # ── IMM-11: Calibration Failed → QA Officer + Workshop Lead ──
    {
        "name": "IMM-11 Calibration Failed",
        "document_type": "IMM Asset Calibration",
        "event": "Value Change",
        "value_changed": "overall_result",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[CAL] FAILED: {{ doc.name }} — {{ doc.asset }}",
        "condition": "doc.overall_result == 'Failed'",
        "message": """
<h3>❌ Hiệu chuẩn KHÔNG ĐẠT</h3>
<p>Phiếu <b>{{ doc.name }}</b> — Thiết bị <b>{{ doc.asset }}</b> đã được đánh dấu <b>Failed</b>.</p>
<p>Hệ thống tự động:</p>
<ul>
<li>Chuyển asset sang Out of Service</li>
<li>Tạo CAPA record (gắn trong field <code>capa_record</code>)</li>
<li>Trigger lookback assessment các asset cùng model</li>
</ul>
<p>QA Officer cần review CAPA và đóng để cho phép Conditionally Passed.</p>
<p><a href="/app/imm-asset-calibration/{{ doc.name }}">Mở phiếu hiệu chuẩn</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM QA Officer"},
            {"receiver_by_role": "IMM Workshop Lead"},
        ],
    },
    # ── IMM-04: Clinical Release approval ready → Ops Manager ──
    {
        "name": "IMM-04 Pending Clinical Release",
        "document_type": "Asset Commissioning",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[IMM-04] Chờ phê duyệt: {{ doc.name }}",
        "condition": "doc.workflow_state == 'Pending Release'",
        "message": """
<h3>✅ Phiếu commissioning sẵn sàng phát hành</h3>
<p><b>{{ doc.name }}</b> — Thiết bị <b>{{ doc.final_asset or doc.master_item }}</b></p>
<p>Vui lòng kiểm tra hồ sơ và phê duyệt Clinical Release.</p>
<p><a href="/app/asset-commissioning/{{ doc.name }}">Mở phiếu</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM Operations Manager"},
        ],
    },
    # ── IMM-05: Document Pending Review → QA Officer ──
    {
        "name": "IMM-05 Document Pending Review",
        "document_type": "Asset Document",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[IMM-05] Tài liệu chờ duyệt: {{ doc.name }}",
        "condition": "doc.workflow_state == 'Pending Review'",
        "message": """
<h3>📄 Tài liệu mới cần duyệt</h3>
<p><b>{{ doc.name }}</b> — Loại: <b>{{ doc.doc_type_detail }}</b></p>
<p>Asset: {{ doc.asset_ref or '—' }}</p>
<p><a href="/app/asset-document/{{ doc.name }}">Review</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM QA Officer"},
        ],
    },
    # ── IMM-12: RCA Required → QA Officer + Workshop Lead ──
    {
        "name": "IMM-12 RCA Required",
        "document_type": "IMM RCA Record",
        "event": "New",
        "is_standard": 0,
        "module": "AssetCore",
        "channel": "Email",
        "send_system_notification": 1,
        "subject": "[RCA] Cần phân tích: {{ doc.name }}",
        "message": """
<h3>🔍 RCA mới — cần phân tích</h3>
<p><b>{{ doc.name }}</b> — Asset <b>{{ doc.asset }}</b></p>
<p>Phương pháp: {{ doc.rca_method }} — Hạn: {{ doc.due_date or 'Không đặt' }}</p>
<p>Trigger: {{ doc.trigger_type }}</p>
<p><a href="/app/imm-rca-record/{{ doc.name }}">Bắt đầu RCA</a></p>
""",
        "recipients": [
            {"receiver_by_role": "IMM QA Officer"},
            {"receiver_by_role": "IMM Workshop Lead"},
        ],
    },
]


def _upsert_notification(rule: dict) -> str:
    """Tạo hoặc update 1 Notification record."""
    name = rule["name"]
    if frappe.db.exists("Notification", name):
        doc = frappe.get_doc("Notification", name)
        # Clear old recipients để tránh trùng
        doc.set("recipients", [])
    else:
        doc = frappe.new_doc("Notification")
        doc.name = name

    fields = (
        "subject", "message", "document_type", "event",
        "value_changed", "condition",
        "send_system_notification", "is_standard", "module",
        "channel",
    )
    for f in fields:
        if f in rule:
            setattr(doc, f, rule[f])

    for r in rule.get("recipients", []):
        doc.append("recipients", r)

    doc.enabled = 1
    doc.save(ignore_permissions=True)
    return doc.name


def install_notifications() -> dict:
    """Idempotent installer — gọi sau mỗi lần migrate."""
    created = []
    for rule in NOTIFICATIONS:
        try:
            n = _upsert_notification(rule)
            created.append(n)
        except Exception as e:
            frappe.log_error(
                f"Notification install failed: {rule.get('name')}: {e}",
                "AssetCore Notification Setup",
            )
    frappe.db.commit()
    return {"created": created, "count": len(created)}
