# Copyright (c) 2026, AssetCore Team
"""Điểm vào website cho bề mặt FHIR — khuôn giống ``www/assetcore.py`` (SPEC §6.1).

Frappe định tuyến ``/fhir/<path:fhir_path>`` về đây qua ``website_route_rules``
trong ``hooks.py``. Controller này chỉ chuyển tiếp sang
:func:`assetcore.fhir.router.handle` rồi ghi resource TRẦN ra response.

Không dùng ``utils/response.py``: FHIR cấm bọc envelope (SPEC §6.2).
"""

from __future__ import annotations

import json

import frappe

from assetcore.fhir.response import FHIR_JSON
from assetcore.fhir.router import handle

no_cache = 1


def get_context(context: dict) -> None:
    """Xử lý một yêu cầu FHIR và ghi thẳng resource ra response.

    Frappe gọi hàm này cho mọi đường dẫn khớp ``/fhir/<path>``. Ta không render
    template — ta ghi JSON và kết thúc.
    """
    request = frappe.local.request
    fhir_path = frappe.form_dict.get("fhir_path", "")
    query = {k: v for k, v in request.args.items()} if request else {}

    resource = handle(fhir_path, (request.method if request else "GET").upper(), query)

    frappe.local.response["type"] = "binary"
    frappe.local.response["filename"] = "fhir.json"
    frappe.local.response["filecontent"] = json.dumps(resource, ensure_ascii=False).encode()
    frappe.local.response["content_type"] = FHIR_JSON
    context.no_cache = 1
