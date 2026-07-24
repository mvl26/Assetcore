# Copyright (c) 2026, AssetCore Team
"""IMM-10 REST API — Cảnh báo Recall/FSCA khi quét thiết bị (UC-028, mobile Đợt-2).

Tier 1 — parse HTTP input → gọi services.imm10 → _ok / _err envelope.
Contract-truth FROZEN = Spec mobile `docs/features/47-canh-bao-recall-fsca.md` §3b.

Convention:
  GET → frappe.whitelist(allow_guest=False)
  Response envelope: {success, data} | {success: false, error, code}
  Lỗi nghiệp vụ (NOT_FOUND / FORBIDDEN-vendor) trên HTTP-200 Decision-B;
  429 (rate-limit) + 403 capability (rbac.require) raise thật — parity imm00.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit          # precedent api/imm00.py:14

from assetcore.services import imm10 as svc
from assetcore.services.imm00 import resolve_qr_token as _svc_resolve_qr_token
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared import rbac
from assetcore.services.shared.scope import assert_vendor_can_access
from assetcore.utils.response import _ok, _err

_DT_ASSET = "AC Asset"

# 404 leak-safe — parity message `api/imm00.py:271` (KHÔNG phân biệt token-sai vs
# asset-không-tồn-tại vs cả-hai-rỗng; KHÔNG import constant private chéo module).
_ERR_ASSET_NOT_FOUND = "Asset không tồn tại"

# Spec 47 §3b — ngưỡng rate-limit endpoint ĐỌC `check_asset_recall`: 30 req/60s/IP.
# Hằng RIÊNG (KHÔNG tái dùng AC_QR_RESOLVE_RATE_LIMIT của imm00 — TÁCH BIỆT ngữ
# nghĩa kể cả trùng giá trị 30): recall-check fire SONG SONG scan-info trên màn
# kết quả quét (D2 §3c) → cùng tần suất quét-rack, cùng họ deep-link bán-công-khai
# (token in trên nhãn). Bucket RIÊNG: frappe rate_limiter cache key gồm
# `frappe.form_dict.cmd` ⟹ counter TÁCH BIỆT resolve/scan_info — 1 endpoint vượt
# ngưỡng KHÔNG khoá endpoint khác. Decorator bọc NGOÀI thân hàm → 429 raise TRƯỚC
# `rbac.require` ⇒ vượt ngưỡng = 0 byte payload build, no-leak (đếm MỌI call, kể
# cả 404/403 → chống enumeration). KHÔNG-HTTP context (test/CLI) bypass có chủ
# đích (`if not frappe.request: return fn` — frappe/rate_limiter.py:134).
AC_RECALL_CHECK_RATE_LIMIT = 30


@frappe.whitelist()
@rate_limit(limit=AC_RECALL_CHECK_RATE_LIMIT, seconds=60, ip_based=True)  # 429 TRƯỚC rbac.require — parity BR-00-29
def check_asset_recall(token: str = "", asset: str = ""):
    """GET — kiểm tra thiết bị có nằm trong recall/FSCA `Active` không (read-only).

    Mobile banner đỏ ở màn kết quả quét + màn chi tiết thiết bị (Spec 47 §2).
    Params: ``token`` (deep-link QR — ƯU TIÊN khi có cả hai) HOẶC ``asset``
    (name PK). Cả hai rỗng → 404 Decision-B.

    Bảo mật — thứ tự parity `imm00.get_asset_scan_info` (Spec §3b FROZEN):
      0. ``@rate_limit(AC_RECALL_CHECK_RATE_LIMIT/60s/IP)`` — 429 TRƯỚC
         ``rbac.require``, bucket RIÊNG theo ``cmd``, no-leak.
      1. ``rbac.require("asset.read")`` — cap CÓ SẴN (DocPerm AC Asset read),
         KHÔNG cap/DocType mới. Thiếu cap → ``frappe.PermissionError`` (403).
      2. Resolve định danh: ưu tiên ``token`` qua ``resolve_qr_token`` (import
         từ ``services.imm00`` — KHÔNG duplicate, kế thừa strip/normalize SSoT),
         fallback ``asset`` + ``frappe.db.exists``.
      3. token sai / asset ∄ / cả hai rỗng → 404 leak-safe (HTTP-200 Decision-B,
         ``code: NOT_FOUND`` — KHÔNG phân biệt nhánh, KHÔNG full-scan).
      4. IDOR/vendor isolation: ``assert_vendor_can_access`` (tái dùng, KHÔNG
         re-implement) → vendor ngoài scope → envelope ``FORBIDDEN``, KHÔNG leak.
      5. Read-only → KHÔNG ghi audit/ALE (chống spam chain mỗi lần quét).
    """
    # 1. RBAC gate — capability asset.read (tái dùng). PermissionError → 403.
    rbac.require("asset.read")
    # 2. Resolve định danh asset: ưu tiên token (deep-link QR), fallback asset-name.
    #    Chuẩn hoá parity get_asset_scan_info: token do _svc_resolve_qr_token strip
    #    SSoT; asset-name strip 2 đầu TRƯỚC exists (rỗng-sau-strip → guard 404,
    #    KHÔNG query — chống full-scan).
    token = token if isinstance(token, str) else ""
    asset = asset.strip() if isinstance(asset, str) else ""
    asset_name = None
    if token:
        resolved = _svc_resolve_qr_token(token)
        if resolved:
            asset_name = resolved.get("name")
    elif asset and frappe.db.exists(_DT_ASSET, asset):
        asset_name = asset
    # 3. 404 leak-safe — KHÔNG phân biệt "token sai" vs "asset không tồn tại".
    if not asset_name:
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # 4. IDOR guard — vendor không được giao việc trên asset → FORBIDDEN, no-leak.
    try:
        assert_vendor_can_access(_DT_ASSET, asset_name)
    except ServiceError as e:
        return _err(e.message, e.code)
    # 5. Read-only — KHÔNG audit/ALE. Build payload qua service; lỗi bất ngờ →
    #    INTERNAL sạch (log server-side, KHÔNG leak traceback — LL-BE-42).
    try:
        return _ok(svc.check_asset_recall(asset_name))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-10 check_asset_recall")
        return _err(_("Lỗi hệ thống, vui lòng thử lại sau."), ErrorCode.INTERNAL)
