# Copyright (c) 2026, AssetCore Team
"""TC-BE-OPHACL-01..04 — `AC-CR-119`: hợp đồng quyền của 3 nhánh vận hành trên hồ sơ thiết bị.

Nguồn spec: `docs/imm-00/ADR-IMM00-ASSET-OP-HISTORY.md §11` (D-OPH-21 · D-OPH-22 ·
D-OPH-27) · `docs/imm-00/05_API_Specification.md §III.26.7`.

Vì sao suite RIÊNG (không nhét vào test_imm08/09/12): đối tượng kiểm là **hợp đồng
quyền chung của cả 3 nhánh** (cap ⇄ DocType bị gate ⇄ envelope 403) — nó cắt ngang 3
module, và cái nó bảo vệ là **tính SOUND của vị-từ cap**, không phải nghiệp vụ PM/CM/
Sự-cố. Đặt ở một chỗ ⇒ thêm nhánh thứ tư chỉ phải sửa MỘT bảng.

Bug gốc (đo từ đĩa 2026-07-30): `pm.read → ("PM Work Order","read")` (auto-gen từ
`_DOMAIN_PRIMARY["PM"]`) trong khi `get_asset_pm_history` đọc **`PM Task Log`**. Hai
DocType, hai bảng DocPerm: `Commissioning Manager` có read `PM Work Order` nhưng KHÔNG
có dòng nào trên `PM Task Log` ⇒ `rbac.can("pm.read")` = True mà endpoint 403 ⇒ FE gate
bằng `pm.read` sẽ MỞ nhánh rồi ĂN 403 (nút «Thử lại» chết).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.integration.test_asset_op_history_acl
"""
from __future__ import annotations

import json
import re
import unittest
import uuid
from pathlib import Path

import frappe

from assetcore.services.shared import rbac
from assetcore.services.shared.connection_meta import OP_HISTORY_BRANCH_GATE
from assetcore.setup.role_profile_catalog import BASE_ROLE
from assetcore.utils.messages import MSG, lookup_message
from frappe.tests.utils import FrappeTestCase

# UID mỗi lần chạy — LL-TEST: fixture tên CỐ ĐỊNH sẽ TỰ CHẶN CHÍNH NÓ sau một lần
# crash (bản ghi cũ còn nằm lại ⇒ insert lần sau đụng duplicate ⇒ đỏ oan mãi mãi).
_UID = uuid.uuid4().hex[:8]

#: `asset_ref` KHÔNG tồn tại — chủ ý: 3 nhánh đều là truy vấn đọc theo filter
#: `{asset_ref|asset}` nên tập kết quả rỗng là **xác định**, và cái đang kiểm là
#: "403 hay KHÔNG 403", tuyệt đối không phụ thuộc dữ liệu thật trên site (chống
#: false-green/false-red khi data site đổi).
_ASSET_ABSENT = f"_TEST_OPHACL_{_UID}"

#: Chuỗi TUYỆT ĐỐI không được xuất hiện trong payload trả client khi 403 (AC4).
_NEVER_LEAK = (
    "PM Task Log", "Asset Repair", "Incident Report",
    "Traceback", "traceback", "SELECT", "select *", "DocPerm",
)


def _call_pm(asset: str) -> dict:
    from assetcore.api import imm08

    return imm08.get_asset_pm_history(asset_ref=asset, limit=10)


def _call_cm(asset: str) -> dict:
    from assetcore.api import imm09

    return imm09.get_asset_repair_history(asset_ref=asset, limit="10")


def _call_incident(asset: str) -> dict:
    from assetcore.api import imm12

    return imm12.get_asset_incident_history(asset=asset, limit=10)


#: nhánh → endpoint THẬT (naming contract BE↔FE). Khoá KHỚP `OP_HISTORY_BRANCH_GATE`.
_BRANCH_CALL = {"pm": _call_pm, "cm": _call_cm, "incident": _call_incident}

#: Khoá chứa MẢNG DÒNG trong payload thành công — **KHÔNG đối xứng giữa 3 nhánh**
#: (đo từ đĩa: `services/imm08.py`/`imm09.py` trả ``history``, `services/imm12.py`
#: trả ``items``). Khai tường minh ở đây thay vì giả định `history` cho cả 3: đổi
#: khoá = breaking change cho FE/mobile đang chạy (Hyrum) ⇒ vòng này chỉ **ghi
#: nhận** bất đối xứng và khoá nó bằng test, không tiện tay đổi shape.
_BRANCH_ROWS_KEY = {"pm": "history", "cm": "history", "incident": "items"}


