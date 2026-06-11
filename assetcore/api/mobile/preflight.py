# Copyright (c) 2026, AssetCore Team and contributors
"""Phase-B pre-flight verifier cho initiative AssetCore Mobile (backend-for-mobile).

Mục đích
--------
Biến **checklist OAuth Client** (đặc tả tại ``docs/mobile/03-auth-oauth2.md §4`` ·
blocker **B-1** tại ``docs/mobile/11-phase-a-exit.md §2``) thành **hợp đồng thực thi
READ-ONLY**: ``verify_oauth_client()`` đọc cấu hình các record ``OAuth Client`` hiện
hữu và trả về **báo cáo có cấu trúc** cho biết Phase B đã provision đúng chưa.

Ranh giới (BẮT BUỘC — bám ADR-MOBILE-001)
-----------------------------------------
- **READ-ONLY tuyệt đối:** KHÔNG ``insert``/``save``/``set_value``/``delete`` bất kỳ
  record nào; KHÔNG sửa ``frappe.integrations.oauth2`` / ``frappe.oauth``.
- **KHÔNG dựng hệ quyền thứ 2** (ADR-MOBILE-001 b): chỉ ĐỌC config ``OAuth Client``;
  quyền THỰC của app native vẫn là RBAC capability/DocPerm theo user (``rbac.py``).
- **KHÔNG thêm capability mới**, KHÔNG đụng ``CAPABILITY_MAP``.
- **Gate System Manager:** ``@frappe.whitelist()`` (KHÔNG ``allow_guest``) +
  ``frappe.only_for("System Manager")`` — khớp DocPerm ``OAuth Client`` (read =
  System Manager). Endpoint chẩn đoán nội bộ, NGOÀI hợp đồng app native (không vào
  ``docs/mobile/openapi/assetcore-mobile.openapi.yaml``).
- **Chịu được hiện trạng thật** (``OAuth Client`` count = 0 @source): trả
  ``ready=False`` + blocker tiếng Việt, **KHÔNG raise**, **KHÔNG leak traceback**.

7 điều kiện B-1 được kiểm
-------------------------
1. có ≥ 1 record ``OAuth Client`` (``client_count >= 1``)
2. ``grant_type == "Authorization Code"``
3. ``response_type == "Code"``
4. ``default_redirect_uri`` == custom-scheme native ``assetcore://oauth/callback``
   VÀ nằm trong danh sách ``redirect_uris``
5. ``scopes == "all openid"`` (coarse — bám ADR-MOBILE-001 b / 03 §3.2)
6. ``skip_authorization == 0`` (hiện màn consent lần đầu)
7. ``allowed_roles`` non-empty (least-privilege field-tech)

Tham chiếu
----------
- Field-spec nguồn (KHÔNG nhân đôi): ``docs/mobile/03-auth-oauth2.md §4``
- Runbook thực thi: ``docs/mobile/10-deploy-ops.md §1``
- Blocker B-1: ``docs/mobile/11-phase-a-exit.md §2``
- Cách đọc report + lệnh chạy: ``docs/mobile/12-phase-b-preflight.md``
"""

from __future__ import annotations

from typing import Any

import frappe

# --- Hằng kỳ vọng (SSoT mã = 03 §4 field-spec; doc trỏ ngược về đây, không sao chép bảng) ---
OAUTH_CLIENT_DOCTYPE = "OAuth Client"

# Custom-scheme native (D-STACK, 03 §1 bước (b)/(c) · 10 §1).
EXPECTED_REDIRECT_URI = "assetcore://oauth/callback"
# Coarse scope (ADR-MOBILE-001 b · 03 §3.2) — quyền thực = RBAC theo user.
EXPECTED_SCOPES = "all openid"
EXPECTED_GRANT_TYPE = "Authorization Code"
EXPECTED_RESPONSE_TYPE = "Code"


def _split_redirect_uris(raw: Any) -> list[str]:
    """Chuẩn hoá Text ``redirect_uris`` (mỗi dòng 1 URI) thành list đã trim, bỏ rỗng."""
    if not raw:
        return []
    return [line.strip() for line in str(raw).splitlines() if line.strip()]


def _normalize_scopes(raw: Any) -> str:
    """Chuẩn hoá scopes về chuỗi token cách nhau 1 space (so coarse, không phụ thuộc spacing)."""
    if not raw:
        return ""
    return " ".join(str(raw).split())


def _check(field: str, expected: Any, actual: Any, passed: bool) -> dict[str, Any]:
    return {"field": field, "expected": expected, "actual": actual, "pass": bool(passed)}


