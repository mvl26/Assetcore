# Copyright (c) 2026, AssetCore Team
"""IMM-10 Recall/FSCA — service tier (UC-028, BA #16 §2 Đợt-2 #12).

Contract-truth FROZEN = Spec mobile `docs/features/47-canh-bao-recall-fsca.md`
§3a (doctype IMM Recall Notice) + §3b (shape response verbatim). Build khớp 1-1
với [CORE-DEV] mobile — lệch shape → quay lại [BA] TRƯỚC khi đổi.

Service CHỈ lookup + build payload (read-only, KHÔNG audit/ALE — parity
`services.imm00.resolve_qr_token`). Gate quyền (rbac `asset.read`) + 404
leak-safe + IDOR vendor-scope do API tier (`api/imm10.py`) xử lý — service
KHÔNG quyết định quyền.
"""
from __future__ import annotations

import frappe

_DT_RECALL = "IMM Recall Notice"
_DT_ASSET = "AC Asset"

# 8 field / row recall — verbatim Spec 47 §3b (rows-key = data.recalls, object-wrap).
# Mobile parity-curate mirror YAML theo response THẬT (CR-26) — đổi list này = đổi
# contract → phải qua [BA] trước.
_RECALL_ROW_FIELDS = (
    "name", "title", "source", "severity",
    "action_required", "scope_note", "published_date", "reference_no",
)


def _str_or_blank(value) -> str:
    """Chuẩn hoá field chuỗi → str strip 2 đầu; None/non-str → ''.

    Parity CONTRACT với SSoT `services.imm00._str_or_blank` (LUÔN trả str, NEVER
    None; KHÔNG transform giữa-chuỗi). Bản local có chủ đích — lane-constraint
    vòng này chỉ import `resolve_qr_token` từ imm00, KHÔNG với private helper.
    """
    if not isinstance(value, str):
        return ""
    return value.strip()


def _date_yyyy_mm_dd(value) -> str:
    """Date/str → chuỗi ``YYYY-MM-DD`` (Spec §3b: date dạng ISO). Rỗng/hỏng → ''.

    `frappe.get_all` trả ``datetime.date`` cho field Date — mobile cần string
    thuần; `published_date` reqd nên nhánh '' chỉ là defensive (KHÔNG raise).
    """
    if not value:
        return ""
    try:
        return frappe.utils.getdate(value).isoformat()
    except Exception:
        return ""


def check_asset_recall(asset_name: str) -> dict:
    """Payload ``{asset, has_recall, recalls[]}`` cho 1 asset — Spec 47 §3b FROZEN.

    Quy tắc chọn rows (§3b): CHỈ notice ``status = Active`` match ``device_model``
    của asset · ORDER ``published_date DESC`` (tiebreak ``name DESC`` cho thứ tự
    deterministic khi trùng ngày — refinement trong-spec, không đổi quy tắc).

    - Asset KHÔNG gán device_model → ``{has_recall: False, recalls: []}``
      (success — không lỗi; D1: match model-level, over-warn > under-warn).
    - ``has_recall`` = bool THẬT (không int-0/1 — shape không có field Check).
    - Query qua ``frappe.get_all`` (ignore_permissions mặc định): quyền đọc đã
      gate bằng capability ``asset.read`` ở API tier — KTV/điều dưỡng không cần
      DocPerm riêng trên IMM Recall Notice để ĐỌC cảnh báo an toàn.
    """
    device_model = frappe.db.get_value(_DT_ASSET, asset_name, "device_model")
    if not device_model:
        return {"asset": asset_name, "has_recall": False, "recalls": []}
    rows = frappe.get_all(
        _DT_RECALL,
        filters={"status": "Active", "device_model": device_model},
        fields=list(_RECALL_ROW_FIELDS),
        order_by="published_date desc, name desc",
    )
    recalls = [
        {
            "name": r.get("name"),
            "title": _str_or_blank(r.get("title")),
            "source": _str_or_blank(r.get("source")),
            "severity": _str_or_blank(r.get("severity")),
            "action_required": _str_or_blank(r.get("action_required")),
            "scope_note": _str_or_blank(r.get("scope_note")),
            "published_date": _date_yyyy_mm_dd(r.get("published_date")),
            "reference_no": _str_or_blank(r.get("reference_no")),
        }
        for r in rows
    ]
    return {"asset": asset_name, "has_recall": bool(recalls), "recalls": recalls}


def asset_exists(asset_name: str) -> bool:
    """Kiểm tra một ``AC Asset`` có tồn tại không.

    Vì sao ở tầng service: tầng ``api/`` chỉ validate + uỷ quyền (CLAUDE.md §15).
    Trước đây ``api/imm10.py`` gọi thẳng ``frappe.db.exists`` — vi phạm 3-tier.

    Caller PHẢI strip chuỗi trước khi gọi: chuỗi rỗng trả ``False`` ngay, không
    query — tránh full-scan do tham số rỗng (giữ nguyên hành vi chống-full-scan đã
    có ở call site cũ).

    Args:
        asset_name: mã bản ghi ``AC Asset``.

    Returns:
        True nếu bản ghi tồn tại.
    """
    if not asset_name:
        return False
    return bool(frappe.db.exists("AC Asset", asset_name))
