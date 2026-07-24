# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của IMM CAPA Record (hành động khắc phục/phòng ngừa) — SSoT Desk + Vue.

CAPA nằm CUỐI chuỗi khắc phục, nên đồ thị nghiêng về chiều XUÔI (nguồn phát sinh CAPA:
sự cố, phát hiện không phù hợp, thiết bị) — đúng câu hỏi người dùng đặt ra khi mở hồ sơ
CAPA: "hồ sơ này sinh ra từ đâu".
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "capa_record",
        "non_standard_fieldnames": {
            "IMM RCA Record": "linked_capa",
            "IMM User Competency": "revoke_capa_ref",
        },
        "internal_links": {
            "AC Asset": "asset",
            "Incident Report": "linked_incident",
            "IMM Compliance Finding": "imm_compliance_finding_ref",
        },
        "transactions": [
            {"label": _("Nguồn phát sinh"), "items": [
                "AC Asset", "Incident Report", "IMM Compliance Finding",
            ]},
            {"label": _("Liên quan"), "items": [
                "IMM Asset Calibration", "IMM RCA Record", "IMM User Competency",
            ]},
        ],
    }
