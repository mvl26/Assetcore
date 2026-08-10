# Copyright (c) 2026, AssetCore Team
"""Shared idempotency-key resolver (CR-24 write-family closure).

Nguồn khoá idempotency dùng chung cho mọi write KHÔNG idempotent phục vụ mobile
write-outbox re-drain (mất mạng giữa request↔response ⇒ client gọi LẠI cùng thao
tác). Extract từ ``services/imm11.py::_resolve_measurement_idempotency_key``
(ADR-IMM11-07) để tái dùng ở IMM-00 ``receive_transfer`` mà KHÔNG copy logic.

Vòng này CHỈ dùng ở imm00; migrate 2 op cũ (imm08/imm11) sang util chung = backlog
(giữ nguyên để 0 regression).
"""
import frappe


def resolve_idempotency_key(client_request_id: str = "") -> str:
    """Resolve khoá idempotency: body param ``client_request_id`` THẮNG header.

    Thứ tự ưu tiên (parity ADR-IMM11-07):

    1. ``client_request_id`` (body/RPC form_dict) non-empty (đã ``strip``) → THẮNG.
       Đây là transport chính — mobile write-outbox thực gửi field trong body,
       nhất quán giữa content-type json và form (ADR-MOBILE-047).
    2. Header ``X-Idempotency-Key`` → alias ``Idempotency-Key`` (không tiền tố
       ``X-``). Werkzeug đọc header case-insensitive; đây là forward-compat cho
       drain middleware-based (docs/mobile/07-offline-sync §3 / A6).
    3. Cả hai vắng/rỗng → ``""`` ⇒ NO-OP dedup (legacy web-desk / client-cũ y
       nguyên, backward-compat 100%).

    An-toàn ngoài request-context (test / scheduler): ``frappe.get_request_header``
    truy cập ``frappe.request`` (thread-local proxy) → raise khi không có request;
    ``try/except`` nuốt → trả ``""`` KHÔNG raise.

    Args:
        client_request_id: khoá do client sinh (body param). Rỗng → thử header.

    Returns:
        Khoá idempotency đã ``strip``; ``""`` khi cả body lẫn header đều vắng.
    """
    resolved = (client_request_id or "").strip()
    if resolved:
        return resolved
    try:
        header = (frappe.get_request_header("X-Idempotency-Key")
                  or frappe.get_request_header("Idempotency-Key") or "")
    except Exception:
        header = ""
    return (header or "").strip()
