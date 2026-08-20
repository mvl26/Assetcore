# Copyright (c) 2026, AssetCore Team
"""Sinh ``CapabilityStatement`` TỪ bảng dispatch — không viết tay (SPEC §10).

Tham chiếu: https://hl7.org/fhir/R4/capabilitystatement.html

Vì sao sinh chứ không viết
---------------------------
``/metadata`` là cửa duy nhất để một client **chưa từng nghe tên AssetCore** tự khám
phá server (phép thử của SPEC §2). Bản khai viết tay sẽ trôi khỏi mã thật, và client
tin lời khai rồi nhận 404 — hỏng đúng thứ mà cả đợt này nhắm tới. Sinh từ
:mod:`assetcore.fhir.dispatch` làm cho việc lệch trở thành bất khả.
"""

from __future__ import annotations

from typing import Any

import frappe

from assetcore.fhir import dispatch
from assetcore.fhir.response import base_url

#: Phiên bản chuẩn mà bề mặt này tuyên bố tuân thủ.
FHIR_VERSION = "4.0.1"


def _software_version() -> str:
    """Phiên bản app — đọc từ SSoT ``assetcore/__init__.py`` (không hardcode)."""
    from assetcore import __version__

    return __version__


def build_capability_statement() -> dict[str, Any]:
    """Dựng ``CapabilityStatement`` phản chiếu ĐÚNG bảng dispatch hiện tại.

    Returns:
        Resource ``CapabilityStatement`` dạng dict — TRẦN, không bọc envelope.
    """
    resources: list[dict[str, Any]] = []
    for type_ in dispatch.resource_types():
        entry = dispatch.registry()[type_]
        block: dict[str, Any] = {
            "type": type_,
            "interaction": [
                {"code": code}
                for code in dispatch.INTERACTION_ORDER
                if code in entry.interactions
            ],
        }
        if entry.profile:
            block["profile"] = entry.profile
        if entry.search_params:
            block["searchParam"] = [
                {"name": p.name, "type": p.type_, "documentation": p.documentation}
                for p in entry.search_params
            ]
        resources.append(block)

    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": frappe.utils.now(),
        "publisher": "AssetCore",
        "kind": "instance",
        "software": {"name": "AssetCore", "version": _software_version()},
        "implementation": {
            "description": "AssetCore — quản lý vòng đời thiết bị y tế (HTM)",
            "url": base_url(),
        },
        "fhirVersion": FHIR_VERSION,
        "format": ["json", "application/fhir+json"],
        "rest": [{
            "mode": "server",
            "documentation": (
                "Bề mặt HL7 FHIR R4 của AssetCore. Mọi tương tác được sinh từ bảng "
                "dispatch nội bộ nên bản khai này luôn khớp mã thật."
            ),
            "security": {
                "service": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                        "code": "SMART-on-FHIR",
                    }],
                }],
            },
            "resource": resources,
        }],
    }