def setUpModule():
    frappe.set_user("Administrator")


class _OpHistoryAclBase(FrappeTestCase):
    """Fixture chung: user tạm mang ĐÚNG bộ role cần thiết, teardown sạch."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.local.form_dict = frappe._dict()
        frappe.set_user("Administrator")

    def _make_user(self, tag: str, roles: list[str]) -> str:
        """User tạm (uuid-suffix) + base role AssetCore + `roles`."""
        email = f"_test_ophacl_{tag}_{_UID}@assetcore.test"
        self._emails.append(email)
        doc = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"OPHACL {tag}",
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            # Base role = định danh "user AssetCore" (mọi user thật đều có) —
            # KHÔNG set role_profile_name (tránh re-sync ghi đè roles, LL-QA-16).
            "roles": [{"role": r} for r in dict.fromkeys([BASE_ROLE, *roles])],
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        # Quyền được resolve từ `Has Role` → DocPerm; xoá cache user để lần
        # has_permission đầu tiên KHÔNG đọc bản đồ role cũ.
        frappe.clear_cache(user=email)
        return email

    # ── assertion helpers ────────────────────────────────────────────────────
    def _assert_forbidden_envelope(self, res: dict, branch: str) -> None:
        """Envelope 403 ĐÚNG hình: HTTP-200 + success=false + code/http_status + message HẰNG."""
        entry = lookup_message(MSG.AUTH_FORBIDDEN)
        self.assertIsInstance(res, dict, f"[{branch}] endpoint phải trả dict envelope")
        self.assertFalse(
            res.get("success"),
            f"[{branch}] thiếu cap mà endpoint vẫn success ⇒ rò dữ liệu ngoài quyền.",
        )
        self.assertEqual(
            res.get("code"), "FORBIDDEN",
            f"[{branch}] code={res.get('code')!r} ≠ 'FORBIDDEN' — FE phân loại 403 "
            f"bằng code (api/errors.ts::isForbiddenError), KHÔNG bằng chuỗi tiếng Việt.",
        )
        self.assertEqual(
            res.get("http_status"), 403,
            f"[{branch}] http_status={res.get('http_status')!r} ≠ 403 (in-handler "
            f"cap-403 trên HTTP-200 — KHÔNG dispatcher-403, FE KHÔNG logout).",
        )
        self.assertEqual(
            res.get("message_code"), MSG.AUTH_FORBIDDEN,
            f"[{branch}] message_code phải là HẰNG {MSG.AUTH_FORBIDDEN} (registry).",
        )
        # Chuỗi hiển thị nằm ở khoá `error` của error-envelope (`utils/response.py::
        # _err` — khoá `message` CHỈ tồn tại trong nhánh success của một số endpoint).
        self.assertEqual(
            res.get("error"), entry["template"],
            f"[{branch}] chuỗi hiển thị phải là HẰNG của registry "
            f"({MSG.AUTH_FORBIDDEN}) — không được đẻ microcopy thứ hai.",
        )
        self.assertEqual(
            res.get("action_hint"), entry["action_hint"],
            f"[{branch}] action_hint phải mượn nguyên registry (câu 2 của khối "
            f"«khoá» ở FE dùng cùng nguồn — 1 giọng cho toàn hệ thống).",
        )
        self._assert_no_leak(res, branch)

    def _assert_no_leak(self, res: dict, branch: str) -> None:
        """AC4 — chuỗi trả client KHÔNG chứa tên DocType/traceback/SQL."""
        blob = json.dumps(res, ensure_ascii=False, default=str)
        for needle in _NEVER_LEAK:
            self.assertNotIn(
                needle, blob,
                f"[{branch}] payload 403 rò {needle!r} ra client: {blob[:400]}",
            )


class TestOpHistoryCapSoundness(_OpHistoryAclBase):
    """TC-BE-OPHACL-01/03 — soundness 2 chiều của vị-từ cap, đo bằng HÀNH VI."""

    # TC-BE-OPHACL-01 — nhân chứng `pm.read` KHÔNG SOUND (RED trước khi land cap mới).
    def test_ophacl_01_pm_read_is_not_sound_for_history(self):
        email = self._make_user("cmgr", ["Commissioning Manager"])
        frappe.set_user(email)
        try:
            self.assertIs(
                rbac.can("pm.read"), True,
                "Commissioning Manager có DocPerm read trên 'PM Work Order' ⇒ "
                "pm.read PHẢI True (nếu False thì DocPerm site đã lệch doctype JSON).",
            )
            self.assertIs(
                rbac.can("pm.read_history"), False,
                "Commissioning Manager KHÔNG có DocPerm read trên 'PM Task Log' ⇒ "
                "pm.read_history PHẢI False. Nếu True ⇒ cap bind SAI doctype hoặc "
                "DocPerm đã bị nới (quyết định cấp-quyền, không thuộc vòng này).",
            )
            res = _call_pm(_ASSET_ABSENT)
        finally:
            frappe.set_user("Administrator")
        # Vế chứng minh: cap CŨ nói "được" mà endpoint nói 403 ⇒ gate FE bằng
        # `pm.read` sẽ vẽ nhánh CHẾT (mở → ăn 403 → «Thử lại» vô vọng).
        self._assert_forbidden_envelope(res, "pm")

    # TC-BE-OPHACL-03 — chiều DƯƠNG: cap True ⇒ endpoint KHÔNG 403.
    def test_ophacl_03_cap_true_means_no_forbidden(self):
        cases = [
            ("pm", "pm.read_history", "PM User", "pmuser"),
            ("cm", "repair.read", "Repair User", "repuser"),
            ("incident", "corrective.read", "Corrective User", "corruser"),
        ]
        for branch, cap, role, tag in cases:
            with self.subTest(branch=branch, cap=cap, role=role):
                email = self._make_user(tag, [role])
                frappe.set_user(email)
                try:
                    granted = rbac.can(cap)
                    res = _BRANCH_CALL[branch](_ASSET_ABSENT)
                finally:
                    frappe.set_user("Administrator")
                self.assertIs(
                    granted, True,
                    f"[{branch}] role {role!r} phải resolve {cap} = True "
                    f"(DocPerm read trên {OP_HISTORY_BRANCH_GATE[branch][1]!r}).",
                )
                self.assertTrue(
                    res.get("success"),
                    f"[{branch}] cap={cap} True nhưng endpoint KHÔNG success ⇒ vị-từ "
                    f"cap KHÔNG SOUND theo chiều dương (khoá OAN người có quyền): {res}",
                )
                self.assertNotEqual(
                    res.get("code"), "FORBIDDEN",
                    f"[{branch}] cap True mà vẫn FORBIDDEN — biconditional D-OPH-21 vỡ.",
                )
                rows_key = _BRANCH_ROWS_KEY[branch]
                self.assertIsInstance(
                    res["data"][rows_key], list,
                    f"[{branch}] payload thành công phải có `{rows_key}` là list.",
                )


class TestOpHistoryForbiddenEnvelope(_OpHistoryAclBase):
    """TC-BE-OPHACL-02 — persona base-role: CẢ 3 nhánh trả ĐÚNG một envelope 403."""

    def test_ophacl_02_base_role_gets_forbidden_on_all_three(self):
        email = self._make_user("baserole", [])
        frappe.set_user(email)
        try:
            resolved = {
                branch: rbac.can(cap)
                for branch, (cap, _dt) in OP_HISTORY_BRANCH_GATE.items()
            }
            results = {b: fn(_ASSET_ABSENT) for b, fn in _BRANCH_CALL.items()}
        finally:
            frappe.set_user("Administrator")

        for branch, cap_value in resolved.items():
            with self.subTest(branch=branch, phase="cap"):
                self.assertIs(
                    cap_value, False,
                    f"[{branch}] user chỉ có base role {BASE_ROLE!r} mà cap "
                    f"{OP_HISTORY_BRANCH_GATE[branch][0]!r} = True ⇒ DocPerm site đã "
                    f"nới ngoài doctype JSON (quyết định cấp-quyền, không phải mã).",
                )
        for branch, res in results.items():
            with self.subTest(branch=branch, phase="envelope"):
                self._assert_forbidden_envelope(res, branch)


class TestOpHistoryGateParity(FrappeTestCase):
    """TC-BE-OPHACL-04 — parity SSoT: bảng nhánh ⇄ CAPABILITY_MAP ⇄ FE component."""

    _FE_COMPONENT = (
        Path(frappe.get_app_path("assetcore")).parent
        / "frontend/src/components/asset/AssetOperationalHistory.vue"
    )

    def test_ophacl_04_branch_keys_are_exactly_three(self):
        self.assertEqual(
            set(OP_HISTORY_BRANCH_GATE), {"pm", "cm", "incident"},
            "Khoá nhánh PHẢI khớp `SectionKey` của FE (AssetOperationalHistory.vue) — "
            "thêm nhánh = thêm 1 dòng ở đây + 1 dòng ở SECTIONS, không đẻ bảng thứ hai.",
        )

    def test_ophacl_04_each_cap_binds_the_gated_doctype_read(self):
        for branch, (cap, doctype) in OP_HISTORY_BRANCH_GATE.items():
            with self.subTest(branch=branch, cap=cap):
                self.assertIn(
                    cap, rbac.CAPABILITY_MAP,
                    f"[{branch}] cap {cap!r} KHÔNG có trong CAPABILITY_MAP ⇒ "
                    f"`rbac.can` trả False VĨNH VIỄN (anti-pattern RBAC dead-gate).",
                )
                self.assertEqual(
                    rbac.CAPABILITY_MAP[cap], (doctype, "read"),
                    f"[{branch}] binding lệch: CAPABILITY_MAP[{cap!r}]="
                    f"{rbac.CAPABILITY_MAP[cap]} ≠ ({doctype!r}, 'read'). Vị-từ cap "
                    f"PHẢI bind ĐÚNG DocType mà truy vấn thật đọc (D-OPH-21).",
                )

    def test_ophacl_04_frontend_uses_exactly_these_caps(self):
        """FE gate 3 nhánh bằng ĐÚNG 3 chuỗi cap này — 0 cap lạ, 0 cap thiếu.

        ⚠️ HỢP ĐỒNG SONG SONG: nửa FE của `AC-CR-119` land ở CÙNG vòng (agent khác).
        Khi component CHƯA có bất kỳ máy móc gate nào (0/3 cap ∧ 0 `capState(`) ⇒
        SKIP kèm thông điệp ồn ào (nửa FE chưa land — báo ở `contract_unverified`),
        KHÔNG giả xanh. Mọi trạng thái KHÁC (một phần / cap lạ / còn `pm.read` trần)
        ⇒ ĐỎ CỨNG: đó chính là drift BE↔FE mà guard này sinh ra để bắt.
        """
        self.assertTrue(
            self._FE_COMPONENT.is_file(),
            f"Không thấy component FE: {self._FE_COMPONENT}",
        )
        src = self._FE_COMPONENT.read_text(encoding="utf-8")
        caps = {cap for cap, _dt in OP_HISTORY_BRANCH_GATE.values()}
        found = {cap for cap in caps if re.search(rf"""['"]{re.escape(cap)}['"]""", src)}

        if not found and "capState(" not in src:
            self.skipTest(
                "AC-CR-119 nửa FE CHƯA land (0/3 cap + 0 `capState(` trong "
                f"{self._FE_COMPONENT.name}) — parity BE↔FE CHƯA verify được. "
                "QA phải chạy lại suite này SAU khi FE land."
            )

        self.assertEqual(
            found, caps,
            f"FE gate bằng tập cap {sorted(found)} ≠ SSoT {sorted(caps)} "
            "(OP_HISTORY_BRANCH_GATE). Thiếu ⇒ nhánh vẫn gọi API vô vọng; lạ ⇒ "
            "gate bằng vị-từ không có trong CAPABILITY_MAP (dead-gate).",
        )
        self.assertIsNone(
            re.search(r"""['"]pm\.read['"]""", src),
            "FE còn gate bằng `pm.read` TRẦN — vị-từ KHÔNG SOUND cho nhánh Bảo trì "
            "(bind PM Work Order, endpoint đọc PM Task Log) ⇒ mở nhánh rồi ăn 403.",
        )