def _evaluate_client(client: dict[str, Any], allowed_roles_count: int) -> tuple[list[dict[str, Any]], list[str]]:
    """Đánh giá 6 điều kiện cấp-record (B-1.2..B-1.7) cho 1 OAuth Client.

    READ-ONLY — chỉ đọc giá trị đã nạp. Trả (checks, blockers VI).
    """
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    grant_type = (client.get("grant_type") or "").strip()
    passed = grant_type == EXPECTED_GRANT_TYPE
    checks.append(_check("grant_type", EXPECTED_GRANT_TYPE, grant_type, passed))
    if not passed:
        blockers.append(
            f"grant_type phải là '{EXPECTED_GRANT_TYPE}' (Implicit đã deprecated, không hỗ trợ PKCE) — hiện: '{grant_type}'."
        )

    response_type = (client.get("response_type") or "").strip()
    passed = response_type == EXPECTED_RESPONSE_TYPE
    checks.append(_check("response_type", EXPECTED_RESPONSE_TYPE, response_type, passed))
    if not passed:
        blockers.append(
            f"response_type phải là '{EXPECTED_RESPONSE_TYPE}' (khớp response_type=code ở bước authorize) — hiện: '{response_type}'."
        )

    default_redirect = (client.get("default_redirect_uri") or "").strip()
    redirect_uris = _split_redirect_uris(client.get("redirect_uris"))
    passed = default_redirect == EXPECTED_REDIRECT_URI and EXPECTED_REDIRECT_URI in redirect_uris
    checks.append(
        _check(
            "default_redirect_uri",
            EXPECTED_REDIRECT_URI,
            {"default_redirect_uri": default_redirect, "redirect_uris": redirect_uris},
            passed,
        )
    )
    if not passed:
        blockers.append(
            f"default_redirect_uri phải == '{EXPECTED_REDIRECT_URI}' VÀ nằm trong redirect_uris "
            f"(custom-scheme native; sai → provider reject) — hiện default: '{default_redirect}'."
        )

    scopes = _normalize_scopes(client.get("scopes"))
    passed = scopes == EXPECTED_SCOPES
    checks.append(_check("scopes", EXPECTED_SCOPES, scopes, passed))
    if not passed:
        blockers.append(
            f"scopes nên là '{EXPECTED_SCOPES}' (coarse — quyền thực do RBAC capability theo user, 03 §3.2) — hiện: '{scopes}'."
        )

    skip_auth = int(client.get("skip_authorization") or 0)
    passed = skip_auth == 0
    checks.append(_check("skip_authorization", 0, skip_auth, passed))
    if not passed:
        blockers.append(
            "skip_authorization phải = 0 (hiện màn Allow/Deny lần đầu); chỉ đặt 1 cho first-party trusted có chủ đích."
        )

    passed = allowed_roles_count > 0
    checks.append(_check("allowed_roles", ">=1 role (field-tech least-priv)", allowed_roles_count, passed))
    if not passed:
        blockers.append(
            "allowed_roles rỗng — phải giới hạn role field-tech (KTV) để least-privilege, giảm bề mặt (T5, 08 §3b)."
        )

    return checks, blockers


@frappe.whitelist()
def verify_oauth_client() -> dict[str, Any]:
    """Pre-flight READ-ONLY: OAuth Client đã provision đúng cho app native chưa? (B-1)

    Gate: System Manager (DocPerm ``OAuth Client`` read = System Manager).
    KHÔNG tạo/sửa record, KHÔNG raise vì lý do nghiệp vụ, KHÔNG leak traceback.

    :returns: báo cáo có cấu trúc::

        {
          "ready": bool,                 # True nếu có ≥1 client THOẢ toàn bộ 7 điều kiện B-1
          "client_count": int,           # số record OAuth Client (read-only count)
          "checks": [                     # 7 điều kiện B-1 (client_count + 6 cấp-record)
            {"field": str, "expected": Any, "actual": Any, "pass": bool}, ...
          ],
          "blockers": [str, ...],         # mô tả tiếng Việt từng điều kiện chưa đạt
          "checked_client": str | None,   # name client được chấm (best-effort) hoặc None
        }

    Hợp đồng "chịu được count==0": khi chưa có client nào (hiện trạng thật @source),
    trả ``ready=False`` + 1 check ``client_count`` fail + blocker
    'Chưa có OAuth Client — Phase B chưa provision'. KHÔNG raise.
    """
    # 1) Gate quyền — chỉ System Manager. KHÔNG allow_guest. Raise quyền là ĐÚNG hợp đồng
    #    (không nuốt) vì đó là bảo vệ truy cập, không phải lỗi nghiệp vụ.
    frappe.only_for("System Manager")

    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    # 2) Đếm record (read-only). client_count >= 1 là điều kiện B-1 #1.
    client_count = frappe.db.count(OAUTH_CLIENT_DOCTYPE)
    has_client = client_count >= 1
    checks.append(_check("client_count", ">=1", client_count, has_client))

    if not has_client:
        # Hiện trạng thật @source: 0 client. KHÔNG raise — trả report sạch.
        blockers.append("Chưa có OAuth Client — Phase B chưa provision.")
        return {
            "ready": False,
            "client_count": client_count,
            "checks": checks,
            "blockers": blockers,
            "checked_client": None,
        }

    # 3) Có ≥1 client → chấm record ĐẦU TIÊN (best-effort, ổn định theo creation).
    #    READ-ONLY: get_all + get_doc chỉ đọc.
    names = frappe.get_all(
        OAUTH_CLIENT_DOCTYPE, fields=["name"], order_by="creation asc", limit_page_length=1
    )
    client_name = names[0]["name"]
    doc = frappe.get_doc(OAUTH_CLIENT_DOCTYPE, client_name)
    client = {
        "grant_type": doc.get("grant_type"),
        "response_type": doc.get("response_type"),
        "default_redirect_uri": doc.get("default_redirect_uri"),
        "redirect_uris": doc.get("redirect_uris"),
        "scopes": doc.get("scopes"),
        "skip_authorization": doc.get("skip_authorization"),
    }
    allowed_roles_count = len(doc.get("allowed_roles") or [])

    record_checks, record_blockers = _evaluate_client(client, allowed_roles_count)
    checks.extend(record_checks)
    blockers.extend(record_blockers)

    ready = all(c["pass"] for c in checks)
    return {
        "ready": ready,
        "client_count": client_count,
        "checks": checks,
        "blockers": blockers,
        "checked_client": client_name,
    }
